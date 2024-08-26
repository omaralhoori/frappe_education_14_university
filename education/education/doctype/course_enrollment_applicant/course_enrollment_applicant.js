// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Enrollment Applicant", {
	refresh(frm) {
        if (!frm.is_new()){
            frappe.call({
                method: "education.education.doctype.course_enrollment_applicant.course_enrollment_applicant.get_applicant_fees",
                args: {
                    enrollment: frm.doc.name,
                },
                callback: (res) => {
                    if (res.message){
                        frm.events.render_fees(frm, res.message.outstanding, res.message.fees_name)
                    }else{
                        frm.events.render_fees(frm,0, "")
                    }
                }
            })
        }
        if (!frm.is_new() && frm.doc.application_status==="Applied") {
			if(frm.doc.paid || true){
                frm.add_custom_button(__("Approve"), function() {
                    //frm.set_value("application_status", "Approved");
                    frm.events.enroll(frm)
                    //frm.save_or_update();
                    frm.reload_doc();
                }, 'Actions');
            }
			if(frm.doc.paid || true){
                frm.add_custom_button(__("Final Approve"), function() {
                    //frm.set_value("application_status", "Approved");
                    frm.events.final_enroll(frm)
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
	},
    final_enroll: function(frm) {
		frappe.call({
            method: "final_enroll_student_in_courses",
            doc:frm.doc,
        })
	},
    render_fees(frm, fees, fees_name){
        let html = `
            <div class="m-3">Fees: <a href="/app/fees/${fees_name}" target="_blank">${fees_name}</a></div>
            <div class="m-3">
            <strong>${__('Outstanding')} : ${fees}</strong>
            </div>
        `;

        $(frm.fields_dict['fees'].wrapper).html(html)
    },
});
