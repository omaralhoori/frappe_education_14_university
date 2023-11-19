# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class StudentCertificateRequest(Document):
	def before_insert(self):
		if not self.student:
			self.student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
		if self.student and not self.program:
			program_data = frappe.db.get_value("Program Enrollment", {"student": self.student}, ["name", "cgpa", "academic_term"])
			if program_data:
				self.program = program_data[0]
				self.cgpa = program_data[1]
				self.academic_term = program_data[2]

	def after_insert(self):
		program = frappe.db.get_value("Program Enrollment", self.program, "program")
		add_program_certifcate_fee(self.student, program, self.name)

def add_program_certifcate_fee(student, program, request_name):
	fee_strct_doc = None
	if fee_strct := frappe.db.exists("Fee Structure", {"program": program}):
		fee_strct_doc= frappe.get_doc("Fee Structure", fee_strct)
	if not fee_strct_doc: return

	
	program_cmpnt = None
	for fee_cmpnt in fee_strct_doc.components:
		if fee_cmpnt.fees_category == 'Program Certificate':
			program_cmpnt = fee_cmpnt
			break
	
	if not program_cmpnt: return
	fees_doc = frappe.get_doc({
	"doctype": "Fees",
	"student": student,
	"against_doctype": "Student Certificate Request",
	"against_doctype_name": request_name,
	"program": program,
	"due_date": frappe.utils.nowdate(),
	})
	component = fees_doc.append("components")
	component.fees_category = 'Program Certificate'
	component.description = ''
	component.amount = program_cmpnt.amount
	component.receivable_account = program_cmpnt.receivable_account
	component.cost_center = program_cmpnt.cost_center
	component.income_account = program_cmpnt.income_account
	fees_doc.calculate_total()
	fees_doc.save(ignore_permissions=True)
	fees_doc.submit()