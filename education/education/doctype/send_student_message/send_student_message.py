# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SendStudentMessage(Document):
	pass


@frappe.whitelist()
def send_message(doctype, docname, message):
	message = frappe.get_doc({
		"doctype": doctype,
		get_message_receiver_field_name(doctype): docname,
		"message": message,
		"send_date": frappe.utils.now()
	})
	message.insert(ignore_permissions=True)
	return True

def get_message_receiver_field_name(doctype):
	if doctype == 'Group Message': return "student_group"
	if doctype == 'Student Message': return "student"