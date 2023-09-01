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
		return
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
	if not enrolled_program: 
		frappe.msgprint(_('You are not registered in any program'))
		return []
	if frappe.db.get_single_value("Education Settings", "fetch_courses_from_program", cache=True):
		return fetech_program_based_courses(student, enrolled_program)
	else:
		return fetech_academic_curriculum_based_courses(student, enrolled_program)

def fetech_program_based_courses(student, enrolled_program):
	graduation_for_prerequisites = frappe.db.get_single_value("Education Settings", "graduation_for_prerequisites", cache=True)

	graduation_stmt = ""
	if graduation_for_prerequisites:
		graduation_stmt = "and tce.graduation_date is not null"
	return frappe.db.sql("""
			SELECT 	tcrs.name as course_id,tcrs.course_code, tcrs.course_name, tcrs.course_language, tcrs.total_course_hours,
		tpoec.pool_name, tpoec.required_course_count,tpoec.requirement_base, tacc.required as compulsory,
		IF (tcrs.name IN (
				SELECT course FROM `tabCourse Enrollment Applied Course` as ceap 
				INNER JOIN `tabCourse Enrollment Applicant` as cea on cea.name=ceap.parent WHERE cea.student=%(student)s AND cea.program=%(program)s AND cea.application_status NOT IN ("Rejected", "Approved")
				  ), 1, 0) as applicant_status,
		IF (tcrs.name IN (SELECT course FROM `tabCourse Enrollment` WHERE student=%(student)s AND program=%(program)s AND enrollment_status not in ('Failed', 'Pulled') ), 1, 0) as enrollment_status,
		IF ((0 not in (
			select IF(tce.course IS NULL , 0, 1) FROM `tabAcademic Course Prerequisite` tacp 
			LEFT JOIN `tabCourse Enrollment` as tce on tacp.course=tce.course and tce.student=%(student)s {graduation_stmt}
			WHERE tacp.parent=tcrs.name
			)), 1, 0) as enrollable
			FROM `tabProgram` as tac
			INNER JOIN `tabProgram Course` as tacc ON tac.name=tacc.parent
			INNER JOIN `tabCourse` as tcrs ON tcrs.name=tacc.course
			LEFT JOIN `tabPool of Elective Courses` tpoec ON tpoec.name=tacc.pool_of_elective_courses
			WHERE tac.name=%(program)s
	""".format(graduation_stmt=graduation_stmt), {
		"program": enrolled_program,
		"student": student
	}, as_dict=True)

def fetech_academic_curriculum_based_courses(student, enrolled_program):
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
	graduation_for_prerequisites = frappe.db.get_single_value("Education Settings", "graduation_for_prerequisites", cache=True)
	if not current_academic_term: return []
	semester = frappe.db.get_value("Academic Term", current_academic_term, "semester")
	educational_year = frappe.db.get_value("Program Enrollment", {"student": student, "program": enrolled_program}, "educational_year")
	educational_year_order = frappe.db.get_value("Educational Year", educational_year, "year_order")
	graduation_stmt = ""
	if graduation_for_prerequisites:
		graduation_stmt = "and tce.graduation_date is not null"
	if not educational_year or not semester: return []

	return frappe.db.sql("""
			SELECT 	tcrs.name as course_id,tcrs.course_code, tcrs.course_name, tcrs.course_language, tcrs.total_course_hours,
		tpoec.pool_name, tpoec.required_course_count, tey.year_name, tacc.compulsory , tacc.force_to_select_course,
		IF (tcrs.name IN (
				SELECT course FROM `tabCourse Enrollment Applied Course` as ceap 
				INNER JOIN `tabCourse Enrollment Applicant` as cea on cea.name=ceap.parent WHERE cea.student=%(student)s AND cea.program=%(program)s AND cea.application_status NOT IN ("Rejected", "Approved")
				  ), 1, 0) as applicant_status,
		IF (tcrs.name IN (SELECT course FROM `tabCourse Enrollment` WHERE student=%(student)s AND program=%(program)s AND enrollment_status not in ('Failed', 'Pulled') ), 1, 0) as enrollment_status,
		IF ((0 not in (
			select IF(tce.course IS NULL , 0, 1) FROM `tabAcademic Course Prerequisite` tacp 
			LEFT JOIN `tabCourse Enrollment` as tce on tacp.course=tce.course and tce.student=%(student)s {graduation_stmt}
			WHERE tacp.parent=tcrs.name
			)), 1, 0) as enrollable
			FROM `tabAcademic Curriculum` as tac
			INNER JOIN `tabAcademic Curriculum Course` as tacc ON tac.name=tacc.parent
			INNER JOIN `tabCourse` as tcrs ON tcrs.name=tacc.course
			LEFT JOIN `tabPool of Elective Courses` tpoec ON tpoec.name=tacc.pool_of_elective_courses
			INNER JOIN `tabEducational Year` tey ON tac.educational_year=tey.name
			WHERE tac.program=%(program)s AND tac.educational_semester=%(semester)s AND tey.year_order <= {year_order}
	""".format(year_order=educational_year_order, graduation_stmt=graduation_stmt), {
		"program": enrolled_program,
		"semester": semester,
		"student": student
	}, as_dict=True)


