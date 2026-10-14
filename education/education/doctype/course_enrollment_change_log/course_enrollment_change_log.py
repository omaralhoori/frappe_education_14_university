# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class CourseEnrollmentChangeLog(Document):
	pass


@frappe.whitelist()
def set_teams_synced(log_name, teams_synced):
	"""Toggle Teams Synced on a change log without opening the rest of the record for edit."""
	if not log_name or not frappe.db.exists("Course Enrollment Change Log", log_name):
		frappe.throw(_("Course Enrollment Change Log {0} not found").format(log_name), frappe.DoesNotExistError)

	if not frappe.has_permission("Course Enrollment Change Log", "read", log_name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	value = 1 if cint(teams_synced) else 0
	frappe.db.set_value(
		"Course Enrollment Change Log",
		log_name,
		"teams_synced",
		value,
		update_modified=True,
	)
	return value
