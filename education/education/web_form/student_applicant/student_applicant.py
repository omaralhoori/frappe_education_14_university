import frappe
from frappe import _

def get_context(context):
	if not context.is_new: return
	# student_admission
	student_admission = frappe.local.form_dict.student_admission
	if not student_admission: frappe.throw(_('Unable to find student admission'))
	if not frappe.db.exists('Student Admission', student_admission): frappe.throw(_('Unable to find student admission'))
	student_admission = frappe.get_doc("Student Admission", student_admission)
	context.student_admission= student_admission
	
	# user
	user = frappe.get_doc('User', frappe.session.user)
	context.user = user

	context.new_applicant= True