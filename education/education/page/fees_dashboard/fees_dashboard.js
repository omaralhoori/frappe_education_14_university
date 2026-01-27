frappe.pages['fees-dashboard'].on_page_load = function(wrapper) {
	// rtl
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'الرسوم',
		single_column: true,
		icon: 'fa fa-money',
		direction: 'rtl'
	});

	// Load HTML content from Python method
	frappe.call({
		method: 'education.education.page.fees_dashboard.fees_dashboard.get_page_html',
		callback: function(r) {
			if (r.message) {
				page.main.html(r.message);
				init_dashboard(page);
			} else {
				// Fallback: show error message
				page.main.html('<div class="alert alert-danger">حدث خطأ في تحميل الصفحة</div>');
			}
		
		}
	});
}

function init_dashboard(page) {
	let me = {
		page: page,
		current_page: 0,
		page_length: 20,
		filters: {},
		summary: {}
	};

	// Initialize filters
	me.init_filters = function() {
		// Set default date range (last 30 days)
		let to_date = frappe.datetime.get_today();
		let from_date = frappe.datetime.add_days(to_date, -30);
		
		$('#filter-from-date').val(from_date);
		$('#filter-to-date').val(to_date);
		
		// Apply filters button
		$('#btn-apply-filters').on('click', function() {
			me.apply_filters();
		});
		
		// Clear filters button
		$('#btn-clear-filters').on('click', function() {
			me.clear_filters();
		});
		
		// Enter key on filters
		$('.filter-group input, .filter-group select').on('keypress', function(e) {
			if (e.which === 13) {
				me.apply_filters();
			}
		});
	};

	me.apply_filters = function() {
		me.filters = {
			from_date: $('#filter-from-date').val() || null,
			to_date: $('#filter-to-date').val() || null,
			receipt_uploaded: $('#filter-receipt-uploaded').val() || null,
			unpaid_only: $('#filter-unpaid').val() || null
		};
		
		// Remove null values
		Object.keys(me.filters).forEach(key => {
			if (me.filters[key] === null || me.filters[key] === '') {
				delete me.filters[key];
			}
		});
		
		me.current_page = 0;
		me.load_data();
		me.load_summary();
	};

	me.clear_filters = function() {
		$('#filter-from-date').val('');
		$('#filter-to-date').val('');
		$('#filter-receipt-uploaded').val('');
		$('#filter-unpaid').val('');
		me.filters = {};
		me.current_page = 0;
		me.load_data();
		me.load_summary();
	};

	me.load_summary = function() {
		frappe.call({
			method: 'education.education.page.fees_dashboard.fees_dashboard.get_dashboard_summary',
			args: {
				filters: me.filters
			},
			callback: function(r) {
				if (r.message && !r.message.error) {
					me.summary = r.message;
					me.render_summary();
				}
			}
		});
	};

	me.render_summary = function() {
		let s = me.summary;
		$('#total-fees').text(s.total_fees || 0);
		$('#total-amount').text(format_currency(s.total_amount || 0));
		$('#total-outstanding').text(format_currency(s.total_outstanding || 0));
		$('#fees-with-receipts').text(s.fees_with_receipts || 0);
		$('#unpaid-fees').text(s.unpaid_fees || 0);
	};

	me.load_data = function() {
		let tbody = $('#fees-table-body');
		tbody.html('<tr><td colspan="9" class="text-center"><div class="loading-spinner"><span>جاري التحميل...</span></div></td></tr>');
		
		frappe.call({
			method: 'education.education.page.fees_dashboard.fees_dashboard.get_fees_data',
			args: {
				filters: me.filters,
				page_length: me.page_length,
				page_start: me.current_page * me.page_length
			},
			callback: function(r) {
				if (r.message && !r.message.error) {
					me.render_table(r.message.data || []);
					me.update_pagination(r.message);
				} else {
					tbody.html('<tr><td colspan="9" class="text-center empty-state"><div class="empty-state-message">حدث خطأ في تحميل البيانات</div></td></tr>');
				}
			}
		});
	};

	me.render_table = function(data) {
		let tbody = $('#fees-table-body');
		
		if (data.length === 0) {
			tbody.html('<tr><td colspan="9" class="text-center empty-state"><div class="empty-state-message">لا توجد بيانات</div></td></tr>');
			return;
		}
		
		let html = '';
		data.forEach(function(row) {
			html += '<tr>';
			html += '<td>' + (row.fee_number || '-') + '</td>';
			html += '<td>' + (row.student_name || '-') + '</td>';
			html += '<td>' + (row.student_number || '-') + '</td>';
			html += '<td>' + (row.payment_type || row.mode_of_payment || '-') + '</td>';
			html += '<td>' + format_currency(row.grand_total || 0) + '</td>';
			html += '<td>' + format_currency(row.receipt_amount || 0) + '</td>';
			html += '<td>' + format_currency(row.outstanding_amount || 0) + '</td>';
			html += '<td>' + (row.receipt_payment_date ? frappe.datetime.str_to_user(row.receipt_payment_date) : '-') + '</td>';
			html += '<td>' + (row.receipt_payer_name || '-') + '</td>';
			html += '<td><div class="action-buttons">';
			
			// View receipt button
			if (row.receipt_uploaded && row.attachments && row.attachments.length > 0) {
				html += '<button class="action-btn btn-view" onclick="fees_dashboard.view_receipt(\'' + row.fee_number + '\')">عرض الإيصال</button>';
			}
			
			// Accept receipt button
			if (row.receipt_uploaded && row.outstanding_amount > 0) {
				html += '<button class="action-btn btn-accept" onclick="fees_dashboard.accept_receipt(\'' + row.fee_number + '\', ' + (row.receipt_amount || row.outstanding_amount) + ')">قبول وتسديد</button>';
			}
			
			// Reject receipt button
			if (row.receipt_uploaded) {
				html += '<button class="action-btn btn-reject" onclick="fees_dashboard.reject_receipt(\'' + row.fee_number + '\')">رفض الإيصال</button>';
			}
			
			// View details button
			html += '<button class="action-btn btn-details" onclick="fees_dashboard.view_details(\'' + row.fee_number + '\')">التفاصيل</button>';
			
			html += '</div></td>';
			html += '</tr>';
		});
		
		tbody.html(html);
	};

	me.update_pagination = function(result) {
		let total = result.total_count || 0;
		let start = result.page_start || 0;
		let length = result.page_length || 20;
		let current_page = Math.floor(start / length) + 1;
		let total_pages = Math.ceil(total / length);
		
		// Update info
		$('#pagination-info').text('صفحة ' + current_page + ' من ' + total_pages + ' (' + total + ' سجل)');
		$('#table-info').text('إجمالي السجلات: ' + total);
		
		// Update buttons
		$('#btn-prev').prop('disabled', me.current_page === 0);
		$('#btn-next').prop('disabled', current_page >= total_pages);
		
		// Bind pagination events
		$('#btn-prev').off('click').on('click', function() {
			if (me.current_page > 0) {
				me.current_page--;
				me.load_data();
			}
		});
		
		$('#btn-next').off('click').on('click', function() {
			if (current_page < total_pages) {
				me.current_page++;
				me.load_data();
			}
		});
	};

	// Initialize
	me.init_filters();
	me.load_data();
	me.load_summary();
	
	// Store in global scope for button callbacks
	window.fees_dashboard = {
		view_receipt: function(fee_name) {
			frappe.call({
				method: 'education.education.page.fees_dashboard.fees_dashboard.get_fee_details',
				args: {
					fee_name: fee_name
				},
				callback: function(r) {
					if (r.message && !r.message.error) {
						let details = r.message;
						let attachments = details.attachments || [];
						
						if (attachments.length === 0) {
							frappe.msgprint(__('لا يوجد إيصال مرفق'));
							return;
						}
						
						let dialog = new frappe.ui.Dialog({
							title: __('عرض الإيصال - ' + fee_name),
							fields: [
								{
									fieldtype: 'HTML',
									fieldname: 'receipt_preview',
									options: '<div class="receipt-preview" id="receipt-preview"></div>'
								}
							],
							size: 'large'
						});
						
						let preview_html = '';
						attachments.forEach(function(att) {
							if (att.file_url) {
								let file_ext = att.file_name.split('.').pop().toLowerCase();
								if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(file_ext)) {
									preview_html += '<img src="' + att.file_url + '" style="max-width: 100%; margin-bottom: 10px;"><br>';
								} else {
									preview_html += '<a href="' + att.file_url + '" target="_blank" class="btn btn-primary">تحميل ' + att.file_name + '</a><br>';
								}
							}
						});
						console.log(preview_html);
						dialog.fields_dict.receipt_preview.$wrapper.html(preview_html);
						dialog.show();
					} else {
						frappe.msgprint(__('حدث خطأ في تحميل الإيصال'));
					}
				}
			});
		},
		
		accept_receipt: function(fee_name, default_amount) {
			frappe.call({
				method: 'education.education.page.fees_dashboard.fees_dashboard.get_fee_details',
				args: {
					fee_name: fee_name
				},
				callback: function(r) {
					if (r.message && !r.message.error) {
						let details = r.message;
						
						let dialog = new frappe.ui.Dialog({
							title: __('قبول الإيصال وتسجيل الدفعة - ' + fee_name),
							fields: [
								{
									fieldtype: 'Section Break',
									label: 'معلومات الرسوم'
								},
								{
									fieldtype: 'Column Break'
								},
								{
									fieldname: 'student_name',
									fieldtype: 'Data',
									label: 'اسم الطالب',
									default: details.student_name,
									read_only: 1
								},
								{
									fieldname: 'outstanding_amount',
									fieldtype: 'Currency',
									label: 'المبلغ المستحق',
									default: details.outstanding_amount,
									read_only: 1
								},
								{
									fieldname: 'receipt_amount',
									fieldtype: 'Currency',
									label: 'مبلغ الإيصال',
									default: details.receipt_amount || default_amount,
									read_only: 1
								},
								{
									fieldtype: 'Section Break',
									label: 'تسجيل الدفعة'
								},
								{
									fieldname: 'payment_amount',
									fieldtype: 'Currency',
									label: 'مبلغ الدفعة',
									default: details.receipt_amount || default_amount,
									reqd: 1
								}
							],
							primary_action_label: __('تسجيل الدفعة'),
							primary_action: function(values) {
								let payment_amount = values.payment_amount;
								
								if (!payment_amount || payment_amount <= 0) {
									frappe.msgprint(__('يرجى إدخال مبلغ صحيح'));
									return;
								}
								
								frappe.call({
									method: 'education.education.page.fees_dashboard.fees_dashboard.accept_receipt_and_pay',
									args: {
										fee_name: fee_name,
										payment_amount: payment_amount
									},
									callback: function(r) {
										if (r.message && !r.message.error) {
											frappe.show_alert({
												message: __('تم تسجيل الدفعة بنجاح'),
												indicator: 'green'
											}, 5);
											dialog.hide();
											me.load_data();
											me.load_summary();
										} else {
											frappe.msgprint(r.message.error || __('حدث خطأ في تسجيل الدفعة'));
										}
									}
								});
							}
						});
						
						dialog.show();
					} else {
						frappe.msgprint(__('حدث خطأ في تحميل بيانات الرسوم'));
					}
				}
			});
		},
		
		reject_receipt: function(fee_name) {
			frappe.confirm(
				__('هل أنت متأكد من رفض هذا الإيصال؟'),
				function() {
					frappe.call({
						method: 'education.education.page.fees_dashboard.fees_dashboard.reject_receipt',
						args: {
							fee_name: fee_name
						},
						callback: function(r) {
							if (r.message && !r.message.error) {
								frappe.show_alert({
									message: __('تم رفض الإيصال بنجاح'),
									indicator: 'green'
								}, 5);
								me.load_data();
								me.load_summary();
							} else {
								frappe.msgprint(r.message.error || __('حدث خطأ في رفض الإيصال'));
							}
						}
					});
				}
			);
		},
		
		view_details: function(fee_name) {
			frappe.call({
				method: 'education.education.page.fees_dashboard.fees_dashboard.get_fee_details',
				args: {
					fee_name: fee_name
				},
				callback: function(r) {
					if (r.message && !r.message.error) {
						let details = r.message;
						
						let components_html = '';
						if (details.components && details.components.length > 0) {
							components_html = '<table class="components-table"><thead><tr><th>الفئة</th><th>الوصف</th><th>المبلغ</th><th>الخصم</th><th>الإجمالي</th></tr></thead><tbody>';
							details.components.forEach(function(comp) {
								components_html += '<tr>';
								components_html += '<td>' + (comp.fees_category || '-') + '</td>';
								components_html += '<td>' + (comp.description || '-') + '</td>';
								components_html += '<td>' + format_currency(comp.fee_rate || 0) + '</td>';
								components_html += '<td>' + (comp.discount || 0) + '%</td>';
								components_html += '<td>' + format_currency(comp.amount || 0) + '</td>';
								components_html += '</tr>';
							});
							components_html += '</tbody></table>';
						}
						
						let dialog = new frappe.ui.Dialog({
							title: __('تفاصيل الرسوم - ' + fee_name),
							fields: [
								{
									fieldtype: 'HTML',
									options: `
										<div class="fee-details-section">
											<div class="fee-details-grid">
												<div class="fee-detail-item">
													<div class="fee-detail-label">اسم الطالب</div>
													<div class="fee-detail-value">${details.student_name || '-'}</div>
												</div>
												<div class="fee-detail-item">
													<div class="fee-detail-label">تاريخ الإصدار</div>
													<div class="fee-detail-value">${details.posting_date ? frappe.datetime.str_to_user(details.posting_date) : '-'}</div>
												</div>
												<div class="fee-detail-item">
													<div class="fee-detail-label">تاريخ الاستحقاق</div>
													<div class="fee-detail-value">${details.due_date ? frappe.datetime.str_to_user(details.due_date) : '-'}</div>
												</div>
												<div class="fee-detail-item">
													<div class="fee-detail-label">الإجمالي</div>
													<div class="fee-detail-value">${format_currency(details.grand_total || 0)}</div>
												</div>
												<div class="fee-detail-item">
													<div class="fee-detail-label">المبلغ المدفوع</div>
													<div class="fee-detail-value">${format_currency(details.paid_amount || 0)}</div>
												</div>
												<div class="fee-detail-item">
													<div class="fee-detail-label">المبلغ المستحق</div>
													<div class="fee-detail-value">${format_currency(details.outstanding_amount || 0)}</div>
												</div>
												<div class="fee-detail-item">
													<div class="fee-detail-label">طريقة الدفع</div>
													<div class="fee-detail-value">${details.payment_type || details.mode_of_payment || '-'}</div>
												</div>
												<div class="fee-detail-item">
													<div class="fee-detail-label">حالة الإيصال</div>
													<div class="fee-detail-value">${details.receipt_uploaded ? 'تم الرفع' : 'لم يتم الرفع'}</div>
												</div>
											</div>
										</div>
										<div class="fee-details-section">
											<h5>مكونات الرسوم</h5>
											${components_html || '<p>لا توجد مكونات</p>'}
										</div>
									`
								}
							],
							size: 'large'
						});
						
						dialog.show();
					} else {
						frappe.msgprint(__('حدث خطأ في تحميل التفاصيل'));
					}
				}
			});
		}
	};
}

function format_currency(amount) {
	return frappe.format(amount);
}
