// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Unregistered Users"] = {
	"filters": [
		{
			"label": "Include Program",
			"fieldname": "include_program",
			"fieldtype": "Check"
		}
	],
	onload: function(report) {
		report.page.add_inner_button(__("Delete All"), function() {
			frappe.call({
				"method": "education.education.report.unregistered_users.unregistered_users.delete_all",
				callback: (res) => {
					if(res.message){
						location.reload()
					}else{
						frappe.msgprint(__("Something went wrong"))
					}
				}
			})
		});
	}
};

const deleteRow = (fieldName) => {
	frappe.call({
		"method": "education.education.report.unregistered_users.unregistered_users.delete_user",
		"args": {
			"student": fieldName
		},
		callback: (res) => {
			if(res.message){
				location.reload()
			}else{
				frappe.msgprint(__("Something went wrong"))
			}
		}
	})
}
