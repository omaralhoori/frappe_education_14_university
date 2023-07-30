# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.website.website_generator import WebsiteGenerator


class StudentAdmission(WebsiteGenerator):
	def autoname(self):
		if not self.title:
			self.title = self.get_title()
		self.name = self.title

	def validate(self):
		if not self.route:  # pylint: disable=E0203
			self.route = "admissions/" + "-".join(self.title.split(" "))

		if self.enable_admission_application and not self.program_details:
			frappe.throw(_("Please add programs to enable admission application."))

	def is_program_registered(self, program):
		student = frappe.db.get_value('Student', {"user": frappe.session.user}, "name")
		registered = frappe.db.sql("""
			select name from `tabProgram Enrollment`
			WHERE program=%(program)s AND student=%(student)s 
		""", {"program": program, "student": student})
		# if len(registered) == 0 :
		# 	registered = frappe.db.sql("""
		# 		select name from `tabStudent Applicant`
		# 		WHERE program=%(program)s AND student=%(student)s
		# 	""", {"program": program, "student": student})
		return True if registered else False

	def get_context(self, context):
		context.no_cache = 1
		context.show_sidebar = True
		context.title = self.title
		context.sidebar_items = frappe.db.get_all("Website Sidebar Item", {"parent": "Student Menu"},['title', 'name', 'route'])
		context.parents = [
			{"name": "admissions", "title": _("All Student Admissions"), "route": "admissions"}
		]

	def get_title(self):
		return _("Admissions for {0}").format(self.academic_year)


def get_list_context(context=None):
	context.update(
		{
			"show_sidebar": True,
			"sidebar_items": frappe.db.get_all("Website Sidebar Item", {"parent": "Student Menu"},['title', 'name', 'route']),
			"title": _("Student Admissions"),
			"get_list": get_admission_list,
			"row_template": "education/doctype/student_admission/templates/student_admission_row.html",
		}
	)


def get_admission_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
	return frappe.db.sql(
		"""select name, title, academic_year, modified, admission_start_date, route,
		admission_end_date from `tabStudent Admission` where published=1 and admission_end_date >= %s
		order by admission_end_date asc limit {0}, {1}
		""".format(
			limit_start, limit_page_length
		),
		[nowdate()],
		as_dict=1,
	)
