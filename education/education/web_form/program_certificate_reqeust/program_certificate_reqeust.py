import frappe
import json
from frappe import _
def get_context(context):
	# do your magic here
	context.msg = _('The information must match the passport. If you do not have a passport, contact us')
	if context.is_new:
		student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name", 
									   "first_name", "middle_name", "last_name",
									   "first_name_arabic", "middle_name_arabic", "last_name_arabic","educational_level",
									   "student_mobile_number", "student_email_id", "nationality"], as_dict=True)
		if not student: return
		context.student_data = json.dumps(student)
