from education.education.doctype.student_admission.student_admission import get_program_admission_list
import frappe
from frappe import _


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
    context.show_sidebar = True
    context.admissions = get_program_admission_list()