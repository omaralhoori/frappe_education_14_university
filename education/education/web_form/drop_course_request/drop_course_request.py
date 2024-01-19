import frappe
import json

def get_context(context):
	if context.is_new:
		student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name"])
		if not student: return
		# enrolled_courses = frappe.db.get_all("Course Enrollment", {"student": student, "enrollment_status": "Enrolled"}, ['course'])
		context.academic_year = "2023-24"#frappe.db.get_single_value("Education Settings", "current_academic_year")
		context.academic_term = "2023-24 (1st Semester)" #frappe.db.get_single_value("Education Settings", "current_academic_term")
		enrolled_courses = frappe.db.sql("""
			SELECT DISTINCT crs.name as value, crs.course_name as label FROM `tabCourse Enrollment` as enrlment
			INNER JOIN `tabCourse` as crs ON crs.name = enrlment.course
			WHERE enrlment.student=%(student)s AND enrlment.enrollment_status="Enrolled" 
			AND enrlment.academic_year=%(academic_year)s AND enrlment.academic_term=%(academic_term)s
		""", {"student": student, "academic_term": context.academic_term, "academic_year": context.academic_year}, as_dict=True)
		
		context.enrolled_courses = json.dumps(enrolled_courses)