# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "change_on",
			"label": _("Change On"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "student",
			"label": _("Student ID"),
			"fieldtype": "Link",
			"options": "Student",
			"width": 130,
		},
		{
			"fieldname": "student_name",
			"label": _("Student Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "action",
			"label": _("Action"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "course",
			"label": _("Course"),
			"fieldtype": "Link",
			"options": "Course",
			"width": 140,
		},
		{
			"fieldname": "course_name",
			"label": _("Course Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "student_group",
			"label": _("Group"),
			"fieldtype": "Link",
			"options": "Student Group",
			"width": 140,
		},
		{
			"fieldname": "previous_group",
			"label": _("Previous Group"),
			"fieldtype": "Link",
			"options": "Student Group",
			"width": 140,
		},
		{
			"fieldname": "academic_term",
			"label": _("Academic Term"),
			"fieldtype": "Link",
			"options": "Academic Term",
			"width": 140,
		},
		{
			"fieldname": "program",
			"label": _("Program"),
			"fieldtype": "Link",
			"options": "Program",
			"width": 140,
		},
		{
			"fieldname": "course_enrollment_applicant",
			"label": _("Enrollment Applicant"),
			"fieldtype": "Link",
			"options": "Course Enrollment Applicant",
			"width": 170,
		},
		{
			"fieldname": "changed_by",
			"label": _("Changed By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{
			"fieldname": "log_name",
			"label": _("Log"),
			"fieldtype": "Link",
			"options": "Course Enrollment Change Log",
			"width": 150,
		},
	]


def get_data(filters):
	conditions = ["1=1"]
	values = {}

	if filters.get("academic_term"):
		conditions.append("log.academic_term = %(academic_term)s")
		values["academic_term"] = filters.get("academic_term")
	if filters.get("academic_year"):
		conditions.append("log.academic_year = %(academic_year)s")
		values["academic_year"] = filters.get("academic_year")
	if filters.get("student"):
		conditions.append("log.student = %(student)s")
		values["student"] = filters.get("student")
	if filters.get("program"):
		conditions.append("log.program = %(program)s")
		values["program"] = filters.get("program")
	if filters.get("course"):
		conditions.append("log.course = %(course)s")
		values["course"] = filters.get("course")
	if filters.get("action"):
		conditions.append("log.action = %(action)s")
		values["action"] = filters.get("action")
	if filters.get("course_enrollment_applicant"):
		conditions.append("log.course_enrollment_applicant = %(course_enrollment_applicant)s")
		values["course_enrollment_applicant"] = filters.get("course_enrollment_applicant")
	if cint(filters.get("student_changes_only")):
		conditions.append("log.changed_by_student = 1")

	rows = frappe.db.sql(
		"""
		SELECT
			log.name as log_name,
			log.change_on,
			log.student,
			log.student_name,
			log.action,
			log.course,
			log.course_name,
			log.student_group,
			log.previous_group,
			log.academic_term,
			log.program,
			log.course_enrollment_applicant,
			log.changed_by
		FROM `tabCourse Enrollment Change Log` log
		WHERE {conditions}
		ORDER BY log.change_on DESC, log.creation DESC
		""".format(
			conditions=" AND ".join(conditions)
		),
		values,
		as_dict=True,
	)

	for row in rows:
		if row.get("action"):
			row["action"] = _(row["action"])
	return rows
