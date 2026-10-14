# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

from education.patches.v14_0.seed_country_codes import seed_country_codes


def execute():
	seed_country_codes()
