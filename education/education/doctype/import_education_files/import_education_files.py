# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
from frappe import _
from frappe.utils.csvutils import read_csv_content
from frappe.utils.data import cint
from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file

class ImportEducationFiles(Document):
	pass


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
		create_course_enrollment(student, program_enrollment, term_info[0], academic_term, [course])
	else:
		frappe.throw("error")
	frappe.db.commit()
	return {"error": False, "student": student, "course": course}
def check_program_enrolled(student, term_info, academic_term):
	program_enrollment = frappe.db.get_value("Program Enrollment", {"student": student}, ['name'])
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

def create_course_enrollment(student, enrolled_program, academic_year, academic_term, courses):
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