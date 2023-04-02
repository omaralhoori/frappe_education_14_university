# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from education.education.doctype.fees.fees import get_fees_due_date
import frappe
from frappe.model.document import Document
from frappe import _


class CourseEnrollmentApplicant(Document):
	@frappe.whitelist()
	def enroll_student_in_courses(self):
		enrolled_program = frappe.db.get_value("Program Enrollment", {"student": self.student}, ["name"])
		if not enrolled_program: frappe.throw(_('Student is not registered in any program'), frappe.DoesNotExistError)
		#print(enrolled_program, courses, student)
		for course in self.courses:
			filters = {
				"student": self.student,
				"course": course.course,
				"program_enrollment": enrolled_program,
				"enrollment_status": "Enrolled"
			}
			if not frappe.db.exists("Course Enrollment", filters):
				filters.update({
					"doctype": "Course Enrollment",
					"enrollment_date": frappe.utils.nowdate()
				})
				frappe.get_doc(filters).save(ignore_permissions=True)
		self.db_set("application_status", "Approved")
		frappe.msgprint(_("Student enrolled successfully"))

	def register_courses(self, courses):
		removed_courses = [courseObj.course for courseObj in self.courses if courseObj.course not in courses]
		added_courses = [course for course in courses if not any(courseObj.course == course for courseObj in self.courses)]
		
		self.courses = [courseObj for courseObj in self.courses if courseObj.course not in removed_courses]

		for course in added_courses:
			row = self.append("courses")
			row.course = course
		
		self.create_added_removed_courses_fees(added_courses, removed_courses)

	def create_added_removed_courses_fees(self, added_courses, removed_courses):
		added_total_fees, added_hour_rate, added_total_hours = self.calculate_courses_fees(added_courses)
		removed_total_fees, removed_hour_rate, removed_total_hours = self.calculate_courses_fees(removed_courses)
		fees_name = frappe.db.exists("Fees", {"student": self.student, "against_doctype": "Course Enrollment Applicant",
					"against_doctype_name": self.name,"program": self.program})
		new_amount = added_total_fees - removed_total_fees
		if fees_name:
			fees_doc = frappe.get_doc("Fees", fees_name)
			# Unpaid Fees and new added-removed courses are greater than zero or less than zero
			if fees_doc.outstanding_amount > 0:
				for cmpnt in fees_doc.components:
					if cmpnt.fees_category == "Hour Rate":
						cmpnt.amount += new_amount
						cmpnt.description = ""
						fees_doc.grand_total += new_amount
						fees_doc.save(ignore_permissions=True)
						fees_doc.make_extra_amount_gl_entries(new_amount)
						return
			# Paid Fees and added-removed courses are greater than zero	
			elif new_amount > 0:
				fees_doc = frappe.get_doc({
				"doctype": "Fees",
				"student": self.student,
				"against_doctype": "Course Enrollment Applicant",
				"against_doctype_name": self.name,
				"program": self.program,
				"due_date": get_fees_due_date()
			})
				component = fees_doc.append("components")
				component.fees_category = 'Hour Rate'
				component.description = _("The total number of registered hours: {0}, hour rate: {1}").format(added_total_hours - removed_total_hours, added_hour_rate)
				component.amount = new_amount

				fees_doc.save(ignore_permissions=True)
				fees_doc.submit()
				self.paid= 0
			# Paid Fees and added-removed courses are lower than zero
			else:
				fees_doc.make_extra_amount_reverse_gl_entries(removed_total_fees - added_total_fees)
				
		
	def after_insert(self):
		self.create_fees_record()

	def calculate_courses_fees(self, courses):
		total_fees = 0
		total_hours =0
		hour_rate = 0
		if len(courses) == 0: return total_fees, hour_rate, total_hours
		current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
		current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
		results = frappe.db.sql("""
			SELECT tbl1.total_courses_hours * tbl2.amount as total_fees, tbl1.total_courses_hours,  tbl2.amount as hour_rate FROM 
			(SELECT SUM(tcurs.total_course_hours) AS total_courses_hours 
			FROM `tabCourse` AS tcurs
				WHERE tcurs.name IN ({courses})
				) as tbl1,
				(SELECT cmpnt.amount
					FROM `tabFee Component` as cmpnt
					INNER JOIN `tabFee Structure` as tfs ON tfs.name=cmpnt.parent
				WHERE cmpnt.fees_category='Hour Rate' 
				AND (program=%(program)s or program='' or program is null) 
				AND (academic_year=%(current_academic_year)s or academic_year='' or academic_year is null) 
				AND (academic_term=%(current_academic_term)s or academic_term='' or academic_term is null) 
					ORDER BY program DESC, academic_year DESC, academic_term DESC LIMIT 1) as tbl2
		""".format(courses=",".join([f'"{course}"' for course in courses])), {
			"program": self.program,
			"current_academic_year": current_academic_year,
			"current_academic_term": current_academic_term
		}, as_dict=True)
		if results:
			total_fees = float(results[0]['total_fees'])
			hour_rate = float(results[0]['hour_rate'])
			total_hours = float(results[0]['total_courses_hours'])
		return total_fees, hour_rate, total_hours

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
	


@frappe.whitelist()
def register_student_courses(courses):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student}, ["program"])
	if not enrolled_program: 
		return {"error": _('You are not registered in any program')}

	academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
	academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
	enrollment_start_date = frappe.db.get_value("Academic Term", academic_term, "enrollment_start_date")
	enrollment_end_date = frappe.db.get_value("Academic Term", academic_term, "enrollment_end_date")
	enrollment_applicant = None
	if  frappe.utils.getdate()  > enrollment_end_date or frappe.utils.getdate() < enrollment_start_date:
		return {"error": _("Enrollment is not allowed in this date.")}
	if not frappe.db.get_single_value("Education Settings","allow_adding_and_removing"):
		if frappe.db.exists("Course Enrollment Applicant", {"student": student, "program": enrolled_program, "academic_year":academic_year, "academic_term": academic_term}):
			return {"error": _('You have already registered the courses for this semester')}
	else:
		enrollment = frappe.db.exists("Course Enrollment Applicant", {"student": student, "program": enrolled_program, "academic_year":academic_year, "academic_term": academic_term})
		if enrollment:
			enrollment_applicant = frappe.get_doc("Course Enrollment Applicant", enrollment)
	#print(enrolled_program, courses, student)
	courses = json.loads(courses)
	if not enrollment_applicant:
		filters = {
				"doctype": "Course Enrollment Applicant",
				"application_date": frappe.utils.nowdate(),
				"student": student,
				"program": enrolled_program,
				"academic_term": academic_term,
				"academic_year": academic_year
			}
		enrollment_applicant = frappe.get_doc(filters)
		for course in courses:
			course_row = enrollment_applicant.append("courses")
			course_row.course = course
	else:
		enrollment_applicant.application_date = frappe.utils.nowdate()
		enrollment_applicant.register_courses(courses)

	enrollment_applicant.save(ignore_permissions=True)
	pay_msg = get_pay_fees_msg(student)
	return {"msg": _("Courses registered successfully.") + " " + pay_msg, "pay": 1 if pay_msg else 0}

def get_pay_fees_msg(student):
	fees_msg = ""
	res = frappe.db.sql("""
		select sum(outstanding_amount) as amount FROM `tabFees` WHERE student=%(student)s AND outstanding_amount > 0
	""", {"student": student}, as_dict=True)
	if res and res[0].get('amount') and  res[0].get('amount') > 0:
		fees_msg = _("Please pay courses fees {0}here{1}.").format("<a href='/fees'>", "</a>")
	return fees_msg