# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DropCourse(Document):
	def before_insert(self):
		if not self.student:
			student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
			self.student = student



@frappe.whitelist()
def get_apporved_requests_count(student):
	return frappe.db.count("Drop Course", {"student": student, "status": "Approved"})