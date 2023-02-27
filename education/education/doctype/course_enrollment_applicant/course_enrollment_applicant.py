# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class CourseEnrollmentApplicant(Document):
	@frappe.whitelist()
	def enroll_student_in_courses(self):
		enrolled_program = frappe.db.get_value("Program Enrollment", {"student": self.student}, ["name"], cache=True)
		if not enrolled_program: frappe.throw(_('Student is not registered in any program'), frappe.DoesNotExistError)
		#print(enrolled_program, courses, student)
		for course in self.courses:
			filters = {
				"student": self.student,
				"course": course.course,
				"program_enrollment": enrolled_program
			}
			if not frappe.db.exists("Course Enrollment", filters):
				filters.update({
					"doctype": "Course Enrollment",
					"enrollment_date": frappe.utils.nowdate()
				})
				frappe.get_doc(filters).save(ignore_permissions=True)
		frappe.msgprint(_("Student enrolled successfully"))

	def after_insert(self):
		self.create_fees_record()

	def create_fees_record(self):
		total_fees = self.calculate_total_fees()
		fees_doc = frappe.get_doc({
			"doctype": "Fees",
			"student": self.student,
			"against_doctype": "Course Enrollment Applicant",
			"against_doctype_name": self.name,
			"program": self.program,
			"due_date": frappe.utils.add_days(frappe.utils.nowdate(), 7)
		})
		component = fees_doc.append("components")
		component.fees_category = 'Hour Rate'
		component.amount = total_fees
		fees_doc.save(ignore_permissions=True)
		fees_doc.submit()

	def calculate_total_fees(self):
		total_fees = 0
		current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
		current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
		results = frappe.db.sql("""
			SELECT tbl1.total_courses_hours * tbl2.amount as total_fees FROM 
			(SELECT SUM(tcurs.total_course_hours) AS total_courses_hours 
			FROM `tabCourse Enrollment Applied Course` AS tceac
				INNER JOIN `tabCourse` AS tcurs ON tcurs.name=tceac.course
				WHERE tceac.parent=%(applicant_name)s
				) as tbl1,
				(SELECT cmpnt.amount
					FROM `tabFee Component` as cmpnt
					INNER JOIN `tabFee Structure` as tfs ON tfs.name=cmpnt.parent
				WHERE cmpnt.fees_category='Hour Rate' AND IF(academic_year=NULL, True, academic_year=%(current_academic_year)s) 
				AND IF(academic_term=NULL, True, academic_term=%(current_academic_term)s) LIMIT 1) as tbl2
		""", {
			"applicant_name": self.name,
			"current_academic_year": current_academic_year,
			"current_academic_term": current_academic_term
		}, as_dict=True)
		if results:
			total_fees = float(results[0]['total_fees'])
		return total_fees