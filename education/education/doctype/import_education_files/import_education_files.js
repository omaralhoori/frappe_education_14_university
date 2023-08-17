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
    },
    import_certificate_file(frm){
        frappe.call({
            method: "education.education.doctype.import_education_files.import_education_files.import_certificate_file",
            args: {
                data_file: frm.doc.program_certificate_file,
            },
            callback: (res) => {
                frappe.msgprint('Done')
            }
        })
    },
    import_grades_file(frm){
        frappe.call({
            method: "education.education.doctype.import_education_files.import_education_files.import_grades_file",
            args: {
                data_file: frm.doc.grades_file,
                assessment_plan: frm.doc.assessment_plan,
            },
            callback: (res) => {
                frappe.msgprint('Done')
            }
        })
    },
});
