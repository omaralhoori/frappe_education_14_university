# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class DropCourse(Document):
	def before_insert(self):
		if not self.student:
			student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
			self.student = student



@frappe.whitelist()
def get_apporved_requests_count(student):
	return frappe.db.count("Drop Course", {"student": student, "status": "Approved"})

@frappe.whitelist()
def drop_course_approve(student, course, academic_term, drop_request):
	if enrollment := frappe.db.exists("Course Enrollment", {"student": student, "course": course, "academic_term": academic_term, "enrollment_status": "Enrolled"}):
		course_enrollment = frappe.get_doc("Course Enrollment", enrollment)
		course_enrollment.pull_enrollment()
		frappe.db.set_value("Drop Course", drop_request, "status", "Approved")
		return {"is_success": 1,}
	else:
		return {"is_success": 0, "error": _('Cannot find course enrollment for student')}