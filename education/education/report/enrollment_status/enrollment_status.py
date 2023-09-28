# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters=filters)
	return columns, data


def get_columns():
	return [
		{
            'fieldname': 'enrollment_id',
            'label': _('Enrollment ID'),
            'fieldtype': 'Link',
            'options': 'Course Enrollment'
        },
		{
            'fieldname': 'student_id',
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
            'fieldname': 'email',
            'label': _('Email'),
            'fieldtype': 'Data',
	    	"width": 200,
			
        },
		 {
            'fieldname': 'academic_term',
            'label': _('Academic Term'),
            'fieldtype': 'Link',
			"options": "Academic Term"
        },
		 {
            'fieldname': 'course',
            'label': _('Course'),
            'fieldtype': 'Link',
			"options": "Course"
        },
		 {
            'fieldname': 'course_name',
            'label': _('Course Name'),
            'fieldtype': 'Data',
        },
		 {
            'fieldname': 'enrollment_status',
            'label': _('Enrollment Status'),
            'fieldtype': 'Data',
        },
		 {
            'fieldname': 'grade',
            'label': _('Grade'),
            'fieldtype': 'Float',
        },
	]


def get_data(filters):
	where_stmt = ""
	if filters.get('course'):
		where_stmt += " AND tbl1.course=%(course)s"
	if filters.get('student'):
		where_stmt += " AND tbl1.student=%(student)s"
	return frappe.db.sql("""
		SELECT tbl1.name as enrollment_id, tbl2.name as student_id, tbl2.student_name, tbl2.student_email_id as email, tbl1.enrollment_status,
		tbl1.academic_term, tbl1.course,tbl3.course_name, tbl1.graduation_grade
		FROM `tabCourse Enrollment` as tbl1
		INNER JOIN `tabStudent` as tbl2 ON tbl1.student=tbl2.name
		INNER JOIN `tabCourse` as tbl3 ON tbl1.course=tbl3.name
		WHERE tbl1.academic_term=%(academic_term)s {where_stmt}
	""".format(where_stmt=where_stmt), {**filters},as_dict=True)

