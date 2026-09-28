// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Post Approval Course Changes"] = {
	filters: [
		{
			fieldname: "academic_term",
			label: __("Academic Term"),
			fieldtype: "Link",
			options: "Academic Term",
			default: frappe.defaults.get_default("academic_term"),
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
		},
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
		},
		{
			fieldname: "course",
			label: __("Course"),
			fieldtype: "Link",
			options: "Course",
		},
		{
			fieldname: "action",
			label: __("Action"),
			fieldtype: "Select",
			options: "\nAdded\nRemoved\nGroup Changed",
		},
		{
			fieldname: "course_enrollment_applicant",
			label: __("Course Enrollment Applicant"),
			fieldtype: "Link",
			options: "Course Enrollment Applicant",
		},
		{
			fieldname: "student_changes_only",
			label: __("Student Changes Only"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
