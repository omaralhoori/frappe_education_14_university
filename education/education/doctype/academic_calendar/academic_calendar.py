# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AcademicCalendar(Document):
	pass


@frappe.whitelist()
def get_events(start=None, end=None, user=None, for_reminder=False, filters=None) -> list[frappe._dict]:
	where_stmt = ""
	if start and end:
		where_stmt = f"where (starts_on between '{start}' and '{end}') OR (ends_on between '{start}' and '{end}')"
	events= frappe.db.sql(f"""
		SELECT name as id, event as title, starts_on as start, ends_on as end, url_link as url, all_day as allDay FROM `tabAcademic Calendar` {where_stmt};
	""", as_dict=True)
	for event in events:
		event['start'] = str(event['start'])
		event['end'] = str(event['end'])
	return events