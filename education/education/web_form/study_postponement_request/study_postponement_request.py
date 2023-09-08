import frappe
import json

def get_context(context):
	terms = frappe.db.get_all("Academic Term", {"term_end_date": [">", frappe.utils.nowdate()]}, ['name as value', 'name as title'])
	context.terms = json.dumps(terms)
	pass
