# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.data_import.importer import Importer
from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file
from frappe.utils.csvutils import read_csv_content
from frappe.utils.data import cint
import json
import os
from frappe import _
class ImportAssessmentResults(Document):
	@frappe.whitelist()
	def get_preview_from_template(self, assessment_results_file=None):
		if assessment_results_file:
			self.assessment_results_file = assessment_results_file

		if not self.assessment_results_file :
			return

		i = self.get_importer()
		return i.get_data_for_import_preview()
	def get_importer(self):
		return Importer(self.reference_doctype, data_import=self)
	


@frappe.whitelist()
def import_grades(data_import, data_file, assessment_plan, background=False):
	data_import_doc = frappe.get_doc("Import Assessment Results", data_import)
	data_import_doc.status = 'In Progress'
	data_import_doc.save()
	frappe.db.commit()
	if background:
		frappe.enqueue(import_grades_file,data_import=data_import_doc, data_file=data_file, assessment_plan=assessment_plan )
	else:
		import_grades_file(data_import_doc, data_file, assessment_plan)

@frappe.whitelist()
def import_grades_file(data_import, data_file, assessment_plan):
	content, extn = read_file(data_file)
	data = read_content(content, extn)
	criterias = frappe.db.get_all("Assessment Plan Criteria", {"parent": assessment_plan}, ['assessment_criteria'])
	required_columns = {
		'academic_year': 'Academic Year', 
		'academic_term': 'Academic Term', 
		'course_id': 'Course id', 
		'student': 'Student Email',
		'total': 'Graduation Grade' }
	for criteria in criterias:
		required_columns[criteria['assessment_criteria']] = criteria['assessment_criteria']
	required_columns_indexes = get_required_columns_indexes(data[0], list(required_columns.values()))
	data = data[1:]
	errors = {}
	warnings = {}
	success =0
	for index in range(len(data)):
		enrollment_data = data[index]
		added = add_grades_data(required_columns, required_columns_indexes, enrollment_data, assessment_plan, criterias)
		if added.get('error'): 
			errors[str(index)] = added.get("msg")
			data_import.error_log = json.dumps(errors)
			#errors.append(added.get('msg'))
		elif added.get('warning'): 
			warnings[str(index)] = added.get("msg")
			data_import.warning_log = json.dumps(warnings)
		else: success +=1	
		if index % 10  == 0:
			data_import.save()
			frappe.db.commit()
			frappe.publish_realtime(
							"assessment_data_import_progress",
							{
								"current": index + 1,
								"total": len(data),
								"data_import": data_import.name,
							},
							user=frappe.session.user,
						)
	data_import.save()
	frappe.publish_realtime(
							"assessment_data_import_progress",
							{
								"current": len(data),
								"total": len(data),
								"data_import": data_import.name,
							},
							user=frappe.session.user,
						)
	if(len(errors) > 0) and success ==0:
		data_import.status = "Error"
	elif (len(errors) > 0) and success > 0:
		data_import.status = 'Partial Success'
	elif (errors) == 0 and success > 0:
		data_import.status = 'Success'
	data_import.save()
	frappe.db.commit()


def add_grades_data(required_columns, required_columns_indexes, enrollment_data, assessment_plan, criterias):
	academic_term = enrollment_data[required_columns_indexes[required_columns['academic_term']]]
	academic_year = enrollment_data[required_columns_indexes[required_columns['academic_year']]]
	student_email = enrollment_data[required_columns_indexes[required_columns['student']]]
	if not student_email:
		return {"error": False}
	student = frappe.db.get_value("Student", {"student_email_id": student_email}, ['name'])
	if not student:
		return {'error': True, 'student': student_email, 'msg': 'Could not find student:' + student_email}
	course_id = enrollment_data[required_columns_indexes[required_columns['course_id']]]
	criterias_grades = {}
	for criteria in criterias:
		criterias_grades[criteria['assessment_criteria']] =  enrollment_data[required_columns_indexes[required_columns[criteria['assessment_criteria']]]] or 0

	student_group = frappe.db.sql("""
		SELECT grpStd.parent FROM `tabStudent Group Student` as grpStd
		INNER JOIN `tabStudent Group` as grp ON grp.name=grpStd.parent
		WHERE grp.academic_term=%(academic_term)s AND grp.course=%(course)s AND grpStd.student=%(student)s
	""",{"student": student, "academic_term": academic_term, "course": course_id}, as_dict=True)
	if not student_group or len(student_group) == 0:
		return {"error": True,  "msg": "Could not find student group for: " + student_email + ',' + str(course_id) }
	filters = {
		"student": student,
		"student_group": student_group[0]['parent'],
		'course': str(course_id),
		'academic_year': academic_year,
		'academic_term': academic_term,
		'assessment_plan': assessment_plan
		}
	if frappe.db.exists("Assessment Result", filters):
		print("grade exists")
		return {"error": False, "warning": True, "msg": "Assessment result exists for:" + student + " ," + str(course_id)}
	assessment = frappe.get_doc({
		"doctype": "Assessment Result",
		**filters
		# 'grading_scale': 'مقياس الدرجات الافتراضي',
		# "maximum_score": 100
	})
	for c in criterias_grades:
		grade = assessment.append('details')
		grade.assessment_criteria = c
		grade.score = float(criterias_grades[c] or 0)
	assessment.save(ignore_permissions=True)
	assessment.submit()
	return {"error": False}

def get_required_columns_indexes(header: list, required_columns: list):
	required_columns_indexes = {}
	for column in required_columns:
		index = header.index(column)
		required_columns_indexes[column] = index
	return required_columns_indexes

def read_content(content, extension):
		error_title = _("Template Error")
		if extension not in ("csv", "xlsx", "xls"):
			frappe.throw(_("Import template should be of type .csv, .xlsx or .xls"), title=error_title)

		if extension == "csv":
			data = read_csv_content(content)
		elif extension == "xlsx":
			data = read_xlsx_file_from_attached_file(fcontent=content)
		elif extension == "xls":
			data = read_xls_file_from_attached_file(content)

		return data

def read_file(file_path: str):
	extn = os.path.splitext(file_path)[1][1:]

	file_content = None

	file_name = frappe.db.get_value("File", {"file_url": file_path})
	if file_name:
		file = frappe.get_doc("File", file_name)
		file_content = file.get_content()

	return file_content, extn