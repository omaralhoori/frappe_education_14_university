from education.education.doctype.course_enrollment_applicant.course_enrollment_applicant import has_student_registred_courses
from education.education.doctype.academic_curriculum.academic_curriculum import get_academic_curriculum_for_student
import frappe
from frappe import _


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
    context.show_sidebar = True
    context.title = _("Course Enrollment")
    context.maximum_hours= frappe.db.get_single_value("Education Settings" ,"maximum_number_of_hours")
    context.minimum_hours= frappe.db.get_single_value("Education Settings" ,"minimum_number_of_hours")

    student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
    courses = get_academic_curriculum_for_student(student)
    context.courses_registered= has_student_registred_courses(student)
    available_courses = {}
    for course in courses:
        if not course.get('pool_name') and course.get('compulsory'):
            if not available_courses.get('Compulsory Courses'): available_courses['Compulsory Courses'] = []
            available_courses['Compulsory Courses'].append(course)
        elif course.get('pool_name'):
            if not available_courses.get(course.get('pool_name')): available_courses[course.get('pool_name')] = []
            available_courses[course.get('pool_name')].append(course)
        else:
            if not available_courses.get('Other Courses'): available_courses['Other Courses'] = []
            available_courses['Other Courses'].append(course)
    context.available_courses =  available_courses

    return context