# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from education.education.doctype.program_graduation_request.graduation_certificate import create_program_certificate

class ProgramGraduationRequest(Document):
	def on_submit(self):
		if len(self.students) == 0:
			frappe.throw("Students table is empty.")
		self.graduate_students()
	def graduate_students(self):
		for student in self.students:
			#enrollment = frappe.db.set_value("graduated")
			certificate_file = create_program_certificate(student.enrollment, self.certificate_creation_date, self.program)
			frappe.db.set_value("Program Enrollment",student.enrollment, {
				"graduated": 1,
				"graduation_date": self.certificate_creation_date,
				"certificate": certificate_file
				})
@frappe.whitelist()
def get_students(program, courses):
	students = frappe.db.sql("""
		select prm.student, crs.graduated_courses,std.student_name,CONCAT(std.first_name_arabic, " ", std.middle_name_arabic," ", std.last_name_arabic) as student_name_arabic, ROUND(prm.cgpa, 2) as cgpa, prm.name
		FROM `tabProgram Enrollment` as prm
		INNER JOIN `tabStudent` as std on prm.student=std.name
		INNER JOIN (
				select program_enrollment, count(DISTINCT course) as graduated_courses
					FROM `tabCourse Enrollment`
					WHERE enrollment_status='Graduated'
					GROUP BY program_enrollment
						   ) as crs ON crs.program_enrollment= prm.name
		WHERE prm.program=%(program)s and crs.graduated_courses >= {courses} and prm.graduated=0
""".format(courses=courses), {"program": program}, as_dict=True)
	return {
		"students": students
	}