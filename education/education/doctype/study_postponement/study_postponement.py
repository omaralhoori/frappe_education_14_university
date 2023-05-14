# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class StudyPostponement(Document):
	def before_insert(self):
		if not self.student:
			student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
			self.student = student


@frappe.whitelist()
def get_apporved_requests_count(student):
	return frappe.db.count("Study Postponement", {"student": student, "status": "Approved"})


def check_postponed_semester(student):
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")

	return False if frappe.db.get_value("Study Postponement", 
				    {"student": student, "status": "Approved", "academic_term": current_academic_term}) else True
