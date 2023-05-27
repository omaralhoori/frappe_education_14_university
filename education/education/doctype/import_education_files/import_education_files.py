# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
from frappe import _
from frappe.utils.csvutils import read_csv_content
from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file

class ImportEducationFiles(Document):
	pass


@frappe.whitelist()
def import_course_enrollment(data_file, create_fees=False):
	content, extn = read_file(data_file)
	data = read_content(content, extn)

	required_columns = {'course': 'Course', 'student': 'Student', 'academic_term': 'Academic Term',
		      'enrollment_status': 'Enrollment Status', 'graduation_grade': 'Graduation Grade' }
	required_columns_indexes = get_required_columns_indexes(data[0], list(required_columns.values()))
	data = data[1:]
	count = 0
	for enrollment_data in data:
		added = add_enrollment_data(required_columns, required_columns_indexes, enrollment_data, create_fees=create_fees)
		if not added: count += 1
	print("Not added enrollments: "+ str(count))
def add_enrollment_data(required_columns, required_columns_indexes, enrollment_data, create_fees=False):
	course = enrollment_data[required_columns_indexes[required_columns['course']]]
	student = enrollment_data[required_columns_indexes[required_columns['student']]]
	academic_term = enrollment_data[required_columns_indexes[required_columns['academic_term']]]
	enrollment_status = enrollment_data[required_columns_indexes[required_columns['enrollment_status']]]
	graduation_grade = enrollment_data[required_columns_indexes[required_columns['graduation_grade']]]
	if frappe.db.exists("Course Enrollment", {"course": course, "student": student, "academic_term": academic_term}): return False
	term_info = frappe.db.get_value('Academic Term', academic_term, ['academic_year', 'term_start_date', 'term_end_date'])
	try:
		program_enrollment = check_program_enrolled(student, term_info, academic_term)
	except:
		print("error with student: " + str(student))
		return False
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
	if create_fees:
		create_course_enrollment(student, program_enrollment, term_info[0], academic_term, [course])
	frappe.db.commit()
	return True
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
	enrollment = frappe.db.exists("Course Enrollment Applicant", {
		"application_status": ["!=", "Rejected"], 
		"student": student, "program": enrolled_program, 
		"academic_year":academic_year, "academic_term": academic_term})
	if enrollment:
		enrollment_applicant = frappe.get_doc("Course Enrollment Applicant", enrollment)
	#print(enrolled_program, courses, student)
	groups = get_course_group(student, enrolled_program, academic_year, academic_term, courses)
	if not enrollment_applicant:
		filters = {
				"doctype": "Course Enrollment Applicant",
				"application_date": frappe.utils.nowdate(),
				"student": student,
				"program": enrolled_program,
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
		enrollment_applicant.application_date = frappe.utils.nowdate()
		enrollment_applicant.register_courses(courses, groups)

	enrollment_applicant.save(ignore_permissions=True)

def get_course_group(student, enrolled_program, academic_year, academic_term, courses):
	student_gender = frappe.db.get_value("Student", student, "gender")
	program = frappe.db.get_value("Program Enrollment", enrolled_program, ['program'])
	gender_name = ( " - " + student_gender) if student_gender else "" 
	groups = {}
	for course in courses:
		filters = {
			"academic_year": academic_year,
			"academic_term": academic_term,
			"group_gender": student_gender,
			"group_based_on": "Course",
			"course": course,
			"program": program,
		}
		student_group = frappe.db.exists("Student Group", filters)
		if student_group:
			groups[course] = student_group
		else:
			filters['doctype'] = 'Student Group'
			filters["student_group_name"] = course + " - " + academic_term + gender_name
			student_group_doc = frappe.get_doc(filters)
			student_group_doc.save(ignore_permissions=True)
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