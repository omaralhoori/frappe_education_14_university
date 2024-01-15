// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Coursepack to Institute Transition", {
	refresh(frm) {
        if (!frm.is_new()){
            if (frm.doc.status == 'Applied'){
                frm.add_custom_button(__("Approve"), function() {
                    frm.events.approve(frm)
                }, 'Actions');
            }
            
        }
	},
    setup: function(frm) {
		frm.set_query("program", function() {
			return {
				filters: [
					["Program","is_coursepack", "=", 0]
				]
			}
		});
		frm.set_query("student", function() {
			return {
				filters: [
					["Student","is_coursepack_student", "=", 1]
				]
			}
		});
	},
    student: function(frm){
        frm.doc.course_transitions = []
        frappe.call({
            "method": "get_student_coursepacks",
            doc: frm.doc,
            callback: (res) => {
                if (res.message){
                    for (var course_enrollment of res.message){
                        console.log(courseRow)
                        var courseRow = frm.add_child('course_transitions')
                        courseRow.from_course = course_enrollment.course;
                        courseRow.to_course = course_enrollment.equivalent_course
                        courseRow.course_enrollment = course_enrollment.name
                        courseRow.grade = course_enrollment.graduation_grade;
                    }
                    frm.refresh_field('course_transitions')
                }
                console.log(res)
            }
        })
    },
    approve: function(frm){
        frappe.call({
            "method": "approve_transition",
            doc: frm.doc,
            callback: (res) => {
                if (res.message){
                    frappe.msgprint("Transfer applied successfully")
                    frm.reload_doc()
                }else{
                    frappe.msgprint("Something went wrong")
                }
            }
        })
    }
});
