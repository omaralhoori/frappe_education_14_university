function reloadCurrentStateOptions() {
	
}

frappe.ready(function() {
	{% if new_applicant %}
	const queryString = window.location.search;
	const urlParams = new URLSearchParams(queryString);
	frappe.web_form.set_value(['program'], [urlParams.get('program')]);
	
	frappe.web_form.set_value(['first_name'], '{{user.first_name or ""}}');
	frappe.web_form.set_value(['middle_name'], '{{user.middle_name or ""}}');
	frappe.web_form.set_value(['last_name'], '{{user.last_name or ""}}');
	// frappe.web_form.set_value(['student_email_id'], '{{user.email or ""}}');
	// frappe.web_form.set_value(['student_mobile_number'], '{{user.mobile_no or ""}}');

	// if ('{{user.email}}' != 'None'){
	// 	frappe.web_form.set_df_property("student_email_id", "read_only", 1)
	// }

	// if ('{{user.mobile_no}}' != 'None'){
	// 	frappe.web_form.set_df_property("student_mobile_number", "read_only", 1)
	// }
	frappe.web_form.set_value(['academic_year'], '{{student_admission.academic_year}}')
	frappe.web_form.set_value(['academic_term'], '{{student_admission.academic_term}}');
	
	
	{% endif %}
});