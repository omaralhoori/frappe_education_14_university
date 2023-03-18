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
    context.client_key = "CKKMQR-V62Q6D-2VPRNV-MPHPDQ"
    return context