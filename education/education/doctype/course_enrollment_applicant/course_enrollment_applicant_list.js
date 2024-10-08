frappe.listview_settings['Course Enrollment Applicant'] = {
	add_fields: [ "application_status", 'paid', 'initial_approval'],
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		if (doc.application_status=="Approved") {
			return [__("Approved"), "green", "application_status,=,Approved"];
		}
		else if (doc.application_status=="Rejected") {
			return [__("Rejected"), "red", "application_status,=,Rejected"];
		}
		if (doc.paid && doc.application_status=='Applied') {
			return [__("Paid"), "green", "paid,=,Yes|application_status,=,Applied"];
		}
		else if (doc.initial_approval==1) {
			return [__("Initial Approval"), "green", "initial_approval,=,1"];
		}
		else if (doc.application_status=="Applied") {
			return [__("Applied"), "orange", "application_status,=,Applied"];
		}
		
		else if (doc.application_status=="Admitted") {
			return [__("Admitted"), "blue", "application_status,=,Admitted"];
		}
	},
	onload: function(listview){
		listview.page.add_action_item("Approve Selected",  () => {
			var selected = listview.get_checked_items().map(item => item.name)
			frappe.call({
				method: "education.education.doctype.course_enrollment_applicant.course_enrollment_applicant.approve_selected_applicant",
				args: {
					applicants: selected
				}
				,callback: () => {
					listview.refresh();
				}
			})
		})
	}
};
