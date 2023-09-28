import frappe
import json

def get_context(context):
	if context.is_new:
		student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name"])
		if not student: return
		# enrolled_courses = frappe.db.get_all("Course Enrollment", {"student": student, "enrollment_status": "Enrolled"}, ['course'])
		enrolled_coursepacks = frappe.db.sql("""
			SELECT enrl.program as value , enrl.program as label FROM `tabProgram Enrollment` as enrl 
			INNER JOIN `tabProgram` as prog ON prog.name=enrl.program
			WHERE enrl.student=%(student)s AND prog.is_coursepack=1 
		""", {"student": student}, as_dict=True)
		
		context.enrolled_coursepacks = json.dumps(enrolled_coursepacks)