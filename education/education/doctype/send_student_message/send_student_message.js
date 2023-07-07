// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Send Student Message", {
	refresh(frm) {
        frm.disable_save();
	},
    send_message(frm){
        if (!frm.events.validate_form(frm)){
            return;
        }
        frappe.call({
            method: "education.education.doctype.send_student_message.send_student_message.send_message",
            args: {
                doctype: frm.doc.message_type,
                docname: frm.events.get_doc_name(frm),
                message: frm.doc.message
            },
            callback: res => {
                if (res.message){
                    frappe.show_alert({
                        message:__('Message sent successfully'),
                        indicator:'green'
                    }, 5);
                    frm.events.empty_form(frm);
                }else{
                    frappe.show_alert({
                        message:__('Something went wrong'),
                        indicator:'red'
                    }, 5);
                }
            }
        })
    },
    get_doc_name(frm){
        if (frm.doc.message_type == 'Group Message'){
            return frm.doc.student_group;
        }
        if (frm.doc.message_type == 'Student Message'){
            return frm.doc.student;
        }
    },
    empty_form(frm){
        frm.set_value("student", "");
        frm.set_value("student_group", "");
        frm.set_value("message", "");
    },
    validate_form(frm){
        if (frm.doc.message_type == 'Group Message' && !frm.doc.student_group ){
            frappe.msgprint(__("Please enter Student Group"));
            return false;
        }
        if (frm.doc.message_type == 'Student Message' && !frm.doc.student ){
            frappe.msgprint(__("Please enter Student"))
            return false;
        }
        if (!frm.doc.message ){
             frappe.msgprint(__("Please enter Message"))
             return false;
        }
        return true;
    }
});
