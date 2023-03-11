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
		registered = frappe.db.sql("""
			select name from `tabStudent Applicant`
			WHERE program=%(program)s AND student_email_id=%(student)s
		""", {"program": self.program, "student": self.student_email_id})
		if registered: frappe.throw("You are not allowed to apply for this program again")
	def after_insert(self):
		student = self.create_student()
		self.create_application_fees(student.name)

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
