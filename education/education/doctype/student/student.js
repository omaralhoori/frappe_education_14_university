// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student', {
	setup: function(frm) {
		frm.add_fetch('guardian', 'guardian_name', 'guardian_name');
		frm.add_fetch('student', 'student_name', 'full_name');
		frm.add_fetch('student', 'gender', 'gender');
		frm.add_fetch('student', 'date_of_birth', 'date_of_birth');

		frm.set_query('student', 'siblings', function(doc) {
			return {
				'filters': {
					'name': ['!=', doc.name]
				}
			};
		})
	},
	student_mobile_number: function(frm) {
		validate_local_mobile(frm, 'student_mobile_number', 'mobile_country_code', __('Mobile Number'));
	},
	mobile_country_code: function(frm) {
		validate_local_mobile(frm, 'student_mobile_number', 'mobile_country_code', __('Mobile Number'));
	},
	student_secondary_mobile_number: function(frm) {
		validate_local_mobile(
			frm,
			'student_secondary_mobile_number',
			'secondary_mobile_country_code',
			__('Secondary Mobile Number')
		);
	},
	secondary_mobile_country_code: function(frm) {
		validate_local_mobile(
			frm,
			'student_secondary_mobile_number',
			'secondary_mobile_country_code',
			__('Secondary Mobile Number')
		);
	},
	refresh: function(frm) {
		frm.set_query("user", function (doc) {
			return {
				filters: {
					ignore_user_type: 1,
				},
			};
		});

		if(!frm.is_new()) {

			// custom buttons
			frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.set_route('query-report', 'General Ledger',
					{party_type:'Student', party:frm.doc.name});
			});
		}

		// frappe.db.get_value('Education Settings', {name: 'Education Settings'}, 'user_creation_skip', (r) => {
		// 	if (cint(r.user_creation_skip) !== 1) {
		// 		// frm.set_df_property('student_email_id', 'reqd', 1);
		// 	}
		// });
	}
});

function validate_local_mobile(frm, number_field, code_field, label) {
	let number = (frm.doc[number_field] || '').toString().trim();
	const code = frm.doc[code_field];
	if (!number) return;

	const removed = ['"', "'", '+', ')', '(', ' ', '-', '_', '{', '}', '[', ']'];
	removed.forEach((ch) => {
		number = number.split(ch).join('');
	});
	if (number.startsWith('00')) number = number.slice(2);

	if (code) {
		const code_digits = String(code).replace(/\D/g, '');
		if (code_digits && number.startsWith(code_digits)) {
			frappe.msgprint(
				__(
					'{0} should not include the country code ({1}). Enter the local number only.',
					[label, code]
				)
			);
		}
	}
}

frappe.ui.form.on('Student Guardian', {
	guardians_add: function(frm){
		frm.fields_dict['guardians'].grid.get_field('guardian').get_query = function(doc){
			let guardian_list = [];
			if(!doc.__islocal) guardian_list.push(doc.guardian);
			$.each(doc.guardians, function(idx, val){
				if (val.guardian) guardian_list.push(val.guardian);
			});
			return { filters: [['Guardian', 'name', 'not in', guardian_list]] };
		};
	}
});


frappe.ui.form.on('Student Sibling', {
	siblings_add: function(frm){
		frm.fields_dict['siblings'].grid.get_field('student').get_query = function(doc){
			let sibling_list = [frm.doc.name];
			$.each(doc.siblings, function(idx, val){
				if (val.student && val.studying_in_same_institute == 'YES') {
					sibling_list.push(val.student);
				}
			});
			return { filters: [['Student', 'name', 'not in', sibling_list]] };
		};
	}
});
