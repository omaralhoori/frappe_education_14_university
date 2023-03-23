// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Course Enrollment', {
	refresh: function(frm){
		if (frm.doc.enrollment_status == "Enrolled"){
			frm.add_custom_button(__("Pull Enrollment"), function() {
				frm.events.pull_enrollment(frm);
			});
		}
	},
	onload: function(frm) {
		frm.set_query('course', function() {
			return {
				query: 'education.education.doctype.program_enrollment.program_enrollment.get_program_courses',
				filters: {
					'program': frm.doc.program
				}
			};
		});
	},
	pull_enrollment: function(frm){
		frappe.confirm(__('Are you sure you want to proceed?'),
    () => {
        frappe.call({
			method: "pull_enrollment",
			doc: frm.doc,
			callback: (res)=>{
				frm.reload_doc()
			}
		})
    }, () => {
    })
		
	}
});
