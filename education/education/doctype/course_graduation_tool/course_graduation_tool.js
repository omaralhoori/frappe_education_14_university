// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Graduation Tool", {
	refresh(frm) {
        frm.disable_save();
        frm.add_custom_button("Get Students", function() {
            frm.events.get_students(frm);
        });
        
	},

    get_students(frm){
        frappe.call({
            "method": "education.education.doctype.course_graduation_tool.course_graduation_tool.get_students",
            "args": {
                "get_type": frm.doc.get_student_by,
                "student_group": frm.doc.student_group,
                "academic_term": frm.doc.academic_term,
                "enrollment_status": frm.doc.enrollment_status,
            },
            callback: (res) =>{
                frm.doc.students = [];
                for(var student of res.message){
                    var student_row = frm.add_child("students");
                    student_row.student = student['student'];   
                    student_row.course_enrollment = student['name'];   
                    student_row.course = student['course'];   
                }
                if (res.message.length > 0){
                    frm.remove_custom_button("Get Students")
                    frm.add_custom_button("Update Students", function() {
                        frm.events.graduate_students(frm);
                    });
                }
                frm.refresh_field("students");
            }
        })
    },
    graduate_students(frm){
        var students = frm.doc.students.map(e => { return {"course": e.course, "enrollment": e.course_enrollment, "student": e.student};})
        frappe.call({
            "method": "education.education.doctype.course_graduation_tool.course_graduation_tool.graduate_students",
            "args": {
                "threshold": frm.doc.graduation_threshold,
                "graduation_date": frm.doc.graduation_date, 
                "get_type": frm.doc.get_student_by,
                "student_group": frm.doc.student_group,
                "academic_term": frm.doc.academic_term,
                "students": students
            },
            callback: (res) =>{
                frm.doc.students = [];
                for(var student of res.message){
                    console.log(student)
                    var student_row = frm.add_child("students");
                    student_row.student = student['student'];
                    student_row.course_enrollment = student['enrollment'];  
                    student_row.course = student['course'];   
                    student_row.status = student['status'];
                }
                frm.remove_custom_button("Update Students")
                frm.add_custom_button("Get Students", function() {
                    frm.events.get_students(frm);
                });
                frm.refresh_field("students");
            }
        })
    }
    
});
