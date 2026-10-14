// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Enrollment Change Log", {
	refresh(frm) {
		frm.disable_save();
	},
	teams_synced(frm) {
		if (frm.is_new() || frm.__updating_teams_synced) {
			return;
		}
		frm.__updating_teams_synced = true;
		frappe.call({
			method: "education.education.doctype.course_enrollment_change_log.course_enrollment_change_log.set_teams_synced",
			args: {
				log_name: frm.doc.name,
				teams_synced: frm.doc.teams_synced ? 1 : 0,
			},
			always(r) {
				frm.__updating_teams_synced = false;
				const saved = r && !r.exc && (r.message === 0 || r.message === 1);
				if (!saved) {
					frm.reload_doc();
					return;
				}
				frm.doc.teams_synced = r.message;
				frm.doc.__unsaved = 0;
			},
		});
	},
});
