// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Drop Coursepack", {
	refresh(frm) {
        if (!frm.is_new() && frm.doc.status==="Applied") {
            frm.add_custom_button(__("Approve"), function() {
                frappe.confirm('Are you sure you want to proceed?',
    () => {
        frm.events.approve(frm)
        }, () => {
        // action to perform if No is selected
    })
             
            }, 'Actions');
            

			frm.add_custom_button(__("Reject"), function() {
                frappe.confirm('Are you sure you want to proceed?',
    () => {
        frm.set_value("status", "Rejected");
        frm.save_or_update();    }, () => {
        // action to perform if No is selected
    })
			
			}, 'Actions');
		}

        if (!frm.is_new()){
            
            frappe.call({
                method: "education.education.doctype.drop_coursepack.drop_coursepack.get_apporved_requests_count",
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
        frappe.call({
            method: "education.education.doctype.drop_coursepack.drop_coursepack.drop_coursepack_approve",
            args: {
                student: frm.doc.student,
                program: frm.doc.program,
                drop_request: frm.doc.name
            },
            callback: (res) => {
                if (res.message.is_success){
                    frm.reload_doc()
                }else{
                    frappe.msgprint(res.message.error)
                }
            }
        })
        
    }
});
