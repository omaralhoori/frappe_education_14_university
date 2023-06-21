from education.education.doctype.fees.fees import get_fee_list
import frappe
from frappe import _


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = _("Fees")
    context.fees_list = get_fee_list("Fees", "", "", 0, 0) or []
    context.pay_form_url= "/api/method/education.education.doctype.fees.fees.pay_fee"
    context.upload_form_url= "/api/method/education.education.doctype.fees.fees.upload_receipt"
    context.client_key = frappe.db.get_single_value("Fees Payment Settings", "client_key")
    context.amount_limit = frappe.db.get_single_value('Fees Payment Settings', 'amount_limit')
    context.amount_msg = _('Lowest amount you can pay is :')
    return context