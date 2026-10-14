# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class CountryCode(Document):
	pass


@frappe.whitelist()
def get_country_mobile_limit(country_code):
	"""Return the configured local-number length limit for a country code."""
	if not country_code or not frappe.db.exists("Country Code", country_code):
		return {"max_mobile_length": 0}

	return {
		"max_mobile_length": cint(
			frappe.db.get_value("Country Code", country_code, "max_mobile_length")
		)
	}
