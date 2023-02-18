function reloadCurrentStateOptions() {
	console.log('reloadCurrentStateOptions');
   // frappe.web_form.set_value(['first_name'], ['{{username}}'])
}

frappe.ready(function() {
	{% if new_applicant %}
	const queryString = window.location.search;
	const urlParams = new URLSearchParams(queryString);
	frappe.web_form.set_value(['program'], [urlParams.get('program')]);
	
	frappe.web_form.set_value(['first_name'], ['{{user.first_name}}']);
	frappe.web_form.set_value(['middle_name'], ['{{user.middle_name}}']);
	frappe.web_form.set_value(['last_name'], ['{{user.last_name}}']);
	frappe.web_form.set_value(['student_email_id'], ['{{user.email}}']);
	frappe.web_form.set_value(['student_mobile_number'], ['{{user.mobile_no}}']);

	frappe.web_form.set_value(['academic_term'], ['{{student_admission.academic_term}}']);
	frappe.web_form.set_value(['academic_year'], ['{{student_admission.academic_year}}'])
	
	console.log('{{student_admission.academic_term}}')
	{% endif %}
});