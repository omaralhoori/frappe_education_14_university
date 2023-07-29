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
		_("Action") +"::200"
	]

def get_data(filters):
	return frappe.db.sql("""
		SELECT name as student_id, student_name, 
		CONCAT("<button class='btn btn-sm btn-primary delete-row-btn' onclick=""deleteRow('", name,"')"">Delete</button>") as action
		  FROM `tabStudent` WHERE 
			name not in (select enrlmnt.student FROM `tabCourse Enrollment` as enrlmnt)
			AND name not in (select pstpnt.student FROM `tabStudy Postponement` as pstpnt)
	""", as_dict=True)


@frappe.whitelist()
def delete_user(student):
	student = frappe.get_doc("Student",student)
	user = student.user
	try:
		student.delete()
	except:
		return False
	if user:
		user = frappe.get_doc("User", user)
		user.delete()
	return True

@frappe.whitelist()
def delete_all():
	students = get_data({})
	for student in students:
		delete_user(student.get('student_id'))
	return True