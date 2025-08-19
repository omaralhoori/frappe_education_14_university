// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Graduation Request", {
	refresh(frm) {
        if (!frm.is_new())
        {
            frm.add_custom_button(__("Get Students"), function() {
                //frm.set_value("application_status", "Approved");
                frm.events.get_students(frm)
            });
        }
	},

    get_students: (frm) => {
        frm.doc.students = []
        frappe.call({
            "method": "education.education.doctype.program_graduation_request.program_graduation_request.get_students",
            args: {
                "program": frm.doc.program,
                "courses": frm.doc.courses
            },
            callback: res => {
                if (res.message.students){
                    res.message.students.forEach(student => {
                        frm.add_child("students", {
                            "student": student.student,
                            "cgpa": student.cgpa,
                            "student_name": student.student_name,
                            "student_name_arabic": student.student_name_arabic,
                            "graduated_course": student.graduated_courses,
                            "enrollment": student.name
                        })
                    })
                    frm.refresh_field("students")
                }
            }
        })
    }
});
