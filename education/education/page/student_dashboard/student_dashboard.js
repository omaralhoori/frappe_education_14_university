// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.pages['student-dashboard'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Student Dashboard'),
		single_column: true,
	});

	const METHOD = 'education.education.page.student_dashboard.student_dashboard';

	frappe.call({
		method: METHOD + '.get_page_html',
		callback: function (r) {
			if (r.message) {
				page.main.html(r.message);
				new StudentDashboard(page, METHOD);
			} else {
				page.main.html(
					'<div class="alert alert-danger">' + __('Failed to load the page.') + '</div>'
				);
			}
		},
	});
};

const CHART_DEFS = [
	{ key: 'nationality', title: __('Nationality'), type: 'bar' },
	{ key: 'country', title: __('Country'), type: 'bar' },
	{ key: 'gender', title: __('Gender'), type: 'donut' },
	{ key: 'major', title: __('Major'), type: 'bar' },
	{ key: 'educational_level', title: __('Educational Level'), type: 'percentage' },
	{ key: 'age_group', title: __('Age Group'), type: 'donut' },
];

const CHART_COLORS = [
	'#42a5f5',
	'#66bb6a',
	'#ffa726',
	'#ab47bc',
	'#26c6da',
	'#ef5350',
	'#7e57c2',
	'#8d6e63',
	'#29b6f6',
	'#9ccc65',
];

const DEFAULT_PROGRAM = 'دبلوم معارف الوحي';

class StudentDashboard {
	constructor(page, method) {
		this.page = page;
		this.method = method;
		this.analytics_charts = [];
		this.course_charts = [];
		this.setup_filters();
		this.bind_events();
		this.set_defaults_and_load();
	}

	$(sel) {
		return this.page.main.find(sel);
	}

	setup_filters() {
		this.program_field = frappe.ui.form.make_control({
			parent: this.$('#sd-program'),
			df: {
				fieldtype: 'Link',
				fieldname: 'program',
				options: 'Program',
				placeholder: __('Select Program'),
				default: DEFAULT_PROGRAM,
			},
			render_input: true,
		});
		this.program_field.refresh();

		this.academic_term_field = frappe.ui.form.make_control({
			parent: this.$('#sd-academic-term'),
			df: {
				fieldtype: 'Link',
				fieldname: 'academic_term',
				options: 'Academic Term',
				placeholder: __('Select Academic Term'),
			},
			render_input: true,
		});
		this.academic_term_field.refresh();

		const on_filter_change = () => {
			if (this._setting_default) return;
			this.$('#sd-apply').click();
		};
		this.program_field.$input.on('change', on_filter_change);
		this.academic_term_field.$input.on('change', on_filter_change);
	}

	set_defaults_and_load() {
		this._setting_default = true;

		const program_p = frappe.db.exists('Program', DEFAULT_PROGRAM).then((exists) => {
			if (exists) {
				return this.program_field.set_value(DEFAULT_PROGRAM);
			}
		});

		const term_p = frappe.db
			.get_single_value('Education Settings', 'current_academic_term')
			.then((term) => {
				if (term) {
					return this.academic_term_field.set_value(term);
				}
			});

		Promise.all([program_p, term_p]).then(() => {
			this._setting_default = false;
			if (this.get_program()) {
				this.load();
			}
		});
	}

	bind_events() {
		this.$('#sd-apply').on('click', () => this.load());
		this.$('#sd-clear').on('click', () => {
			this._setting_default = true;
			Promise.all([
				this.program_field.set_value(''),
				this.academic_term_field.set_value(''),
			]).then(() => {
				this._setting_default = false;
				this.show_empty();
			});
		});
	}

	get_program() {
		return this.program_field ? this.program_field.get_value() : '';
	}

	get_academic_term() {
		return this.academic_term_field ? this.academic_term_field.get_value() : '';
	}

	show_empty() {
		this.destroy_charts(this.analytics_charts);
		this.destroy_charts(this.course_charts);
		this.$('#sd-content').hide();
		this.$('#sd-empty-state').show();
	}

	load() {
		const program = this.get_program();
		if (!program) {
			frappe.show_alert({ message: __('Please select a Program'), indicator: 'orange' });
			this.show_empty();
			return;
		}

		const academic_term = this.get_academic_term();

		this.$('#sd-empty-state').hide();
		this.$('#sd-content').show();

		frappe.dom.freeze(__('Loading...'));
		Promise.all([
			this.load_analytics(program, academic_term),
			this.load_course_stats(program, academic_term),
		])
			.catch((err) => {
				console.error(err);
				frappe.msgprint(__('Failed to load dashboard data.'));
			})
			.finally(() => frappe.dom.unfreeze());
	}

	load_analytics(program, academic_term) {
		return frappe
			.call({
				method: this.method + '.get_student_analytics',
				args: { program, academic_term: academic_term || undefined },
			})
			.then((r) => {
				const data = r.message || { total_students: 0 };
				this.render_analytics(data);
			});
	}

	load_course_stats(program, academic_term) {
		return frappe
			.call({
				method: this.method + '.get_course_registration_stats',
				args: { program, academic_term: academic_term || undefined },
			})
			.then((r) => {
				this.render_course_stats(r.message || {});
			});
	}

	destroy_charts(list) {
		(list || []).forEach((c) => {
			try {
				if (c && c.destroy) c.destroy();
			} catch (e) {
				/* ignore */
			}
		});
		if (list) {
			list.length = 0;
		}
	}

	render_analytics(data) {
		this.destroy_charts(this.analytics_charts);

		const $grid = this.$('#sd-analytics-charts').empty();
		this.$('#sd-total-students').text(__('Total: {0}', [data.total_students || 0]));

		const has_data = (data.total_students || 0) > 0;
		if (!has_data) {
			this.$('#sd-analytics-empty').show();
			$grid.hide();
			return;
		}

		this.$('#sd-analytics-empty').hide();
		$grid.show();

		CHART_DEFS.forEach((def) => {
			const chart_id = 'sd-analytics-' + def.key;
			$grid.append(
				`<div class="sd-chart-card">
					<div class="sd-chart-title">${def.title}</div>
					<div class="sd-chart-box" id="${chart_id}"></div>
				</div>`
			);
			const series = data[def.key] || { labels: [], values: [] };
			this.render_chart('#' + chart_id, def, series, this.analytics_charts);
		});
	}

	render_chart(selector, def, series, chart_list) {
		const $el = this.$(selector);
		if (!$el.length) return;

		$el.empty();
		const labels = series.labels || [];
		const values = series.values || [];

		if (!labels.length || values.every((v) => !v)) {
			$el.html(`<div class="sd-no-data">${__('No data')}</div>`);
			return;
		}

		try {
			const chart = new frappe.Chart($el.get(0), {
				title: '',
				data: {
					labels: labels,
					datasets: [{ name: __('Students'), values: values }],
				},
				type: def.type,
				height: 220,
				colors: CHART_COLORS,
				barOptions: { spaceRatio: 0.4 },
				maxSlices: 8,
				tooltipOptions: {
					formatTooltipY: (d) => d,
				},
			});
			(chart_list || this.analytics_charts).push(chart);
		} catch (e) {
			console.error('Chart error', e);
			$el.html(`<div class="sd-no-data">${__('Unable to render chart')}</div>`);
		}
	}

	render_course_stats(data) {
		this.destroy_charts(this.course_charts);

		const term = data.academic_term || '';
		const year = data.academic_year || '';
		const term_label =
			[term, year].filter(Boolean).join(' · ') || __('No current academic term set');
		this.$('#sd-term-label').text(term_label);

		this.$('#sd-applicant-count').text(data.applicant_count || 0);

		const courses = data.courses || [];
		this.$('#sd-course-count').text(courses.length);

		const $chart = this.$('#sd-course-chart').empty();
		const $empty = this.$('#sd-courses-empty');

		if (!courses.length) {
			$empty.show();
			return;
		}
		$empty.hide();

		const labels = courses.map((c) => c.course_name || c.course);
		const values = courses.map((c) => c.student_count || 0);

		if (courses.length <= 12) {
			try {
				const chart = new frappe.Chart($chart.get(0), {
					data: {
						labels: labels,
						datasets: [{ name: __('Students'), values: values }],
					},
					type: 'bar',
					height: Math.max(280, courses.length * 36),
					colors: ['#42a5f5'],
					barOptions: { spaceRatio: 0.3 },
				});
				this.course_charts.push(chart);
				return;
			} catch (e) {
				console.error(e);
			}
		}

		this.render_course_bars($chart, courses);
	}

	render_course_bars($container, courses) {
		const max = Math.max(...courses.map((c) => c.student_count || 0), 1);
		const $list = $('<div class="sd-course-bars"></div>');

		courses.forEach((c) => {
			const count = c.student_count || 0;
			const pct = Math.round((count / max) * 100);
			const name = frappe.utils.escape_html(c.course_name || c.course || '');
			$list.append(
				`<div class="sd-course-bar-row" title="${name}">
					<div class="sd-course-bar-label">${name}</div>
					<div class="sd-course-bar-track">
						<div class="sd-course-bar-fill" style="width:${pct}%"></div>
					</div>
					<div class="sd-course-bar-count">${count}</div>
				</div>`
			);
		});

		$container.append($list);
	}
}
