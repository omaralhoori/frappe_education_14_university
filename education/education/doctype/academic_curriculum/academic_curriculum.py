# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

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
				frappe.throw(_('Selected courses are less than required courses in elective pool'))
		return True
