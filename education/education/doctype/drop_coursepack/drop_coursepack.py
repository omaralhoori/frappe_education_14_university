# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class DropCoursepack(Document):
	def before_insert(self):
		if not self.student:
			student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
			self.student = student



@frappe.whitelist()
def get_apporved_requests_count(student):
	return frappe.db.count("Drop Coursepack", {"student": student, "status": "Approved"})

@frappe.whitelist()
def drop_coursepack_approve(student, program, drop_request):
	if enrollment := frappe.db.exists("Program Enrollment", 
				   {"student": student, "program": program,}):
		if enrollment_applicant := frappe.db.exists("Course Enrollment Applicant", 
				   {"student": student, "program": program,}):
			if fees := frappe.db.exists("Fees", 
				   { "against_doctype_name": enrollment_applicant,}):
				fees_doc = frappe.get_doc("Fees", fees)
				fees_doc.cancel()
				fees_doc.delete(ignore_permissions=True)				
			frappe.delete_doc("Course Enrollment Applicant",enrollment_applicant)
		program_enrollment = frappe.get_doc("Program Enrollment", enrollment)
		program_enrollment.cancel()
		program_enrollment.delete(ignore_permissions=True)
		frappe.db.set_value("Drop Coursepack", drop_request, "status", "Approved")
		return {"is_success": 1,}
	else:
		return {"is_success": 0, "error": _('Cannot find program enrollment for student')}