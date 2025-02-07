# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from education.education.doctype.fees.fees import get_fees_due_date
import frappe
from frappe.model.document import Document
from frappe import _


class CourseEnrollmentApplicant(Document):
	def on_update(self):
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.student_comment != self.student_comment:
			self.db_set("comment_seen", 0)
		if old_doc:
			for enrollment_row in old_doc.courses:
				found = False
				for new_enrollment in self.courses:
					if new_enrollment.course == enrollment_row.course:
						found =True
						break
				if not found:
					print("Not found", enrollment_row.course)
					self.delete_enrollment(enrollment_row=enrollment_row)
	def delete_enrollment(self, enrollment_row):
		if enrollment_row.group:
			student_group = frappe.get_doc("Student Group", enrollment_row.group)
			for student_row in student_group.students:
				if student_row.student == self.student:
					student_group.remove(student_row)
					student_group.save(ignore_permissions=True)
					break
			if course_enrollment:= frappe.db.exists("Course Enrollment", {
				"program": self.program,
				"academic_term": self.academic_term,
				"course":  enrollment_row.course,
				"student": self.student
			}):
				frappe.delete_doc("Course Enrollment", course_enrollment, ignore_permissions=True)
	@frappe.whitelist()
	def enroll_student_in_courses(self):
		enrolled_program = frappe.db.get_value("Program Enrollment", {"student": self.student, "program": self.program}, ["name"])
		if not enrolled_program: frappe.throw(_('Student is not registered in any program'), frappe.DoesNotExistError)
		#print(enrolled_program, courses, student)
		for course in self.courses:
			filters = {
				"student": self.student,
				"course": course.course,
				"program_enrollment": enrolled_program,
				"academic_year": self.academic_year,
				"academic_term": self.academic_term,
				"enrollment_status": "Enrolled"
			}
			if not frappe.db.exists("Course Enrollment", filters):
				filters.update({
					"doctype": "Course Enrollment",
					"enrollment_date": frappe.utils.nowdate()
				})
				frappe.get_doc(filters).save(ignore_permissions=True)
			if course.group:
				student_group = frappe.get_doc("Student Group", course.group)
				if not any(student.student == self.student for student in student_group.students):
					student_row = student_group.append("students")
					student_row.student = self.student
					student_row.active = 1
					student_group.save(ignore_permissions=True)
		#self.db_set("application_status", "Approved")
		self.db_set("initial_approval", 1)
		frappe.msgprint(_("Student enrolled successfully"))
	@frappe.whitelist()
	def final_enroll_student_in_courses(self):
		enrolled_program = frappe.db.get_value("Program Enrollment", {"student": self.student, "program": self.program}, ["name"])
		if not enrolled_program: frappe.throw(_('Student is not registered in any program'), frappe.DoesNotExistError)
		#print(enrolled_program, courses, student)
		for course in self.courses:
			filters = {
				"student": self.student,
				"course": course.course,
				"program_enrollment": enrolled_program,
				"academic_year": self.academic_year,
				"academic_term": self.academic_term,
				"enrollment_status": "Enrolled"
			}
			if not frappe.db.exists("Course Enrollment", filters):
				filters.update({
					"doctype": "Course Enrollment",
					"enrollment_date": frappe.utils.nowdate()
				})
				frappe.get_doc(filters).save(ignore_permissions=True)
			if course.group:
				student_group = frappe.get_doc("Student Group", course.group)
				if not any(student.student == self.student for student in student_group.students):
					student_row = student_group.append("students")
					student_row.student = self.student
					student_row.active = 1
					student_group.save(ignore_permissions=True)
		self.db_set("application_status", "Approved")
		self.db_set("initial_approval", 1)
		frappe.msgprint(_("Student enrolled successfully"))

	def register_courses(self, courses, groups):
		removed_courses = [courseObj.course for courseObj in self.courses if courseObj.course not in courses]
		added_courses = [course for course in courses if not any(courseObj.course == course for courseObj in self.courses)]
		
		self.courses = [courseObj for courseObj in self.courses if courseObj.course not in removed_courses]

		for course in added_courses:
			row = self.append("courses")
			row.course = course
			if groups.get(course):
				row.group = groups.get(course)
		if not self.student_has_scholarship():
			self.create_added_removed_courses_fees(added_courses, removed_courses)

	def create_added_removed_courses_fees(self, added_courses, removed_courses):
		added_total_fees, added_hour_rate, added_total_hours, course_receivable_account, course_cost_center, course_income_account = self.calculate_courses_fees(added_courses)
		removed_total_fees, removed_hour_rate, removed_total_hours, _course_receivable_account, _course_cost_center, _course_income_account = self.calculate_courses_fees(removed_courses)
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
						if len(added_courses) > 0:
							fees_doc.make_extra_amount_gl_entries(new_amount, course_receivable_account, course_cost_center, course_income_account)
						else:
							fees_doc.make_extra_amount_gl_entries(new_amount, _course_receivable_account, _course_cost_center, _course_income_account)
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
				component.receivable_account = course_receivable_account
				component.cost_center = course_cost_center
				component.income_account = course_income_account

				fees_doc.save(ignore_permissions=True)
				fees_doc.submit()
				self.paid= 0
			# Paid Fees and added-removed courses are lower than zero
			else:
				if len(added_courses) > 0:
					fees_doc.make_extra_amount_reverse_gl_entries(removed_total_fees - added_total_fees, course_receivable_account, course_cost_center, course_income_account)
				else:
					fees_doc.make_extra_amount_reverse_gl_entries(removed_total_fees - added_total_fees, _course_receivable_account, _course_cost_center, _course_income_account)
				
		
	def after_insert(self):
		if not self.student_has_scholarship():
			self.create_fees_record()
	def student_has_scholarship(self):
		has_scholarship = frappe.db.get_value("Program Enrollment", {"program": self.program, "student": self.student}, ['has_scholarship'])
		if has_scholarship: return True
		return False
	def calculate_courses_fees(self, courses):
		total_fees = 0
		total_hours =0
		hour_rate = 0
		course_receivable_account, course_cost_center, course_income_account = None, None, None
		if len(courses) == 0: return total_fees, hour_rate, total_hours, course_receivable_account, course_cost_center, course_income_account
		current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
		current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
		results = frappe.db.sql("""
			SELECT tbl1.total_courses_hours * tbl2.amount as total_fees, tbl1.total_courses_hours,  tbl2.amount as hour_rate,
			  tbl2.receivable_account as course_receivable_account, tbl2.cost_center as course_cost_center, tbl2.income_account as course_income_account
			   FROM 
			(SELECT SUM(tcurs.total_course_hours) AS total_courses_hours 
			FROM `tabCourse` AS tcurs
				WHERE tcurs.name IN ({courses})
				) as tbl1,
				(SELECT cmpnt.amount, cmpnt.receivable_account, cmpnt.cost_center, cmpnt.income_account
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
			course_receivable_account, course_cost_center, course_income_account = (results[0]['course_receivable_account'],
									   												results[0]['course_cost_center'],
																					results[0]['course_income_account'])
		return total_fees, hour_rate, total_hours, course_receivable_account, course_cost_center, course_income_account

	def create_fees_record(self):
		total_fees, application_fees, hour_rate, total_hours, course_receivable_account, course_cost_center, course_income_account, application_receivable_account, application_cost_center, application_income_account  = self.calculate_total_fees()
		print(total_fees, application_fees, hour_rate, total_hours, course_receivable_account, course_cost_center, course_income_account, application_receivable_account, application_cost_center, application_income_account)
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
				component.receivable_account = course_receivable_account
				component.cost_center = course_cost_center
				component.income_account = course_income_account
			if application_fees > 0 and new_student_course_enrollment(self.student):
				component = fees_doc.append("components")
				component.fees_category = 'Application Fee'
				component.amount = application_fees
				component.receivable_account = application_receivable_account
				component.cost_center = application_cost_center
				component.income_account = application_income_account
			fees_doc.save(ignore_permissions=True)
			fees_doc.submit()

	def calculate_total_fees(self):
		total_fees = 0
		application_fees = 0
		total_hours =0
		hour_rate = 0
		course_receivable_account, course_cost_center, course_income_account = None, None, None
		application_receivable_account, application_cost_center, application_income_account = None, None, None
		current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
		current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
		results = frappe.db.sql("""
			SELECT tbl1.total_courses_hours * tbl2.amount as total_fees, tbl3.application_fee, tbl1.total_courses_hours,  tbl2.amount as hour_rate,
			tbl2.receivable_account as course_receivable_account, tbl2.income_account as course_income_account, tbl2.cost_center as course_cost_center,
			tbl3.receivable_account as application_receivable_account, tbl3.income_account as application_income_account, tbl3.cost_center as application_cost_center
			FROM 
			(SELECT SUM(tcurs.total_course_hours) AS total_courses_hours 
			FROM `tabCourse Enrollment Applied Course` AS tceac
				INNER JOIN `tabCourse` AS tcurs ON tcurs.name=tceac.course
				WHERE tceac.parent=%(applicant_name)s
				) as tbl1 LEFT JOIN
				(SELECT cmpnt.amount, cmpnt.receivable_account, cmpnt.income_account, cmpnt.cost_center
					FROM `tabFee Component` as cmpnt
					INNER JOIN `tabFee Structure` as tfs ON tfs.name=cmpnt.parent
				WHERE cmpnt.fees_category='Hour Rate' 
				AND (program=%(program)s or program='' or program is null) 
				AND (academic_year=%(current_academic_year)s or academic_year='' or academic_year is null) 
				AND (academic_term=%(current_academic_term)s or academic_term='' or academic_term is null) 
					ORDER BY program DESC, academic_year DESC, academic_term DESC LIMIT 1) as tbl2 ON 1=1
					LEFT JOIN
				(SELECT cmpnt.amount as application_fee, cmpnt.receivable_account, cmpnt.income_account, cmpnt.cost_center
					FROM `tabFee Component` as cmpnt
					INNER JOIN `tabFee Structure` as tfs ON tfs.name=cmpnt.parent
				WHERE cmpnt.fees_category='Application Fee' 
				AND (program=%(program)s or program='' or program is null) 
				AND (academic_year=%(current_academic_year)s or academic_year='' or academic_year is null) 
				AND (academic_term=%(current_academic_term)s or academic_term='' or academic_term is null) 
					ORDER BY program DESC, academic_year DESC, academic_term DESC LIMIT 1) as tbl3 ON 1=1
		""", {
			"applicant_name": self.name,
			"program": self.program,
			"current_academic_year": current_academic_year,
			"current_academic_term": current_academic_term
		}, as_dict=True)
		if results:
			total_fees = float(results[0]['total_fees'] or 0)
			application_fees = float(results[0]['application_fee'] or 0)
			hour_rate = float(results[0]['hour_rate'] or 0)
			total_hours = float(results[0]['total_courses_hours'] or 0)
			course_receivable_account, course_cost_center, course_income_account = (results[0]['course_receivable_account'],
									   												results[0]['course_cost_center'],
																					results[0]['course_income_account'])
			application_receivable_account, application_cost_center, application_income_account = (results[0]['application_receivable_account'],
									   												results[0]['application_cost_center'],
																					results[0]['application_income_account'])
			
		return (total_fees, application_fees, hour_rate, total_hours, 
	  course_receivable_account, course_cost_center, course_income_account,
	  application_receivable_account, application_cost_center, application_income_account
	  )
	
@frappe.whitelist()
def has_student_registred_courses(student):
	current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
	main_prgram = frappe.db.get_single_value("Education Settings", "main_program")
	enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student, "program": main_prgram}, ["program"], cache=True)
	return True if frappe.db.exists("Course Enrollment Applicant", {"program": enrolled_program, "academic_year":current_academic_year, "academic_term": current_academic_term}) else False
	

@frappe.whitelist()
def get_student_comments():
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	return frappe.db.sql("""
		SELECT student_comment, name FROM `tabCourse Enrollment Applicant`
		WHERE student=%(student)s AND student_comment IS NOT NULL AND comment_seen=0 
	""",{"student": student}, as_dict=True)

def new_student_course_enrollment(student):
    current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
    enrollments = frappe.db.get_all("Course Enrollment Applicant", filters={"student": student, "application_status": "Approved", "academic_term": current_academic_term})
    if len(enrollments) > 0:
        return False
    return True

@frappe.whitelist()
def dismiss_comment(application_id):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	frappe.db.sql("""
		UPDATE `tabCourse Enrollment Applicant` SET comment_seen=1
		WHERE name=%(application_id)s AND student=%(student)s
	""",{"student": student, "application_id": application_id}, as_dict=True)
@frappe.whitelist()
def register_student_courses(courses, groups):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	#main_prgram = frappe.db.get_single_value("Education Settings", "main_program")
	enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student,  "graduated": 0}, ["program"])
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
		if frappe.db.exists("Course Enrollment Applicant", {"application_status":  "Approved","student": student, "program": enrolled_program, "academic_year":academic_year, "academic_term": academic_term}):
			return {"error": _('You have already registered the courses for this semester')}
		enrollment = frappe.db.exists("Course Enrollment Applicant", {"application_status":  "Applied", "student": student, "program": enrolled_program, "academic_year":academic_year, "academic_term": academic_term})
		if enrollment:
			enrollment_applicant = frappe.get_doc("Course Enrollment Applicant", enrollment)
	else:
		enrollment = frappe.db.exists("Course Enrollment Applicant", {"application_status":  "Applied", "student": student, "program": enrolled_program, "academic_year":academic_year, "academic_term": academic_term})
		if enrollment:
			enrollment_applicant = frappe.get_doc("Course Enrollment Applicant", enrollment)
	#print(enrolled_program, courses, student)
	courses = json.loads(courses)
	groups = json.loads(groups)
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
			if groups.get(course):
				course_row.group = groups.get(course)
	else:
		#enrollment_applicant.application_date = frappe.utils.nowdate()
		enrollment_applicant.register_courses(courses, groups)

	enrollment_applicant.save(ignore_permissions=True, ignore_version=True)
	pay_msg = get_pay_fees_msg(student)
	return {"msg": _("Courses registered successfully.") + " " + pay_msg, "pay": 1 if pay_msg else 0}

def get_pay_fees_msg(student):
	fees_msg = ""
	res = frappe.db.sql("""
		select sum(outstanding_amount) as amount FROM `tabFees` WHERE student=%(student)s AND outstanding_amount > 0 and docstatus=1
	""", {"student": student}, as_dict=True)
	if res and res[0].get('amount') and  res[0].get('amount') > 0:
		fees_msg = _("Please pay courses fees {0}here{1}.").format("<a href='/fees'>", "</a>")
	return fees_msg

@frappe.whitelist()
def approve_selected_applicant(applicants):
	if not 'System Manager' in frappe.get_roles(frappe.session.user):
		frappe.throw("You do not have enough permissions")
	if type(applicants) == str:
		applicants = json.loads(applicants)
	for applicant in applicants:
		applicant_doc = frappe.get_doc("Course Enrollment Applicant", applicant)
		if not applicant_doc.application_status == 'Applied':
			continue
		try:
			applicant_doc.enroll_student_in_courses()
		except:
			frappe.msgprint("Unable to approve " + applicant)
	frappe.db.commit()


@frappe.whitelist()
def get_applicant_fees(enrollment):
	fees = frappe.db.get_value("Fees", {"against_doctype": "Course Enrollment Applicant", "against_doctype_name": enrollment}, ["name", "outstanding_amount"])
	if fees:
		return {
			"fees_name": fees[0],
			"outstanding": fees[1]
		}