frappe.ready(function() {
	{% if is_new%}
	var terms = `{{terms}}`;
	terms = JSON.parse(terms)
	frappe.web_form.fields_dict.academic_term.df.options = terms;
	frappe.web_form.refresh_fields([{fieldname: 'academic_term'}])
	{% endif %}
})