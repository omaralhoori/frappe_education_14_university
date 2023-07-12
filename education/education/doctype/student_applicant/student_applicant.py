# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import add_years, date_diff, getdate, nowdate


class StudentApplicant(Document):
	def autoname(self):
		from frappe.model.naming import set_name_by_naming_series

		if self.student_admission:
			naming_series = None
			if self.program:
				# set the naming series from the student admission if provided.
				student_admission = get_student_admission_data(self.student_admission, self.program)
				if student_admission:
					naming_series = student_admission.get("applicant_naming_series")
				else:
					naming_series = None
			else:
				frappe.throw(_("Select the program first"))

			if naming_series:
				self.naming_series = naming_series

		set_name_by_naming_series(self)

	def validate(self):
		self.validate_duplication()
		self.validate_dates()
		self.validate_term()
		self.title = " ".join(
			filter(None, [self.first_name, self.middle_name , self.last_name])
		)

		if self.student_admission and self.program and self.date_of_birth:
			self.validation_from_student_admission()

	def validate_duplication(self):
		return
		registered = frappe.db.sql("""
			select name from `tabStudent Applicant`
			WHERE program=%(program)s AND student_email_id=%(student)s
		""", {"program": self.program, "student": self.student_email_id})
		if registered: frappe.throw("You are not allowed to apply for this program again")
	def after_insert(self):
		student = self.create_student()
		self.enroll_student(student)
		# self.create_application_fees(student.name)

	def validate_dates(self):
		if self.date_of_birth and getdate(self.date_of_birth) >= getdate():
			frappe.throw(_("Date of Birth cannot be greater than today."))

	def validate_term(self):
		if self.academic_year and self.academic_term:
			actual_academic_year = frappe.db.get_value(
				"Academic Term", self.academic_term, "academic_year"
			)
			if actual_academic_year != self.academic_year:
				frappe.throw(
					_("Academic Term {0} does not belong to Academic Year {1}").format(
						self.academic_term, self.academic_year
					)
				)

	def on_update_after_submit(self):
		student = frappe.get_list("Student", filters={"student_applicant": self.name})
		if student:
			frappe.throw(
				_(
					"Cannot change status as student {0} is linked with student application {1}"
				).format(student[0].name, self.name)
			)

	def on_submit(self):
		if self.paid and not self.student_admission:
			frappe.throw(
				_(
					"Please select Student Admission which is mandatory for the paid student applicant"
				)
			)

	def create_student(self):
		if frappe.db.exists("Student", {"student_email_id": self.student_email_id}):
			return  frappe.get_doc("Student", {"student_email_id": self.student_email_id})
		if frappe.db.exists("Student", {"student_mobile_number": self.student_mobile_number}):
			return frappe.get_doc("Student", {"student_mobile_number":self.student_mobile_number })
		student = get_mapped_doc(
		"Student Applicant",
		self.name,
		{
			"Student Applicant": {
				"doctype": "Student",
				"field_map": {"name": "student_applicant"},
			}
		},
		ignore_permissions=True,
	)
		student.user = frappe.session.user
		educational_year = frappe.db.sql("""
				SELECT name FROM `tabEducational Year` ORDER BY year_order LIMIT 1;
			""",as_dict=True)
		if educational_year: student.educational_year = educational_year[0]['name']
		student.save(ignore_permissions=True)
		user = frappe.get_doc("User", student.user)
		user.append_roles(['Student'])
		user.save(ignore_permissions=True)
		return student
	
	def create_application_fees(self, student):
		if not self.student_admission: return frappe.throw(_("Please select Student Admission which is mandatory for the paid student applicant"))
		student_admission = get_student_admission_data(self.student_admission, self.program)
		if not student_admission: frappe.throw(_("Cannot find selected Student Admission for the selected program"))
		if not student_admission.application_fee or student_admission.application_fee == 0: return
		fees_doc = frappe.get_doc({
			"doctype": "Fees",
			"student": student,
			"against_doctype": "Student Applicant",
			"against_doctype_name": self.name,
			"program": self.program,
			"due_date": student_admission.application_fee_due_date or student_admission.admission_end_date
		})
		component = fees_doc.append("components")
		component.fees_category = student_admission['fee_category']
		component.amount = student_admission.application_fee
		fees_doc.save(ignore_permissions=True)
		fees_doc.submit()

	def enroll_student(self, student):
		if frappe.db.exists("Program Enrollment", {"program": self.program, "student": student.name}): return
		years = frappe.db.get_all("Educational Year", fields = ["name"], order_by="year_order asc", page_length=1)
		if not years: return
		program_enrollment = frappe.new_doc("Program Enrollment")
		program_enrollment.student = student.name
		program_enrollment.student_category = self.student_category
		program_enrollment.student_name = student.student_name
		program_enrollment.program = self.program
		program_enrollment.academic_year = self.academic_year
		program_enrollment.academic_term = self.academic_term
		program_enrollment.educational_year= years[0]['name']
		program_enrollment.save(ignore_permissions=True)
		program_enrollment.submit()

	def validation_from_student_admission(self):

		student_admission = get_student_admission_data(self.student_admission, self.program)

		if (
			student_admission
			and student_admission.min_age
			and date_diff(
				nowdate(), add_years(getdate(self.date_of_birth), student_admission.min_age)
			)
			< 0
		):
			frappe.throw(
				_("Not eligible for the admission in this program as per Date Of Birth")
			)

		if (
			student_admission
			and student_admission.max_age
			and date_diff(
				nowdate(), add_years(getdate(self.date_of_birth), student_admission.max_age)
			)
			> 0
		):
			frappe.throw(
				_("Not eligible for the admission in this program as per Date Of Birth")
			)

	def on_payment_authorized(self, *args, **kwargs):
		self.db_set("paid", 1)


def get_student_admission_data(student_admission, program):

	student_admission = frappe.db.sql(
		"""select sa.admission_start_date, sa.admission_end_date, sa.application_fee_due_date,
		sap.program, sap.min_age, sap.max_age, sap.applicant_naming_series, sap.application_fee, sap.fee_category
		from `tabStudent Admission` sa, `tabStudent Admission Program` sap
		where sa.name = sap.parent and sa.name = %s and sap.program = %s""",
		(student_admission, program),
		as_dict=1,
	)

	if student_admission:
		return student_admission[0]
	else:
		return None


def create_student_by_user(user, additional_data={}):
	if user.email and frappe.db.exists("Student", {"student_email_id": user.email}):
		print("exists by email")
		return  frappe.get_doc("Student", {"student_email_id": user.email})
	if user.mobile_no and frappe.db.exists("Student", {"student_mobile_number": user.mobile_no}):
		print("exists by phone")
		return frappe.get_doc("Student", {"student_mobile_number":user.mobile_no })
	print("not exists")
	student = frappe.get_doc({
		"doctype": "Student",
		"first_name": user.first_name,
		"last_name": user.last_name,
		"joining_date": frappe.utils.nowdate(),
		"student_email_id": user.email,
		"student_mobile_number": user.mobile_no,
		"user": user.name,
		"nationality": additional_data.get('student_nationality'),
		"date_of_birth": additional_data.get('student_dob'),
		"native_language": additional_data.get('student_language'),
		"latest_educational_certificate": additional_data.get('educational_certificate'),
		"educational_level": additional_data.get('educational_level'),
		"country": additional_data.get('student_country'),
		"city": additional_data.get('student_city'),
		"marital_status": additional_data.get('student_status'),
		"gender": additional_data.get('student_gender'),
		"owner": user.name
	})
	educational_year = frappe.db.sql("""
			SELECT name FROM `tabEducational Year` ORDER BY year_order LIMIT 1;
		""",as_dict=True)
	if educational_year: student.educational_year = educational_year[0]['name']
	student.save(ignore_permissions=True)
	# user = frappe.get_doc("User", student.user)
	user.append_roles(['Student'])
	user.save(ignore_permissions=True)
	frappe.db.sql("""
		UPDATE `tabStudent` SET owner=%(user)s
		WHERE name=%(student)s
	""", {"user": user.name, "student": student.name})
	if additional_data:
		frappe.db.sql("""
			UPDATE `tabUser` SET first_login=1
			WHERE name=%(user)s
		""", {"user": user.name})
	# student.owner = user.name
	# student.save(ignore_permissions=True)
	add_student_to_group(student)	

	return student

def add_student_to_group(student):
	if not frappe.db.get_single_value("Education Settings", "add_new_students_to_groups"):
		return True
	batch_name = frappe.db.get_single_value("Education Settings", "batch_name")
	batch_count =  frappe.db.get_single_value("Education Settings", "batch_count")
	max_strength =  frappe.db.get_single_value("Education Settings", "max_group_strength")
	if not batch_name: batch_name = 'Batch'
	batch_name_count = batch_name + " - " + str(int(batch_count))
	academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year")
	academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
	student_group = None
	if exists := frappe.db.exists("Student Group", {"batch": batch_name_count, "academic_year": academic_year, "academic_term": academic_term}):
		student_group = frappe.get_doc("Student Group", exists)
		if len(student_group.students) < student_group.max_strength:
			student_row = student_group.append('students')
			student_row.student = student.name
			student_row.active = 1
			student_group.save(ignore_permissions=True)
			return True
	
	batch_count += 1
	batch_name_count = batch_name + " - " + str(int(batch_count))
	while frappe.db.exists("Student Batch Name", batch_name_count):
		batch_count += 1
		batch_name_count = batch_name + " - " + str(int(batch_count))
	else:
		frappe.get_doc({
			"doctype": "Student Batch Name",
			"batch_name": batch_name_count
		}).save(ignore_permissions=True)
	program = frappe.db.get_all("Program")
	group_name = batch_name_count
	if academic_term:
		group_name += " - " + academic_term
	whats_app_links = frappe.db.sql("""
		SELECT 	name, group_link FROM `tabWhatsapp Group`
		WHERE is_used=0
	""", as_dict=True)
	student_group = frappe.get_doc({
		"doctype": "Student Group",
		"max_strength": max_strength,
		"group_based_on": "Batch",
		"batch": batch_name_count,
		"program": program[0].get('name'),
		"academic_year": academic_year,
		"academic_term": academic_term,
		"student_group_name": group_name,
	})
	student_row = student_group.append('students')
	student_row.student = student.name
	student_row.active = 1
	student_group.save(ignore_permissions=True)
	frappe.db.set_single_value("Education Settings", "batch_count", batch_count)
	if len(whats_app_links) > 0:
		student_group.whatsapp_link = whats_app_links[0].get('group_link')
		frappe.db.sql("""
			UPDATE `tabWhatsapp Group` SET is_used=1, associated_group=%(student_group)s
			WHERE name=%(name)s
		""", {"student_group": student_group.name, "name": whats_app_links[0].get('name')})
		student_group.save(ignore_permissions=True)
	frappe.db.commit()
	return True