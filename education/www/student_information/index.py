import frappe
from frappe import _

def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)

    context.current_user = frappe.get_doc("User", frappe.session.user)
    context.student = frappe.get_doc("Student", {"user": frappe.session.user})
    if enrollment := frappe.db.exists("Program Enrollment", {"student": context.student.name}):
        context.program_enrollment = frappe.get_doc("Program Enrollment", enrollment)
    context.registered_courses = get_registered_courses(context.student.name)
    context.show_sidebar = True
    context.lang = frappe.lang

    return context


def get_registered_courses(student):
    return frappe.db.sql("""
        SELECT
            (SELECT COUNT(DISTINCT course) FROM `tabCourse Enrollment` WHERE student=%(student)s) AS total_courses,
            (SELECT COUNT(DISTINCT course) FROM `tabCourse Enrollment` WHERE student=%(student)s AND (enrollment_status = 'Enrolled' OR enrollment_status = 'Partially Pulled')) AS total_enrolled,
            (SELECT COUNT(DISTINCT course) FROM `tabCourse Enrollment` WHERE student=%(student)s AND (enrollment_status = 'Graduated')) AS total_graduated,
            (SELECT COUNT(DISTINCT course) FROM `tabCourse Enrollment` WHERE student=%(student)s AND (enrollment_status = 'Pulled')) AS total_pulled
    """, {"student": student}, as_dict=True)