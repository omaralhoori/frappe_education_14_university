# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe import _

class AcademicCurriculum(Document):
	def validate(self):
		self.validate_compulsory_courses()
	
	def validate_compulsory_courses(self):
		required_course = {}
		for course in self.courses:
			if course.pool_of_elective_courses:
				if not required_course.get(course.pool_of_elective_courses):
					required_course_count = frappe.db.get_value('Pool of Elective Courses', course.pool_of_elective_courses, ['required_course_count'])
					required_course[course.pool_of_elective_courses] = required_course_count
		for key, val in required_course.items():
			course_count = sum(map(lambda x : x.pool_of_elective_courses==key, self.courses))
			if val > course_count:
				frappe.throw(_('Selected courses are less than required courses in elective pool'), frappe.DataError)
		return True


def get_academic_curriculum_for_student(student):
	enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student}, ["program"], cache=True)
	if not enrolled_program: frappe.throw(_('You are not registered in any program'), frappe.DoesNotExistError)
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
	if not current_academic_term: return []
	semester = frappe.db.get_value("Academic Term", current_academic_term, "semester", cache=True)
	educational_year = frappe.db.get_value("Student", student, "educational_year", cache=True)
	educational_year_order = frappe.db.get_value("Educational Year", educational_year, "year_order", cache=True)
	
	if not educational_year or not semester: return []
	return frappe.db.sql("""
			SELECT 	tcrs.name as course_id,tcrs.course_code, tcrs.course_name, tcrs.course_language, tcrs.total_course_hours,
		tpoec.pool_name, tpoec.required_course_count, tey.year_name, tacc.compulsory 
			FROM `tabAcademic Curriculum` as tac
			INNER JOIN `tabAcademic Curriculum Course` as tacc ON tac.name=tacc.parent
			INNER JOIN `tabCourse` as tcrs ON tcrs.name=tacc.course
			LEFT JOIN `tabPool of Elective Courses` tpoec ON tpoec.name=tacc.pool_of_elective_courses
			INNER JOIN `tabEducational Year` tey ON tac.educational_year=tey.name
			WHERE tac.program=%(program)s AND tac.educational_semester=%(semester)s AND tey.year_order <= {year_order} AND tcrs.name NOT IN (SELECT course FROM `tabCourse Enrollment` WHERE student=%(student)s )
	""".format(year_order=educational_year_order), {
		"program": enrolled_program,
		"semester": semester,
		"student": student
	}, as_dict=True)


@frappe.whitelist()
def register_student_courses(courses):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student}, ["program"], cache=True)
	if not enrolled_program: frappe.throw(_('You are not registered in any program'), frappe.DoesNotExistError)
	#print(enrolled_program, courses, student)
	courses = json.loads(courses)
	for course in courses:
		filters = {
			"student": student,
			"course": course,
			"program_enrollment": enrolled_program
		}
		print(filters)
		if not frappe.db.exists("Course Enrollment", filters):
			filters.update({
				"doctype": "Course Enrollment",
				"enrollment_date": frappe.utils.nowdate()
			})
			frappe.get_doc(filters).save(ignore_permissions=True)
	return {"msg": _("Courses registered successfully")}