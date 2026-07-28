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
		this.setup_program_filter();
		this.bind_events();
		this.set_default_program();
	}

	$(sel) {
		return this.page.main.find(sel);
	}

	setup_program_filter() {
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
		this.program_field.$input.on('change', () => {
			if (this._setting_default) return;
			this.$('#sd-apply').click();
		});
	}

	set_default_program() {
		frappe.db.exists('Program', DEFAULT_PROGRAM).then((exists) => {
			if (!exists) return;
			this._setting_default = true;
			this.program_field.set_value(DEFAULT_PROGRAM).then(() => {
				this._setting_default = false;
				this.load();
			});
		});
	}

	bind_events() {
		this.$('#sd-apply').on('click', () => this.load());
		this.$('#sd-clear').on('click', () => {
			if (this.program_field) {
				this.program_field.set_value('');
			}
			this.show_empty();
		});
	}

	get_program() {
		return this.program_field ? this.program_field.get_value() : '';
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

		this.$('#sd-empty-state').hide();
		this.$('#sd-content').show();

		frappe.dom.freeze(__('Loading...'));
		Promise.all([this.load_analytics(program), this.load_course_stats(program)])
			.catch((err) => {
				console.error(err);
				frappe.msgprint(__('Failed to load dashboard data.'));
			})
			.finally(() => frappe.dom.unfreeze());
	}

	load_analytics(program) {
		return frappe
			.call({
				method: this.method + '.get_student_analytics',
				args: { program },
			})
			.then((r) => {
				const data = r.message || { years: [], total_students: 0 };
				this.render_analytics(data);
			});
	}

	load_course_stats(program) {
		return frappe
			.call({
				method: this.method + '.get_course_registration_stats',
				args: { program },
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

		const years = data.years || [];
		const $tabs = this.$('#sd-year-tabs').empty();
		const $content = this.$('#sd-year-tab-content').empty();

		this.$('#sd-total-students').text(__('Total: {0}', [data.total_students || 0]));

		if (!years.length) {
			this.$('#sd-analytics-empty').show();
			this.$('.sd-tabs-wrap').hide();
			return;
		}

		this.$('#sd-analytics-empty').hide();
		this.$('.sd-tabs-wrap').show();

		years.forEach((year_data, idx) => {
			const year = year_data.educational_year || __('Unknown');
			const tab_id = 'sd-year-' + idx;
			const active = idx === 0 ? 'active' : '';

			// Use button + data attributes — avoid href="#..." which Frappe router treats as a page
			$tabs.append(
				`<li class="nav-item">
					<button type="button" class="nav-link sd-year-tab ${active}"
						data-year-idx="${idx}" data-tab-id="${tab_id}" role="tab">
						${frappe.utils.escape_html(year)}
						<small class="text-muted">(${year_data.total || 0})</small>
					</button>
				</li>`
			);

			const $pane = $(
				`<div class="tab-pane fade ${active ? 'show active' : ''}" id="${tab_id}"
					data-year-idx="${idx}" role="tabpanel">
					<div class="sd-year-total">${__('Students in this year')}: <strong>${year_data.total || 0}</strong></div>
					<div class="sd-charts-grid"></div>
				</div>`
			);
			const $grid = $pane.find('.sd-charts-grid');

			CHART_DEFS.forEach((def) => {
				const chart_id = `${tab_id}-${def.key}`;
				$grid.append(
					`<div class="sd-chart-card">
						<div class="sd-chart-title">${def.title}</div>
						<div class="sd-chart-box" id="${chart_id}"></div>
					</div>`
				);
			});

			$content.append($pane);
		});

		this._analytics_years = years;
		this.render_year_charts(years[0], 'sd-year-0');

		$tabs.find('.sd-year-tab').on('click', (e) => {
			e.preventDefault();
			e.stopPropagation();
			const $btn = $(e.currentTarget);
			const year_idx = cint($btn.data('year-idx'));
			const tab_id = $btn.data('tab-id');
			if (isNaN(year_idx) || !this._analytics_years[year_idx]) return;

			$tabs.find('.sd-year-tab').removeClass('active');
			$btn.addClass('active');
			$content.find('.tab-pane').removeClass('show active');
			$content.find('#' + tab_id).addClass('show active');

			this.render_year_charts(this._analytics_years[year_idx], tab_id);
		});
	}

	render_year_charts(year_data, tab_id) {
		if (!year_data) return;
		this.destroy_charts(this.analytics_charts);
		CHART_DEFS.forEach((def) => {
			const series = year_data[def.key] || { labels: [], values: [] };
			const selector = `#${tab_id}-${def.key}`;
			this.$(selector).empty();
			this.render_chart(selector, def, series, this.analytics_charts);
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
