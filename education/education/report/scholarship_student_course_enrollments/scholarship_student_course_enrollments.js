// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Scholarship Student Course Enrollments"] = {
	"filters": [
		{
			"fieldname":"academic_term",
			"label": __("Academic Term"),
			"fieldtype": "Link",
			"options": "Academic Term",
			"reqd": 1,
			"default": frappe.defaults.get_default('academic_term')
		},
	]
};


const approveStudent = (fieldName) => {
	$('.approve-row-btn').prop('disabled', true);

	frappe.call({
		"method": "education.education.report.scholarship_student_course_enrollments.scholarship_student_course_enrollments.approve_enrollment",
		"args": {
			"enrollment": fieldName
		},
		callback: (res) => {
			$('.approve-row-btn').prop('disabled', false);

			if(res.message){
				$('button[data-original-title="Refresh"]').click()
				//location.reload()
			}else{
				frappe.msgprint(__("Something went wrong"))
			}
		}
	})
}
