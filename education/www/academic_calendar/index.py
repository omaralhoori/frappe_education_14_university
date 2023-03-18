import frappe
from education.education.doctype.academic_calendar.academic_calendar import get_events

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.events = get_events()
    context.lang = frappe.lang
    return context