frappe.ready(function() {
	// bind events here
	// frappe.call({
	// 	"method": "education.education.web_form.drop_course_request.drop_course_request.get_student_enrolled_courses",
	// 	"callback": (res)=> {
	// 		console.log(res)
	// 	}
	// })
	
	{% if is_new%}
	var courses = `{{enrolled_courses}}`;
	courses = JSON.parse(courses)
	frappe.web_form.fields_dict.course.df.options = courses;
	frappe.web_form.set_value(["academic_term"], ["{{academic_term}}"])
	frappe.web_form.refresh_fields([{fieldname: 'course'}])
	{% endif %}
})


