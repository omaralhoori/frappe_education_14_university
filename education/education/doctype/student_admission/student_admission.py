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
		context.sidebar_items = frappe.db.get_all("Website Sidebar Item", {"parent": "Student Menu"},['title', 'name', 'route'], order_by="idx")
		context.parents = [
			{"name": "admissions", "title": _("All Student Admissions"), "route": "admissions"}
		]

	def get_title(self):
		return _("Admissions for {0}").format(self.academic_year)


def get_list_context(context=None):
	context.update(
		{
			"show_sidebar": True,
			"sidebar_items": frappe.db.get_all("Website Sidebar Item", {"parent": "Student Menu"},['title', 'name', 'route'], order_by="idx"),
			"title": _("Student Admissions"),
			"get_list": get_admission_list,
			"row_template": "education/doctype/student_admission/templates/student_admission_row.html",
		}
	)


def get_admission_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
	return frappe.db.sql(
		"""select name, title, academic_year, modified, admission_start_date, route, enable_admission_application,
		admission_end_date from `tabStudent Admission` where published=1 and admission_end_date >= %s
		order by admission_end_date asc limit {0}, {1}
		""".format(
			limit_start, limit_page_length
		),
		[nowdate()],
		as_dict=1,
	)


def get_program_admission_list():
	admissions = {
		"programs": [],
		"coursepacks": []
	}
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, ['name', 'is_coursepack_student'])
	if not student: return admissions
	where_stmt = ""

	registered_enrollments = frappe.db.sql("""
		SELECT enrl.program, prog.is_coursepack FROM `tabProgram Enrollment` as enrl 
		INNER JOIN `tabProgram` as prog ON prog.name = enrl.program
		WHERE enrl.student=%(student)s
	""", {"student": student[0]}, as_dict=True)
	if len(registered_enrollments) > 0:
		if not student[1]:
			return admissions
		where_stmt =f" AND prog.is_coursepack={registered_enrollments[0]['is_coursepack']}"
		programs = []
		for enrollment in registered_enrollments:
			programs.append("'" + enrollment['program'] + "'")
		programs = ",".join(programs)
		where_stmt += f" AND prog.name NOT IN ({programs})"
	program_admission_list = frappe.db.sql(
		"""SELECT 
			adm.name, adm.title, adm.academic_year, adm.modified, 
			adm.admission_start_date, adm.route, adm.enable_admission_application,
			adm.admission_end_date, admProg.program, admProg.min_age, admProg.max_age,
			admProg.application_fee, admProg.hour_rate, prog.is_coursepack
		FROM `tabStudent Admission` as adm 
		LEFT JOIN `tabStudent Admission Program` as admProg ON admProg.parent=adm.name
		INNER JOIN `tabProgram` as prog on prog.name=admProg.program
		WHERE adm.published=1 AND adm.admission_end_date >= %s {where_stmt}
		ORDER BY adm.admission_end_date asc
		""".format(where_stmt=where_stmt),
		[nowdate()],
		as_dict=1,
	)
	
	for program in program_admission_list:
		if program.get('is_coursepack'):
			program['courses'] = frappe.db.get_all("Program Course", {"parent": program.get('program')}, ['course_name'])
			admissions['coursepacks'].append(program)
		else:
			admissions["programs"].append(program)

	return admissions
