// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Enrollment Applicant", {
	refresh(frm) {
        if (!frm.is_new() && frm.doc.application_status==="Applied") {
			if(frm.doc.paid || true){
                frm.add_custom_button(__("Approve"), function() {
                    //frm.set_value("application_status", "Approved");
                    frm.events.enroll(frm)
                    //frm.save_or_update();
                    frm.reload_doc();
                }, 'Actions');
            }

			frm.add_custom_button(__("Reject"), function() {
				frm.set_value("application_status", "Rejected");
				frm.save_or_update();
			}, 'Actions');
		}

	},
    enroll: function(frm) {
		frappe.call({
            method: "enroll_student_in_courses",
            doc:frm.doc,
        })
	}
});
