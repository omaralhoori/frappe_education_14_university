frappe.ready(function() {
	{% if is_new%}
	var enrolled_coursepacks = `{{enrolled_coursepacks}}`;
	enrolled_coursepacks = JSON.parse(enrolled_coursepacks)
	frappe.web_form.fields_dict.program.df.options = enrolled_coursepacks;
	frappe.web_form.refresh_fields([{fieldname: 'program'}])
	{% endif %}
})