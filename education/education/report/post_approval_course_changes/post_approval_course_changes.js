// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Post Approval Course Changes"] = {
	filters: [
		{
			fieldname: "academic_term",
			label: __("Academic Term"),
			fieldtype: "Link",
			options: "Academic Term",
			default: frappe.defaults.get_default("academic_term"),
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
		},
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
		},
		{
			fieldname: "course",
			label: __("Course"),
			fieldtype: "Link",
			options: "Course",
		},
		{
			fieldname: "action",
			label: __("Action"),
			fieldtype: "Select",
			options: "\nAdded\nRemoved\nGroup Changed",
		},
		{
			fieldname: "course_enrollment_applicant",
			label: __("Course Enrollment Applicant"),
			fieldtype: "Link",
			options: "Course Enrollment Applicant",
		},
		{
			fieldname: "student_changes_only",
			label: __("Student Changes Only"),
			fieldtype: "Check",
			default: 1,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		if ((column.fieldname === "teams_synced" || column.id === "teams_synced") && data && data.log_name) {
			const checked = cint(data.teams_synced) ? "checked" : "";
			const log_name = frappe.utils.escape_html(data.log_name);
			return `<input type="checkbox" class="teams-synced-checkbox" data-log-name="${log_name}" ${checked}>`;
		}
		return default_formatter(value, row, column, data);
	},

	after_datatable_render(datatable) {
		const $body = $(datatable.bodyScrollable);
		$body.off("change.teams_synced");
		$body.on("change.teams_synced", ".teams-synced-checkbox", function () {
			const $input = $(this);
			if ($input.data("saving")) {
				return;
			}

			const log_name = $input.attr("data-log-name");
			const teams_synced = $input.is(":checked") ? 1 : 0;
			$input.data("saving", 1);

			frappe.call({
				method: "education.education.doctype.course_enrollment_change_log.course_enrollment_change_log.set_teams_synced",
				args: {
					log_name,
					teams_synced,
				},
				always(r) {
					$input.data("saving", 0);
					const saved = r && !r.exc && (r.message === 0 || r.message === 1);
					if (!saved) {
						$input.prop("checked", !teams_synced);
						return;
					}
					(frappe.query_report.data || []).forEach((row, rowIndex) => {
						if (row.log_name !== log_name) {
							return;
						}
						row.teams_synced = r.message;
						const colIndex = datatable.datamanager.getColumnIndexById("teams_synced");
						const cell = datatable.datamanager.getCell(colIndex, rowIndex);
						if (cell) {
							cell.content = r.message;
							cell.html = null;
						}
					});
				},
			});
		});

		$body.find(".teams-synced-checkbox").each(function () {
			this.addEventListener("mousedown", (event) => {
				event.stopPropagation();
			});
		});
	},
};
