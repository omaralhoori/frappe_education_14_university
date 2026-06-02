// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.pages['new-registered-students'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('New Registered Students'),
		single_column: true,
	});

	const METHOD = 'education.education.page.new_registered_students.new_registered_students';

	frappe.call({
		method: METHOD + '.get_page_html',
		callback: function (r) {
			if (r.message) {
				page.main.html(r.message);
				new NewRegisteredStudents(page, METHOD);
			} else {
				page.main.html(
					'<div class="alert alert-danger">' + __('Failed to load the page.') + '</div>'
				);
			}
		},
	});
};

class NewRegisteredStudents {
	constructor(page, method) {
		this.page = page;
		this.method = method;
		this.filters = {};
		this.page_length = 50;
		this.page_start = 0;
		this.total_count = 0;
		this.deleting = false;

		this.setup_program_filter();
		this.bind_events();
		this.bind_realtime();
		this.load();
	}

	// ---- helpers -------------------------------------------------------
	$(sel) {
		return this.page.main.find(sel);
	}

	setup_program_filter() {
		this.program_field = frappe.ui.form.make_control({
			parent: this.$('#nrs-program'),
			df: {
				fieldtype: 'Link',
				fieldname: 'program',
				options: 'Program',
				placeholder: __('Select Program'),
			},
			render_input: true,
		});
		this.program_field.refresh();
		// Apply filters when a program is picked
		this.program_field.$input.on('change', () => this.$('#nrs-apply').click());
	}

	collect_filters() {
		const f = {};
		const search = this.$('#nrs-search').val();
		const year = this.$('#nrs-educational-year').val();
		const program = this.program_field ? this.program_field.get_value() : '';
		const from_date = this.$('#nrs-from-date').val();
		const to_date = this.$('#nrs-to-date').val();
		if (search) f.search = search;
		if (year) f.educational_year = year;
		if (program) f.program = program;
		if (from_date) f.from_date = from_date;
		if (to_date) f.to_date = to_date;
		return f;
	}

	// ---- events --------------------------------------------------------
	bind_events() {
		this.$('#nrs-apply').on('click', () => {
			this.filters = this.collect_filters();
			this.page_start = 0;
			this.load();
		});

		this.$('#nrs-clear').on('click', () => {
			this.$('#nrs-search').val('');
			this.$('#nrs-educational-year').val('');
			if (this.program_field) this.program_field.set_value('');
			this.$('#nrs-from-date').val('');
			this.$('#nrs-to-date').val('');
			this.filters = {};
			this.page_start = 0;
			this.load();
		});

		this.$('#nrs-search, #nrs-educational-year').on('keypress', (e) => {
			if (e.which === 13) this.$('#nrs-apply').click();
		});

		// Jump to a typed page number
		this.$('#nrs-page-number').on('keypress', (e) => {
			if (e.which === 13) this.goto_page();
		});
		this.$('#nrs-page-number').on('change', () => this.goto_page());

		this.$('#nrs-prev').on('click', () => {
			if (this.page_start > 0) {
				this.page_start = Math.max(0, this.page_start - this.page_length);
				this.load();
			}
		});

		this.$('#nrs-next').on('click', () => {
			if (this.page_start + this.page_length < this.total_count) {
				this.page_start += this.page_length;
				this.load();
			}
		});

		this.$('#nrs-export').on('click', () => this.export_excel());
		this.$('#nrs-delete-all').on('click', () => this.delete_all());

		// Per-row delete (delegated)
		this.page.main.on('click', '.nrs-delete-row', (e) => {
			const student = $(e.currentTarget).data('student');
			const name = $(e.currentTarget).data('name');
			this.delete_one(student, name);
		});
	}

	bind_realtime() {
		frappe.realtime.on('new_registered_students_delete_progress', (data) => {
			this.update_progress(data);
		});
		frappe.realtime.on('new_registered_students_delete_done', (data) => {
			this.finish_deletion(data);
		});
	}

	// ---- data load -----------------------------------------------------
	load() {
		const tbody = this.$('#nrs-table-body');
		tbody.html(
			'<tr><td colspan="8" class="text-center text-muted">' +
				__('Loading...') +
				'</td></tr>'
		);

		frappe.call({
			method: this.method + '.get_students',
			args: {
				filters: this.filters,
				page_length: this.page_length,
				page_start: this.page_start,
			},
			callback: (r) => {
				if (!r.message) return;
				this.total_count = r.message.total_count;
				this.render_rows(r.message.data);
				this.render_summary();
				if (r.message.delete_running && !this.deleting) {
					this.set_deleting(true);
					this.$('#nrs-progress-wrap').show();
					this.$('#nrs-progress-label').text(__('Deletion in progress...'));
				}
			},
		});
	}

	render_rows(rows) {
		const tbody = this.$('#nrs-table-body');
		tbody.empty();

		if (!rows || !rows.length) {
			tbody.html(
				'<tr><td colspan="8" class="text-center text-muted">' +
					__('No matching students found.') +
					'</td></tr>'
			);
			return;
		}

		rows.forEach((row) => {
			const tr = $('<tr>');
			tr.append($('<td>').html(this.student_link(row.student_id)));
			tr.append($('<td>').text(row.student_name || ''));
			tr.append($('<td>').text(row.full_name || ''));
			tr.append($('<td>').text(row.email || ''));
			tr.append($('<td>').text(row.mobile_no || ''));
			tr.append($('<td>').text(row.joining_date ? frappe.datetime.str_to_user(row.joining_date) : ''));
			tr.append($('<td>').text(row.educational_year || ''));

			const btn = $(
				'<button class="btn btn-xs btn-danger nrs-delete-row">' +
					'<i class="fa fa-trash"></i> ' +
					__('Delete') +
					'</button>'
			);
			btn.attr('data-student', row.student_id);
			btn.attr('data-name', row.student_name || row.student_id);
			if (this.deleting) btn.prop('disabled', true);
			tr.append($('<td class="text-center">').append(btn));
			tbody.append(tr);
		});
	}

	student_link(id) {
		return (
			'<a href="/app/student/' +
			encodeURIComponent(id) +
			'" target="_blank">' +
			frappe.utils.escape_html(id) +
			'</a>'
		);
	}

	render_summary() {
		this.$('#nrs-total-count').text(this.total_count);
		const from = this.total_count ? this.page_start + 1 : 0;
		const to = Math.min(this.page_start + this.page_length, this.total_count);
		this.$('#nrs-page-info').text(__('{0} - {1} of {2}', [from, to, this.total_count]));

		const total_pages = Math.max(1, Math.ceil(this.total_count / this.page_length));
		const current_page = Math.floor(this.page_start / this.page_length) + 1;
		this.$('#nrs-total-pages').text(total_pages);
		this.$('#nrs-page-number').val(current_page).attr('max', total_pages);

		this.$('#nrs-prev').prop('disabled', this.page_start === 0);
		this.$('#nrs-next').prop(
			'disabled',
			this.page_start + this.page_length >= this.total_count
		);
	}

	goto_page() {
		const total_pages = Math.max(1, Math.ceil(this.total_count / this.page_length));
		let page = cint(this.$('#nrs-page-number').val());
		if (!page || page < 1) page = 1;
		if (page > total_pages) page = total_pages;

		const new_start = (page - 1) * this.page_length;
		if (new_start === this.page_start) {
			// value unchanged (or clamped back) — just re-sync the input
			this.$('#nrs-page-number').val(page);
			return;
		}
		this.page_start = new_start;
		this.load();
	}

	// ---- single row deletion ------------------------------------------
	delete_one(student, name) {
		frappe.confirm(
			__('Permanently delete student <b>{0}</b> and all related records (user, program enrollment, fees, course enrollment applicant)?', [
				frappe.utils.escape_html(name),
			]),
			() => {
				frappe.dom.freeze(__('Deleting {0}...', [name]));
				frappe.call({
					method: this.method + '.delete_student',
					args: { student: student },
					always: () => frappe.dom.unfreeze(),
					callback: (r) => {
						const res = r.message || {};
						if (res.success) {
							frappe.show_alert({
								message: __('Deleted {0}', [name]),
								indicator: 'green',
							});
							this.load();
						} else {
							frappe.msgprint({
								title: __('Deletion Failed'),
								message: frappe.utils.escape_html(res.error || __('Unknown error')),
								indicator: 'red',
							});
						}
					},
				});
			}
		);
	}

	// ---- bulk deletion -------------------------------------------------
	delete_all() {
		if (this.deleting) return;
		if (!this.total_count) {
			frappe.msgprint(__('There are no matching students to delete.'));
			return;
		}

		frappe.confirm(
			__('This will permanently delete <b>{0}</b> students and all their related records (users, program enrollments, fees, course enrollment applicants). This cannot be undone. Continue?', [
				this.total_count,
			]),
			() => {
				frappe.call({
					method: this.method + '.delete_all',
					args: { filters: this.filters },
					callback: (r) => {
						const res = r.message || {};
						if (res.enqueued) {
							this.start_deletion(res.total);
						} else {
							frappe.msgprint(res.message || __('Could not start deletion.'));
						}
					},
				});
			}
		);
	}

	start_deletion(total) {
		this.set_deleting(true);
		this.$('#nrs-failures').hide();
		this.$('#nrs-failures-body').empty();
		this.$('#nrs-progress-wrap').show();
		this.$('#nrs-progress-label').text(__('Deleting students...'));
		this.$('#nrs-progress-counts').text(__('0 of {0}', [total]));
		this.update_bar(0);
		frappe.show_alert({
			message: __('Deletion started in the background.'),
			indicator: 'blue',
		});
	}

	update_progress(data) {
		if (!this.deleting) {
			// A job was already running when the page loaded
			this.set_deleting(true);
			this.$('#nrs-progress-wrap').show();
		}
		const pct = data.total ? Math.round((data.current / data.total) * 100) : 0;
		this.update_bar(pct);
		this.$('#nrs-progress-counts').text(
			__('{0} of {1} — {2} deleted, {3} failed', [
				data.current,
				data.total,
				data.deleted,
				data.failed,
			])
		);
	}

	update_bar(pct) {
		this.$('#nrs-progress-bar').css('width', pct + '%').text(pct + '%');
	}

	finish_deletion(data) {
		this.update_bar(100);
		this.set_deleting(false);
		this.$('#nrs-progress-wrap').hide();

		const failures = (data && data.failures) || [];
		if (failures.length) {
			this.render_failures(failures);
			frappe.msgprint({
				title: __('Deletion Completed with Errors'),
				message: __('{0} deleted, {1} failed. See the failure details below.', [
					data.deleted,
					failures.length,
				]),
				indicator: 'orange',
			});
		} else {
			frappe.show_alert({
				message: __('All {0} students deleted successfully.', [data.deleted]),
				indicator: 'green',
			});
		}
		this.page_start = 0;
		this.load();
	}

	render_failures(failures) {
		const body = this.$('#nrs-failures-body');
		body.empty();
		failures.forEach((f) => {
			const tr = $('<tr>');
			tr.append($('<td>').text(f.student));
			tr.append($('<td>').text(f.student_name || ''));
			tr.append($('<td>').text(f.error || ''));
			body.append(tr);
		});
		this.$('#nrs-failures-count').text(failures.length);
		this.$('#nrs-failures').show();
	}

	// ---- UI state ------------------------------------------------------
	set_deleting(state) {
		this.deleting = state;
		this.$('#nrs-delete-all').prop('disabled', state);
		this.$('#nrs-export').prop('disabled', state);
		this.page.main.find('.nrs-delete-row').prop('disabled', state);
	}

	// ---- export --------------------------------------------------------
	export_excel() {
		const args = $.param({ filters: JSON.stringify(this.filters) });
		const url = '/api/method/' + this.method + '.export_students?' + args;
		window.open(url, '_blank');
	}
}
