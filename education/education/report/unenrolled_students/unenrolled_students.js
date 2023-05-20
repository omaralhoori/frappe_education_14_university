// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Unenrolled Students"] = {
	"filters": [
		{
			"fieldname":"academic_year",
			"label": __("Academic Year"),
			"fieldtype": "Link",
			"options": "Academic Year",
			"reqd": 1,
			"default": frappe.defaults.get_default('academic_year')
		},
		{
			"fieldname":"academic_term",
			"label": __("Academic Term"),
			"fieldtype": "Link",
			"options": "Academic Term",
			"reqd": 1,
			"get_query": () =>{
				return {
					filters: { "academic_year": frappe.query_report.get_filter_value('academic_year')}
				}
			},
			"default": frappe.defaults.get_default('academic_term')
		},
	]
};
