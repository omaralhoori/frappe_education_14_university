// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Import Education Files", {
	refresh(frm) {
        frm.disable_save();
	},
    import_course_enrollment(frm){
        frappe.call({
            method: "education.education.doctype.import_education_files.import_education_files.import_course_enrollment",
            args: {
                data_file: frm.doc.course_enrollment_file,
                create_fees: frm.doc.create_fees,
            },
            callback: (res) => {
                frappe.msgprint('Done')
            }
        })
    }
});
