frappe.ready(function () {
	const limits = {};

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

	function lengthError(label, code, maxLength) {
		return `لقد أدخلت ${label} بشكل غير صحيح. الحد المسموح به لرمز الدولة ${code} هو ${maxLength} أرقام. يرجى تصحيح الرقم.`;
	}

	function loadLimit(codeField, callback) {
		const code = frappe.web_form.get_value(codeField);
		if (!code) {
			callback && callback();
			return;
		}
		if (Object.prototype.hasOwnProperty.call(limits, code)) {
			callback && callback();
			return;
		}
		frappe.call({
			method: 'education.education.doctype.country_code.country_code.get_country_mobile_limit',
			args: { country_code: code },
			callback: (r) => {
				limits[code] = cint((r.message && r.message.max_mobile_length) || 0);
				callback && callback();
			},
		});
	}

	function checkMobileLength(numberField, codeField, label, required) {
		const number = cleanMobile(frappe.web_form.get_value(numberField));
		const code = frappe.web_form.get_value(codeField);

		if (!number) {
			if (required) {
				return `الرجاء إدخال ${label}`;
			}
			return null;
		}

		if (code && !Object.prototype.hasOwnProperty.call(limits, code)) {
			loadLimit(codeField);
		}

		const maxLength = code ? cint(limits[code]) : 0;
		if (maxLength && number.length > maxLength) {
			return lengthError(label, code, maxLength);
		}

		const codeDigits = digitsOnly(code);
		if (codeDigits && number.startsWith(codeDigits)) {
			return `${label} يجب ألا يتضمن رمز الدولة (${code}). أدخل الرقم المحلي فقط.`;
		}

		return null;
	}

	function warnMobile(numberField, codeField, label, required) {
		const message = checkMobileLength(numberField, codeField, label, required);
		if (message) {
			frappe.msgprint({
				title: 'رقم الجوال غير صحيح',
				message: message,
				indicator: 'red',
			});
		}
	}

	function bindMobile(numberField, codeField, label) {
		const warn = () => warnMobile(numberField, codeField, label, false);
		frappe.web_form.on(codeField, () => loadLimit(codeField, warn));
		frappe.web_form.on(numberField, warn);
		loadLimit(codeField);
	}

	bindMobile('student_mobile_number', 'mobile_country_code', 'رقم الجوال');
	bindMobile(
		'student_secondary_mobile_number',
		'secondary_mobile_country_code',
		'رقم الجوال الثانوي'
	);

	frappe.web_form.validate = () => {
		const primary = checkMobileLength(
			'student_mobile_number',
			'mobile_country_code',
			'رقم الجوال',
			true
		);
		if (primary) {
			frappe.msgprint({
				title: 'رقم الجوال غير صحيح',
				message: primary,
				indicator: 'red',
			});
			return false;
		}

		const secondary = checkMobileLength(
			'student_secondary_mobile_number',
			'secondary_mobile_country_code',
			'رقم الجوال الثانوي',
			false
		);
		if (secondary) {
			frappe.msgprint({
				title: 'رقم الجوال غير صحيح',
				message: secondary,
				indicator: 'red',
			});
			return false;
		}

		return true;
	};
});
