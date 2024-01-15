# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from education.education.doctype.fees.fees import get_fees_accounts
import frappe
from frappe.model.document import Document
import os
from frappe import _
from frappe.utils.csvutils import read_csv_content
from frappe.utils.data import cint
from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file
import pandas as pd

class ImportEducationFiles(Document):
	pass

@frappe.whitelist()
def import_grades_file(data_file, assessment_plan):
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
	errors = []
	for enrollment_data in data:
		added = add_grades_data(required_columns, required_columns_indexes, enrollment_data, assessment_plan, criterias)
		if added.get('error'): errors.append(added.get('msg'))
		frappe.db.commit()
	print("Not added enrollments: ")
	print(errors)
def add_grades_data(required_columns, required_columns_indexes, enrollment_data, assessment_plan, criterias):
	academic_term = enrollment_data[required_columns_indexes[required_columns['academic_term']]]
	academic_year = enrollment_data[required_columns_indexes[required_columns['academic_year']]]
	student_email = enrollment_data[required_columns_indexes[required_columns['student']]]
	if not student_email:
		return {"error": False}
	student = frappe.db.get_value("Student", {"student_email_id": student_email}, ['name'])
	if not student:
		return {'error': True, 'student': student_email, 'msg': 'could not find student'}
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
		return {"error": True,  "msg": student_email + ',' + str(course_id) }
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
		return {"error": False}
	assessment = frappe.get_doc({
		"doctype": "Assessment Result",
		**filters
		# 'grading_scale': 'مقياس الدرجات الافتراضي',
		# "maximum_score": 100
	})
	for c in criterias_grades:
		grade = assessment.append('details')
		grade.assessment_criteria = c
		grade.score = criterias_grades[c]
	assessment.save(ignore_permissions=True)
	assessment.submit()
	return {"error": False}
@frappe.whitelist()
def import_certificate_file(data_file, add_payment=False):
	content, extn = read_file(data_file)
	data = read_content(content, extn)
	required_columns = {'amount': 'Amount', 'student': 'Student', 'paid': 'Paid'}
	required_columns_indexes = get_required_columns_indexes(data[0], list(required_columns.values()))
	data = data[1:]
	errors = []
	students = []
	emails = []
	for enrollment_data in data:
		student_column = enrollment_data[required_columns_indexes[required_columns['student']]]
		student = frappe.db.get_value("Student", {"student_email_id":student_column}, ['name'])
		students.append(student)
		emails.append(student_column)
		# added = add_program_certifcate_fee(required_columns, required_columns_indexes, enrollment_data, add_payment)
		# if added.get('error'): errors.append(added)
	data = {
    'Student': students,
    'Student Email': emails,
}
	df = pd.DataFrame(data)

	# Specify the Excel file name and sheet name
	excel_file_name = 'students.xlsx'
	sheet_name = 'Sheet1'

	# Save the DataFrame to Excel
	df.to_excel(excel_file_name, sheet_name=sheet_name, index=False)
	# print("Not added enrollments: ")
	# print(errors)

def add_program_certifcate_fee(required_columns, required_columns_indexes, enrollment_data, add_payment=False):
	
	amount = enrollment_data[required_columns_indexes[required_columns['amount']]]
	paid = enrollment_data[required_columns_indexes[required_columns['paid']]]
	student_column = enrollment_data[required_columns_indexes[required_columns['student']]]
	if not student_column: return {"error": True, "student": student_column, 'msg': 'student null'}
	student = frappe.db.get_value("Student", {"student_email_id":student_column}, ['name'])
	if not student: return {"error": True, "student": student_column, 'msg': 'student not found'}
	main_prgram = frappe.db.get_single_value("Education Settings", "main_program")
	program = frappe.db.get_value("Program Enrollment", {"student": student, "program": main_prgram}, ['program'])
	if not program: return {"error": True, "student": student, 'msg': 'program not enrolled'}
	accounts = get_fees_accounts('Program Certificate', program)
	if not accounts: return {"error": True, "student": student, 'msg': 'accounts not found'}
	# if check_if_has_fees(student, 'Program Certificate'):
	# 	return {"error": False, "student": student}
	fees_doc = None
	# fees_new = False
	# if frappe.db.exists("Fees", {"student": student,}):
	# 	fees_doc = frappe.get_doc("Fees", {"student": student,})
	fees_new = True
	fees_doc = frappe.get_doc({
	"doctype": "Fees",
	"student": student,
	"against_doctype": "Student",
	"against_doctype_name": student,
	"program": program,
	"due_date": frappe.utils.nowdate(),
	})
	if float(amount) > 0:
		component = fees_doc.append("components")
		component.fees_category = 'Program Certificate'
		component.description = ''
		component.amount = float(amount)
		component.receivable_account = accounts[1]
		component.cost_center = accounts[3]
		component.income_account = accounts[2]
	fees_doc.calculate_total()
	fees_doc.save(ignore_permissions=True)
	if fees_new:
		fees_doc.submit()
	if add_payment:
		if paid and float(paid) > 0:
			fees_doc.pay_fee(float(paid))
	frappe.db.commit()
	return {"error": False, "student": student}

def check_if_has_fees(student, fees_category):
	results = frappe.db.sql("""
		SELECT cmpnt.name FROM `tabFee Component` as cmpnt
		INNER JOIN `tabFees` as tfs ON tfs.name=cmpnt.parent
		WHERE cmpnt.fees_category=%(fees_category)s AND tfs.student=%(student)s
	""",{"student": student, "fees_category": fees_category})

	if len(results)> 0:
		return True
	return False

@frappe.whitelist()
def import_course_enrollment(data_file, create_fees=0):
	content, extn = read_file(data_file)
	data = read_content(content, extn)

	required_columns = {'course': 'Course', 'student': 'Student', 'academic_term': 'Academic Term',
		      'enrollment_status': 'Enrollment Status', 'graduation_grade': 'Graduation Grade' }
	required_columns_indexes = get_required_columns_indexes(data[0], list(required_columns.values()))
	data = data[1:]
	errors = []
	for enrollment_data in data:
		added = add_enrollment_data(required_columns, required_columns_indexes, enrollment_data, create_fees=create_fees)
		if added.get('error'): errors.append(added)
	print("Not added enrollments: ")
	print(errors)

def add_enrollment_data(required_columns, required_columns_indexes, enrollment_data, create_fees=0):
	course = enrollment_data[required_columns_indexes[required_columns['course']]]
	student = enrollment_data[required_columns_indexes[required_columns['student']]]
	if not student: return {"error": True, "student": student, "course": course}
	student = frappe.db.get_value("Student", {"student_email_id":student}, ['name'])
	academic_term = enrollment_data[required_columns_indexes[required_columns['academic_term']]]
	enrollment_status = enrollment_data[required_columns_indexes[required_columns['enrollment_status']]]
	graduation_grade = enrollment_data[required_columns_indexes[required_columns['graduation_grade']]]
	if frappe.db.exists("Course Enrollment", {"course": course, "student": student, "academic_term": academic_term}): return {"error": True, "student": student, "course": course}
	term_info = frappe.db.get_value('Academic Term', academic_term, ['academic_year', 'term_start_date', 'term_end_date'])
	try:
		program_enrollment = check_program_enrolled(student, term_info, academic_term)
	except:
		print("error with student: " + str(student))
		return {"error": True, "student": student, "course": course}
	enrollment_doc = frappe.get_doc({
		'doctype': 'Course Enrollment',
		"program_enrollment": program_enrollment,
		"enrollment_date": term_info[1],
		"academic_year": term_info[0],
		"academic_term": academic_term,
		"course": course,
		"student": student,
		"enrollment_status": enrollment_status,
		"graduation_grade": graduation_grade,
		'graduation_date': term_info[2]
	})
	enrollment_doc.save(ignore_permissions=True)
	if cint(create_fees):
		create_course_enrollment_fees(student, program_enrollment, term_info[0], academic_term, [course])
	else:
		pass
		#frappe.throw("error")
	frappe.db.commit()
	return {"error": False, "student": student, "course": course}
def check_program_enrolled(student, term_info, academic_term):
	main_prgram = frappe.db.get_single_value("Education Settings", "main_program")
	program_enrollment = frappe.db.get_value("Program Enrollment", {"student": student, "program": main_prgram}, ['name'])
	if program_enrollment: return program_enrollment
	program_enrollment = frappe.get_doc({
		"doctype": "Program Enrollment",
		"student": student,
		"enrollment_date": term_info[1],
		"program": frappe.db.get_all("Program", pluck='name')[0],
		"educational_year": frappe.db.get_value("Student", student, ['educational_year']) or frappe.db.get_value('Educational Year', {'year_order': 1}, ['name'], cache=True),
		"academic_year": term_info[0],
		"academic_term": academic_term,
	})

	program_enrollment.save(ignore_permissions=True)
	program_enrollment.submit()
	return program_enrollment.name

def create_course_enrollment_fees(student, enrolled_program, academic_year, academic_term, courses):
	enrollment_applicant = None
	program = frappe.db.get_value("Program Enrollment", enrolled_program, ['program'])

	enrollment = frappe.db.exists("Course Enrollment Applicant", {
		"application_status": ["!=", "Rejected"], 
		"student": student, "program": program, 
		"academic_year":academic_year, "academic_term": academic_term})
	if enrollment:
		enrollment_applicant = frappe.get_doc("Course Enrollment Applicant", enrollment)
	#print(enrolled_program, courses, student)
	groups = get_course_group(student, program, academic_year, academic_term, courses)
	if not enrollment_applicant:
		filters = {
				"doctype": "Course Enrollment Applicant",
				"application_date": frappe.utils.nowdate(),
				"student": student,
				"program": program,
				"academic_term": academic_term,
				"academic_year": academic_year,
				'application_status': 'Approved'
			}
		enrollment_applicant = frappe.get_doc(filters)
		for course in courses:
			course_row = enrollment_applicant.append("courses")
			course_row.course = course
			if groups.get(course):
				course_row.group = groups.get(course)
				student_group = frappe.get_doc("Student Group", groups.get(course))
				if not any(student.student == student for student in student_group.students):
					student_row = student_group.append("students")
					student_row.student = student
					student_row.active = 1
					student_group.save(ignore_permissions=True)
				else:
					print("student exists in group: " + student_group.name)
					print(student)
	else:
		enrollment_applicant.application_date = frappe.utils.nowdate()
		old_courses = [course.course for course in enrollment_applicant.courses]
		old_courses.extend(courses)
		print(old_courses)
		enrollment_applicant.register_courses(old_courses, groups)
		for course in courses:
			if groups.get(course):
				student_group = frappe.get_doc("Student Group", groups.get(course))
				if not any(student.student == student for student in student_group.students):
					student_row = student_group.append("students")
					student_row.student = student
					student_row.active = 1
					student_group.save(ignore_permissions=True)
				else:
					print("student exists in group: " + student_group.name)
					print(student)

	enrollment_applicant.save(ignore_permissions=True)
	frappe.db.commit()

def get_course_group(student, program, academic_year, academic_term, courses):
	student_gender = frappe.db.get_value("Student", student, "gender")
	gender_name = ( " - " + student_gender) if student_gender else "" 
	groups = {}
	for course in courses:
		filters = {
			"academic_year": academic_year,
			"academic_term": academic_term,
			"group_gender": student_gender,
			"group_based_on": "Course",
			"course": str(course),
			"program": program,
		}
		student_group = frappe.db.sql("""
			select name from `tabStudent Group` where
			program=%(program)s AND academic_year=%(academic_year)s AND academic_term=%(academic_term)s AND group_based_on=%(group_based_on)s
			AND course=%(course)s AND (group_gender=%(group_gender)s or group_gender is NULL)
		""", filters, as_dict=True)
		#frappe.db.exists("Student Group", filters)
		if len(student_group) > 0:
			groups[course] = student_group[0]['name']
		else:
			print(course, academic_term, academic_year)
			filters['doctype'] = 'Student Group'
			filters["student_group_name"] = str(course) + " - " + academic_term + gender_name
			student_group_doc = frappe.get_doc(filters)
			student_group_doc.save(ignore_permissions=True)
			frappe.db.commit()
			groups[course] = student_group_doc.name
	return groups
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