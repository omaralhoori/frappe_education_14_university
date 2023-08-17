# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
class CourseGraduationTool(Document):
	pass


@frappe.whitelist()
def get_students(get_type, enrollment_status, student_group=None, academic_term=None):
	filters = {"student_group": student_group, "enrollment_status":  enrollment_status}
	if get_type =="Academic Term":
		filters = {"academic_term": academic_term,  "enrollment_status":  enrollment_status}
	return frappe.db.get_all("Course Enrollment", filters, ['student', 'course', 'name'])

@frappe.whitelist()
def graduate_students(students, graduation_date, threshold, get_type, student_group=None, academic_term=None):
	students = json.loads(students)
	unhandeled_students = []
	filters = {"student_group": student_group,}
	if get_type =="Academic Term":
		filters = {"academic_term": academic_term, }
	for student in students:
		filters['course']= student.get('course')
		filters['student']= student.get('student')
		total_score = frappe.db.get_value("Assessment Result", filters, ['total_score'])
		if not total_score and total_score is None:
			unhandeled_students.append({"student": student.get("student"), "enrollment": student.get("enrollment"),'course': student.get('course'), "status" :"unable to find Assessment Result"})
		else:
			enrollment = frappe.get_doc("Course Enrollment", student.get('enrollment'))
			enrollment.graduation_grade = total_score
			if float(total_score) >= float(threshold):
				enrollment.enrollment_status = 'Graduated'
			else:
				enrollment.enrollment_status = 'Failed'
			enrollment.graduation_date = graduation_date
			enrollment.save()
	return unhandeled_students