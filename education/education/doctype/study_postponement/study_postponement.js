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
	},

    approve(frm){
        frm.set_value("status", "Approved");
        frm.save_or_update();
    }
});
