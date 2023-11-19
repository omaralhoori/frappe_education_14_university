frappe.ready(function() {
	{% if is_new%}
	var student = `{{student_data}}`;
	console.log(student)
	student = JSON.parse(student)
	// frappe.web_form.fields_dict.course.df.options = courses;
	frappe.web_form.set_value(["first_name_arabic"], [student.first_name_arabic])
	frappe.web_form.set_value(["first_name_english"], [student.first_name])
	frappe.web_form.set_value(["middle_name_arabic"], [student.middle_name_arabic])
	frappe.web_form.set_value(["middle_name_english"], [student.middle_name])
	frappe.web_form.set_value(["last_name_arabic"], [student.last_name_arabic])
	frappe.web_form.set_value(["last_name_english"], [student.last_name])
	frappe.web_form.set_value(["nationality"], [student.nationality])
	frappe.web_form.set_value(["mobile_no"], [student.student_mobile_number])
	frappe.web_form.set_value(["email"], [student.student_email_id])
	frappe.web_form.set_value(["educational_level"], [student.educational_level])
	
	// frappe.web_form.set_value(["academic_term"], ["{{academic_term}}"])
	// frappe.web_form.refresh_fields([{fieldname: 'course'}])
	{% endif %}
	console.log(__('The information must be identical to an official document such as a passport'))
	$('div[data-fieldname="__section_1"] div.section-head').text('{{msg}}')
})