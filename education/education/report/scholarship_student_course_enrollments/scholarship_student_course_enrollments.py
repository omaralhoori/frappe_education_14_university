# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	return get_columns(), get_data(filters)

def get_columns():
	return [
		 {
            'fieldname': 'enrollment_id',
            'label': _('Enrollment ID'),
            'fieldtype': 'Link',
            'options': 'Course Enrollment Applicant'
        },
		 {
            'fieldname': 'student',
            'label': _('Student ID'),
            'fieldtype': 'Link',
            'options': 'Student'
        },
		 {
            'fieldname': 'student_name',
            'label': _('Student Name'),
            'fieldtype': 'Data',
	    	"width": 200
        },
		 {
            'fieldname': 'student_email_id',
            'label': _('Email'),
            'fieldtype': 'Data',
	    	"width": 200,
			
        },
		 {
            'fieldname': 'student_mobile_number',
            'label': _('Mobile No'),
            'fieldtype': 'Data',
        },
		 {
            'fieldname': 'nationality',
            'label': _('Nationality'),
            'fieldtype': 'Data',
        },
		 {
            'fieldname': 'date_of_birth',
            'label': _('Date of Birth'),
            'fieldtype': 'Data',
        },
		 {
            'fieldname': 'application_status',
            'label': _('Application Status'),
            'fieldtype': 'Data',
        },
		 {
            'fieldname': 'action',
            'label': _('Action'),
            'fieldtype': 'Data',
	    "width": 100,
        },
	]

def get_data(filters):
	return frappe.db.sql("""
		SELECT tbl1.name as enrollment_id, tbl1.student, tbl2.student_name, tbl2.student_email_id, tbl2.student_mobile_number,
					  tbl2.nationality, tbl2.date_of_birth,
		tbl1.application_status,
		IF(tbl1.initial_approval=0,CONCAT("<button class='btn btn-sm btn-primary approve-row-btn' onclick=""approveStudent('", tbl1.name,"')"">Approve</button>") , '' )
		as action
		FROM `tabCourse Enrollment Applicant` tbl1
		INNER JOIN `tabStudent` tbl2 ON tbl1.student=tbl2.name
		INNER JOIN `tabProgram Enrollment` tbl3 ON tbl3.program=tbl1.program AND tbl3.student=tbl1.student
		WHERE tbl1.academic_term=%(academic_term)s AND tbl3.has_scholarship=1
	""", {"academic_term": filters.get('academic_term')},as_dict=True)


@frappe.whitelist()
def approve_enrollment(enrollment):
	try:
		enrollment = frappe.get_doc("Course Enrollment Applicant", enrollment)
		enrollment.enroll_student_in_courses()
		return True
	except:
		return False