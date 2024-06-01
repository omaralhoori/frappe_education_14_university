import frappe
import json

def get_context(context):
	if context.is_new:
		student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name"])
		if not student: return
		# enrolled_courses = frappe.db.get_all("Course Enrollment", {"student": student, "enrollment_status": "Enrolled"}, ['course'])
		context.academic_year = frappe.db.get_single_value("Education Settings", "current_drop_course_year") # "2023-24"#
		context.academic_term = frappe.db.get_single_value("Education Settings", "current_drop_course_term")
		enrolled_courses = frappe.db.sql("""
			SELECT DISTINCT crs.name as value, crs.course_name as label FROM `tabCourse Enrollment` as enrlment
			INNER JOIN `tabCourse` as crs ON crs.name = enrlment.course
			WHERE enrlment.student=%(student)s AND enrlment.enrollment_status="Enrolled" 
			AND enrlment.academic_term=%(academic_term)s
		""", {"student": student, "academic_term": context.academic_term,}, as_dict=True)
		
		context.enrolled_courses = json.dumps(enrolled_courses)