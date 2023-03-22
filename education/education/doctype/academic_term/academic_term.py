# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class AcademicTerm(Document):
	def autoname(self):
		self.name = (
			self.academic_year + " ({})".format(self.term_name) if self.term_name else ""
		)

	def validate(self):
		# Check if entry with same academic_year and the term_name already exists
		validate_duplication(self)
		self.title = (
			self.academic_year + " ({})".format(self.term_name) if self.term_name else ""
		)

		# Check that start of academic year is earlier than end of academic year
		if (
			self.term_start_date
			and self.term_end_date
			and getdate(self.term_start_date) > getdate(self.term_end_date)
		):
			frappe.throw(
				_(
					"The Term End Date cannot be earlier than the Term Start Date. Please correct the dates and try again."
				)
			)

		# Check that the start of the term is not before the start of the academic year
		# and end of term is not after the end of the academic year"""

		year = frappe.get_doc("Academic Year", self.academic_year)
		if (
			self.term_start_date
			and getdate(year.year_start_date)
			and (getdate(self.term_start_date) < getdate(year.year_start_date))
		):
			frappe.throw(
				_(
					"The Term Start Date cannot be earlier than the Year Start Date of the Academic Year to which the term is linked (Academic Year {}). Please correct the dates and try again."
				).format(self.academic_year)
			)

		if (
			self.term_end_date
			and getdate(year.year_end_date)
			and (getdate(self.term_end_date) > getdate(year.year_end_date))
		):
			frappe.throw(
				_(
					"The Term End Date cannot be later than the Year End Date of the Academic Year to which the term is linked (Academic Year {}). Please correct the dates and try again."
				).format(self.academic_year)
			)


def validate_duplication(self):
	term = frappe.db.sql(
		"""select name from `tabAcademic Term` where academic_year= %s and term_name= %s
    and docstatus<2 and name != %s""",
		(self.academic_year, self.term_name, self.name),
	)
	if term:
		frappe.throw(
			_(
				"An academic term with this 'Academic Year' {0} and 'Term Name' {1} already exists. Please modify these entries and try again."
			).format(self.academic_year, self.term_name)
		)


def is_course_enrollment_avilable():
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
	if not current_academic_term: return False
	enrollment_start_date = frappe.db.get_value("Academic Term", current_academic_term, "enrollment_start_date", cache=True)
	enrollment_end_date = frappe.db.get_value("Academic Term", current_academic_term, "enrollment_end_date", cache=True)
	if not enrollment_start_date or not enrollment_end_date: return False
	if enrollment_end_date >= getdate() >= enrollment_start_date:
		return True
	return False