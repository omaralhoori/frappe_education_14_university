# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_cloumns(), get_data(filters)
	return columns, data


def get_cloumns():
	return [
		_("Student ID") + ":Link/Student:150",
		_("Student Name") + "::200",
	]

def get_data(filters):
	academic_year, academic_term = filters.get('academic_year'), filters.get('academic_term')
	return frappe.db.sql("""
		SELECT name as student_id, student_name FROM `tabStudent` WHERE name not in (select enrlmnt.student FROM `tabCourse Enrollment Applicant` as enrlmnt
		WHERE academic_term=%(academic_term)s AND academic_year=%(academic_year)s)
		AND enabled=1
	""",{"academic_year": academic_year, "academic_term": academic_term}, as_dict=True)