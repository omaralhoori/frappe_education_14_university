import frappe
from frappe import _

def get_context(context):
	email = frappe.local.form_dict.email
	context.certificate = ""
	if email:
		student = frappe.db.get_value("Student", {"student_email_id": email}, ['name'])
		if not student:
			context.error = _('Could not find student with provided email')
			return
		certificate = frappe.db.get_value("Program Enrollment", {
			"student": student,
			"graduated": 1
		}, ["certificate"])

		if not certificate:
			context.error = _("Could not find certificate for selected student")
			return
		context.certificate = certificate
		return
	