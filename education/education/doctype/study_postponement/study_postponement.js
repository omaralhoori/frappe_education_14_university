// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Study Postponement", {
	refresh(frm) {
        if (!frm.is_new() && frm.doc.status==="Applied") {
            frm.add_custom_button(__("Approve"), function() {
                frm.events.approve(frm)
            }, 'Actions');
            

			frm.add_custom_button(__("Reject"), function() {
				frm.set_value("status", "Rejected");
				frm.save_or_update();
			}, 'Actions');
		}
        if (!frm.is_new()){
            
            frappe.call({
                method: "education.education.doctype.study_postponement.study_postponement.get_apporved_requests_count",
                args: {
                    student: frm.doc.student,
                },
                callback: (res) => {
                    if (res.message){
                        frm.events.render_requests_counter(frm, res.message)
                    }else{
                        frm.events.render_requests_counter(frm,0)
                    }
                }
            })
        }
        
	},
    render_requests_counter(frm, approve_requests){
        let html = `
            <div class="m-3">
            <strong>${__('Student Approved Requests')} : ${approve_requests}</strong>
            </div>
        `;

        $(frm.fields_dict['student_approved_requests'].wrapper).html(html)
    },
    approve(frm){
        frm.set_value("status", "Approved");
        frm.save_or_update();
    }
});
