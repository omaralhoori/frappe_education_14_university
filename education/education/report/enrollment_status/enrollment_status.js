// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Enrollment Status"] = {
	"filters": [
		{
			"fieldname":"academic_term",
			"label": __("Academic Term"),
			"fieldtype": "Link",
			"options": "Academic Term",
			"reqd": 1,
			"default": frappe.defaults.get_default('academic_term')
		},
		{
			"fieldname":"course",
			"label": __("Course"),
			"fieldtype": "Link",
			"options": "Course",
		},
		{
			"fieldname":"student",
			"label": __("Student"),
			"fieldtype": "Link",
			"options": "Student",
		},
	]
};
