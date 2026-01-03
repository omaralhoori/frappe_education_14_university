# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
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
	filter_program = "AND name not in (select student FROM `tabProgram Enrollment`)" if filters.get('include_program') else ""
	return frappe.db.sql("""
		SELECT name as student_id, student_name, 
		CONCAT("<button class='btn btn-sm btn-primary delete-row-btn' onclick=""deleteRow('", name,"')"">Delete</button>") as action
		  FROM `tabStudent` WHERE 
			name not in (select enrlmnt.student FROM `tabCourse Enrollment` as enrlmnt)
			AND name not in (select aplcnt.student FROM `tabCourse Enrollment Applicant` as aplcnt)
			AND name not in (select pstpnt.student FROM `tabStudy Postponement` as pstpnt)
			{filter_program}
	""".format(filter_program=filter_program), as_dict=True)


@frappe.whitelist()
def delete_user(student):
	student = frappe.get_doc("Student",student)
	user = student.user
	try:
		if enrollment := frappe.db.exists("Program Enrollment", {"student": student.name}):
			enrollment_doc = frappe.get_doc("Program Enrollment", enrollment)
			enrollment_doc.cancel()
			enrollment_doc.delete()
		student.delete()
	except:
		return False
	try:
		if user:
			user = frappe.get_doc("User", user)
			user.delete()
	except:
		return False
	return True


@frappe.whitelist()
def delete_all_students(students):
	if type(students) == str:
		students = json.loads(students)
	for student in students:
		# delete fees
		fees = frappe.db.get_all("Fees", {"student": student},)
		for fee in fees:
			fee_doc = frappe.get_doc("Fees", fee.name)
			if fee_doc.docstatus == 1:
				fee_doc.cancel()
			fee_doc.delete()
		# course enrollment applicant
		enrollment_applicants = frappe.db.get_all("Course Enrollment Applicant", {"student": student})
		for enrollment in enrollment_applicants:
			enrollment_doc = frappe.get_doc("Course Enrollment Applicant", enrollment.name)
			enrollment_doc.delete()
		# delete cancel program enrollment
		programs = frappe.db.get_all("Program Enrollment", {"student": student})
		for prog in programs:
			program_doc = frappe.get_doc("Program Enrollment", prog.name)
			if program_doc.docstatus ==1:
				program_doc.cancel()
			program_doc.delete()

		# delete dropcourse
		drops = frappe.db.get_all("Drop Coursepack", {"student": student})
		for drop in drops:
			drop_doc =frappe.get_doc("Drop Coursepack", drop.name)
			drop_doc.delete()
		# delete student
		student_doc = frappe.get_doc("Student", student)
		user_doc = frappe.get_doc("User", student_doc.user)
		access_logs = frappe.db.get_all("Access Log", {"user": user_doc.name})
		for log in access_logs:
			frappe.get_doc("Access Log", log.name).delete()
			
		student_doc.delete()
		user_doc.delete()
		frappe.db.commit()
	return {"sucess": True, "students": students}
@frappe.whitelist()
def delete_all():
	frappe.enqueue(delete_all_enqueue, queue='long')
	return True

def delete_all_enqueue():
	students = get_data({})
	delete_count = 0
	for student in students:
		delete_user(student.get('student_id'))
		delete_count += 1
		if delete_count == 10:
			frappe.db.commit()
			delete_count = 0
	return True