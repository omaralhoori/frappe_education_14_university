# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CourseWithdrawRequest(Document):
	def before_insert(self):
		if not self.student:
			self.student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
