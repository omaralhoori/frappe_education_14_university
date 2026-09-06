import frappe
from frappe import _


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	if not student:
		return context

	context.programs = get_student_program_enrollments(student)
	default_enrollment = frappe.form_dict.get("program_enrollment") or _get_default_program_enrollment(
		student, context.programs
	)
	# Ensure selected enrollment belongs to this student
	if default_enrollment and not frappe.db.exists(
		"Program Enrollment",
		{"name": default_enrollment, "student": student, "docstatus": 1},
	):
		default_enrollment = _get_default_program_enrollment(student, context.programs)
	context.selected_program_enrollment = default_enrollment

	if default_enrollment:
		data = get_student_transcript_data(student, default_enrollment)
		context.transcript_data = data["transcript_data"]
		context.terms_gpa = data["terms_gpa"]
		context.cgpa = data["cgpa"]
	else:
		context.transcript_data = {}
		context.terms_gpa = {}
		context.cgpa = 0

	return context


def get_student_program_enrollments(student):
	return frappe.db.sql(
		"""
		SELECT
			pe.name,
			pe.program,
			pe.graduated,
			pe.enrollment_date,
			pe.modified
		FROM `tabProgram Enrollment` pe
		WHERE pe.student = %(student)s
			AND pe.docstatus = 1
		ORDER BY pe.modified DESC
		""",
		{"student": student},
		as_dict=True,
	)


def _get_default_program_enrollment(student, programs=None):
	if not programs:
		programs = get_student_program_enrollments(student)
	if not programs:
		return None

	main_program = frappe.db.get_single_value("Education Settings", "main_program")
	for pe in programs:
		if pe.program == main_program:
			return pe.name

	return programs[0].name


def get_student_transcript_data(student, program_enrollment):
	if not program_enrollment:
		return {"transcript_data": {}, "terms_gpa": {}, "cgpa": 0}

	owned = frappe.db.exists(
		"Program Enrollment",
		{"name": program_enrollment, "student": student, "docstatus": 1},
	)
	if not owned:
		return {"transcript_data": {}, "terms_gpa": {}, "cgpa": 0}

	course_enrollments = frappe.db.sql(
		"""
		SELECT
			crsEnrl.enrollment_status,
			crsEnrl.partially_pulled,
			crsEnrl.academic_term,
			crsEnrl.graduation_grade,
			crsEnrl.course,
			crs.course_name,
			crs.total_course_hours
		FROM `tabCourse Enrollment` crsEnrl
		INNER JOIN `tabCourse` crs ON crs.name = crsEnrl.course
		WHERE crsEnrl.program_enrollment = %(program_enrollment)s
		ORDER BY crsEnrl.graduation_date DESC
		""",
		{"program_enrollment": program_enrollment},
		as_dict=True,
	)

	terms = {}
	terms_gpa = {}
	for enrollment in course_enrollments:
		old_grade = None
		term = enrollment["academic_term"]
		if term not in terms:
			terms[term] = []

		if enrollment["partially_pulled"] and enrollment["graduation_grade"]:
			old_grade = enrollment["graduation_grade"]
			enrollment["graduation_grade"] = float(enrollment["graduation_grade"]) * 45 / 100

		if enrollment["enrollment_status"] not in ["Graduated", "Failed", "Pulled"]:
			enrollment["enrollment_status"] = ""

		if enrollment["enrollment_status"] == "Pulled":
			enrollment["graduation_grade"] = None

		terms[term].append(enrollment)

		if enrollment["graduation_grade"]:
			if term not in terms_gpa:
				terms_gpa[term] = {
					"count": float(enrollment["total_course_hours"]),
					"grade": float(enrollment["graduation_grade"])
					* float(enrollment["total_course_hours"]),
				}
			else:
				terms_gpa[term]["count"] += float(enrollment["total_course_hours"])
				terms_gpa[term]["grade"] += float(enrollment["graduation_grade"]) * float(
					enrollment["total_course_hours"]
				)

		if enrollment["enrollment_status"] == "Pulled":
			enrollment["graduation_grade"] = "W"
		if old_grade:
			enrollment["graduation_grade"] = old_grade

	total_grades = 0
	total_courses = 0
	cgpa = 0
	for term in terms_gpa.values():
		term["gpa"] = term["grade"] / term["count"]
		total_grades += term["grade"]
		total_courses += term["count"]
	if total_courses > 0:
		cgpa = total_grades / total_courses

	stored_cgpa = frappe.db.get_value("Program Enrollment", program_enrollment, "cgpa")

	return {
		"transcript_data": terms,
		"terms_gpa": terms_gpa,
		"cgpa": stored_cgpa or cgpa,
	}


@frappe.whitelist()
def get_transcript_for_program(program_enrollment=None):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	if not student:
		frappe.throw(_("You need to be logged in as a student"), frappe.PermissionError)

	if not program_enrollment:
		frappe.throw(_("Please select a program"))

	data = get_student_transcript_data(student, program_enrollment)
	program = frappe.db.get_value("Program Enrollment", program_enrollment, "program")

	return {
		"program": program,
		"program_enrollment": program_enrollment,
		"transcript_data": data["transcript_data"],
		"terms_gpa": data["terms_gpa"],
		"cgpa": data["cgpa"],
	}
