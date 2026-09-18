frappe.ready(function () {
	function digitsOnly(value) {
		return String(value || '').replace(/\D/g, '');
	}

	function cleanMobile(value) {
		let mobile = String(value || '').trim();
		const removed = ['"', "'", '+', ')', '(', ' ', '-', '_', '{', '}', '[', ']'];
		removed.forEach((ch) => {
			mobile = mobile.split(ch).join('');
		});
		if (mobile.startsWith('00')) {
			mobile = mobile.slice(2);
		}
		return mobile;
	}

	function validateMobilePair(numberField, codeField, label, required) {
		const number = cleanMobile(frappe.web_form.get_value(numberField));
		const code = frappe.web_form.get_value(codeField);

		if (!number) {
			if (required) {
				frappe.throw(__('Please enter {0}', [label]));
			}
			if (code) {
				frappe.throw(
					__('Please enter {0} or clear the country code', [label])
				);
			}
			return;
		}

		if (!code) {
			frappe.throw(__('Please select Country Code for {0}', [label]));
		}

		if (!/^\d+$/.test(number)) {
			frappe.throw(
				__('{0} must contain digits only, without country code', [label])
			);
		}

		if (number.length < 7 || number.length > 15) {
			frappe.throw(__('{0} length must be between 7 and 15 digits', [label]));
		}

		const codeDigits = digitsOnly(code);
		if (codeDigits && number.startsWith(codeDigits)) {
			frappe.throw(
				__(
					'{0} should not include the country code ({1}). Enter the local number only.',
					[label, code]
				)
			);
		}

		frappe.web_form.set_value(numberField, number);
	}

	// frappe.web_form.validate = () => {
	// 	validateMobilePair(
	// 		'student_mobile_number',
	// 		'mobile_country_code',
	// 		__('Mobile Number'),
	// 		true
	// 	);
	// 	validateMobilePair(
	// 		'student_secondary_mobile_number',
	// 		'secondary_mobile_country_code',
	// 		__('Secondary Mobile Number'),
	// 		false
	// 	);
	// 	return true;
	// };
});
