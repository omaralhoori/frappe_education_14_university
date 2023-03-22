# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from education.education.doctype.fees.fees import get_fees_due_date
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
		total_fees, application_fees, hour_rate, total_hours  = self.calculate_total_fees()
		if total_fees > 0 or application_fees > 0:
			fees_doc = frappe.get_doc({
				"doctype": "Fees",
				"student": self.student,
				"against_doctype": "Course Enrollment Applicant",
				"against_doctype_name": self.name,
				"program": self.program,
				"due_date": get_fees_due_date()
			})
			if total_fees > 0:
				component = fees_doc.append("components")
				component.fees_category = 'Hour Rate'
				component.description = _("The total number of registered hours: {0}, hour rate: {1}").format(total_hours, hour_rate)
				component.amount = total_fees
			if application_fees > 0:
				component = fees_doc.append("components")
				component.fees_category = 'Application Fee'
				component.amount = application_fees
			fees_doc.save(ignore_permissions=True)
			fees_doc.submit()

	def calculate_total_fees(self):
		total_fees = 0
		application_fees = 0
		total_hours =0
		hour_rate = 0
		current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
		current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
		results = frappe.db.sql("""
			SELECT tbl1.total_courses_hours * tbl2.amount as total_fees, tbl3.application_fee, tbl1.total_courses_hours,  tbl2.amount as hour_rate FROM 
			(SELECT SUM(tcurs.total_course_hours) AS total_courses_hours 
			FROM `tabCourse Enrollment Applied Course` AS tceac
				INNER JOIN `tabCourse` AS tcurs ON tcurs.name=tceac.course
				WHERE tceac.parent=%(applicant_name)s
				) as tbl1,
				(SELECT cmpnt.amount
					FROM `tabFee Component` as cmpnt
					INNER JOIN `tabFee Structure` as tfs ON tfs.name=cmpnt.parent
				WHERE cmpnt.fees_category='Hour Rate' 
				AND (program=%(program)s or program='' or program is null) 
				AND (academic_year=%(current_academic_year)s or academic_year='' or academic_year is null) 
				AND (academic_term=%(current_academic_term)s or academic_term='' or academic_term is null) 
					ORDER BY program DESC, academic_year DESC, academic_term DESC LIMIT 1) as tbl2,
				(SELECT cmpnt.amount as application_fee
					FROM `tabFee Component` as cmpnt
					INNER JOIN `tabFee Structure` as tfs ON tfs.name=cmpnt.parent
				WHERE cmpnt.fees_category='Application Fee' 
				AND (program=%(program)s or program='' or program is null) 
				AND (academic_year=%(current_academic_year)s or academic_year='' or academic_year is null) 
				AND (academic_term=%(current_academic_term)s or academic_term='' or academic_term is null) 
					ORDER BY program DESC, academic_year DESC, academic_term DESC LIMIT 1) as tbl3
		""", {
			"applicant_name": self.name,
			"program": self.program,
			"current_academic_year": current_academic_year,
			"current_academic_term": current_academic_term
		}, as_dict=True)
		if results:
			total_fees = float(results[0]['total_fees'])
			application_fees = float(results[0]['application_fee'])
			hour_rate = float(results[0]['hour_rate'])
			total_hours = float(results[0]['total_courses_hours'])
		return total_fees, application_fees, hour_rate, total_hours
	
@frappe.whitelist()
def has_student_registred_courses(student):
	current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
	enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student}, ["program"], cache=True)
	return True if frappe.db.exists("Course Enrollment Applicant", {"program": enrolled_program, "academic_year":current_academic_year, "academic_term": current_academic_term}) else False
	