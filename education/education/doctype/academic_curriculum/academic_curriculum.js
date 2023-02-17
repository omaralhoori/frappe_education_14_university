// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Academic Curriculum", {
	refresh(frm) {

	},
    validate(frm){
        
    },
    validate_compulsory_courses(frm){
        $.each(doc.courses, function(idx, val){
            if (val.course) courses_list.push(val.course);
        });
    }
});


frappe.ui.form.on('Academic Curriculum Course', {
	courses_add: function(frm){
		frm.fields_dict['courses'].grid.get_field('course').get_query = function(doc){
			var courses_list = [];
			$.each(doc.courses, function(idx, val){
				if (val.course) courses_list.push(val.course);
			});
			return { filters: [['Course', 'name', 'not in', courses_list]] };
		};
	}
});
