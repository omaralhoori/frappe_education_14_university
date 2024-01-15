# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CoursepacktoInstituteTransition(Document):
	@frappe.whitelist()
	def get_student_coursepacks(self):
		enrolled_courspacks = frappe.db.get_all("Course Enrollment", {"student": self.student, }, ['name', 'course', 'graduation_grade'])
		for coursepack in enrolled_courspacks:
			transferology = frappe.get_single("Course Transfer Evaluation")
			for course in transferology.courses:
				if course.course == coursepack['course']:
					coursepack['equivalent_course'] = course.equivalent_course
					break
		return enrolled_courspacks
	
	@frappe.whitelist()
	def approve_transition(self):
		frappe.db.set_value("Student", self.student, "is_coursepack_student", 0)
		program_enrollment = frappe.get_doc({
			"doctype": "Program Enrollment",
			"student": self.student,
			"program": self.program,
			"educational_year": frappe.db.get_value("Student", self.student, "educational_year")
		})
		program_enrollment.save(ignore_permissions=True)
		program_enrollment.submit()
		for course in self.course_transitions:
			old_course_enrollment = frappe.get_doc("Course Enrollment", course.course_enrollment)
			course_enrollment = frappe.get_doc({
				"doctype": "Course Enrollment",
				"program_enrollment": program_enrollment.name,
				"enrollment_date": old_course_enrollment.enrollment_date,
				"course": course.to_course,
				"student": self.student,
				"academic_term": old_course_enrollment.academic_term,
				"academic_year": old_course_enrollment.academic_year,
				"graduation_grade": old_course_enrollment.graduation_grade,
				"enrollment_status": old_course_enrollment.enrollment_status
			})
			course_enrollment.save(ignore_permissions=True)
		self.db_set('status', 'Approved')
		return True