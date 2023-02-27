frappe.listview_settings['Course Enrollment Applicant'] = {
	add_fields: [ "application_status", 'paid'],
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		if (doc.paid && doc.application_status=='Applied') {
			return [__("Paid"), "green", "paid,=,Yes|application_status,=,Applied"];
		}
		else if (doc.application_status=="Applied") {
			return [__("Applied"), "orange", "application_status,=,Applied"];
		}
		else if (doc.application_status=="Approved") {
			return [__("Approved"), "green", "application_status,=,Approved"];
		}
		else if (doc.application_status=="Rejected") {
			return [__("Rejected"), "red", "application_status,=,Rejected"];
		}
		else if (doc.application_status=="Admitted") {
			return [__("Admitted"), "blue", "application_status,=,Admitted"];
		}
	}
};
