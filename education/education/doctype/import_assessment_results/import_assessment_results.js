// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Import Assessment Results", {
    setup(frm) {

        frappe.realtime.on("assessment_data_import_progress", (data) => {
			frm.import_in_progress = true;
			if (data.data_import !== frm.doc.name) {
				return;
			}
			let percent = Math.floor((data.current * 100) / data.total);
			let seconds = Math.floor(data.eta);
			let minutes = Math.floor(data.eta / 60);
			let eta_message =
				// prettier-ignore
				seconds < 60
					? __('About {0} seconds remaining', [seconds])
					: minutes === 1
						? __('About {0} minute remaining', [minutes])
						: __('About {0} minutes remaining', [minutes]);

			let message;
			if (data.success) {
				let message_args = [data.current, data.total, eta_message];
				message =
					frm.doc.import_type === "Insert New Records"
						? __("Importing {0} of {1}, {2}", message_args)
						: __("Updating {0} of {1}, {2}", message_args);
			}
			if (data.skipping) {
				message = __("Skipping {0} of {1}, {2}", [data.current, data.total, eta_message]);
			}
			frm.dashboard.show_progress(__("Import Progress"), percent, message);
			frm.page.set_indicator(__("In Progress"), "orange");
			frm.trigger("update_primary_action");

			// hide progress when complete
			if (data.current === data.total) {
				setTimeout(() => {
					frm.dashboard.hide();
					frm.refresh();
				}, 2000);
			}
		});
    },
	refresh(frm) {
        frm.trigger("toggle_buttons")
        frm.events.render_error_log_tables(frm)
        frm.events.render_warning_log_tables(frm)
	},
    toggle_buttons(frm){
        if(frm.doc.status == 'Pending' && frm.doc.assessment_results_file){
            frm.add_custom_button("Start Import", () => {
               var d = frappe.show_progress("Importing....")
               frappe.call({
                "method": "education.education.doctype.import_assessment_results.import_assessment_results.import_grades",
                "args": {
                    "data_import": frm.doc.name,
                    "data_file": frm.doc.assessment_results_file,
                    "assessment_plan": frm.doc.assessment_plan
                },
                callback: (res) =>{
                    frappe.hide_progress()
                }
                
               })
            });
            frm.add_custom_button("Start Import Background", () => {
               frappe.call({
                "method": "education.education.doctype.import_assessment_results.import_assessment_results.import_grades",
                "args": {
                    "data_import": frm.doc.name,
                    "data_file": frm.doc.assessment_results_file,
                    "assessment_plan": frm.doc.assessment_plan,
                    "backgound": true
                },
                

                
               })
            });
        }
    },
    render_warning_log_tables(frm){
        let warnings = JSON.parse(frm.doc.warning_log || "[]");
        if (warnings.length === 0) {
			frm.get_field("import_warnings").$wrapper.html("");
			return;
		}
        frm.toggle_display("warning_log_section", true)

        let html = "";
		html += Object.keys(warnings)
			.map((row_number) => {
				let message = warnings[row_number]
				return `
				<div class="warning" data-row="${row_number}">
					<h5 class="text-uppercase">${__("Row {0}", [Number(row_number) + 2])}</h5>
					<div class="body">${message}</div>
				</div>
			`;
			})
			.join("");

            frm.get_field("import_warnings").$wrapper.html(`
			<div class="row">
				<div class="col-sm-10 warnings">${html}</div>
			</div>
		`);
    },
    render_error_log_tables(frm){
        let errors = JSON.parse(frm.doc.error_log || "[]");
        if (errors.length === 0) {
			frm.get_field("import_errors").$wrapper.html("");
			return;
		}
        frm.toggle_display("import_log_section", true)

        let html = "";
		html += Object.keys(errors)
			.map((row_number) => {
				let message = errors[row_number]
				return `
				<div class="errors" data-row="${row_number}">
					<h5 class="text-uppercase">${__("Row {0}", [Number(row_number) + 2])}</h5>
					<div class="body">${message}</div>
				</div>
			`;
			})
			.join("");

            frm.get_field("import_errors").$wrapper.html(`
			<div class="row">
				<div class="col-sm-10 warnings">${html}</div>
			</div>
		`);
    }
});
