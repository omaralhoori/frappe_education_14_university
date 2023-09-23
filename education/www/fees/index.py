from education.education.doctype.fees.fees import get_fee_list
from erpnext.accounts.utils import get_balance_on
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
    context.balance = get_student_balance()

    coursepack_student = frappe.db.get_value("Student", {"user": frappe.session.user}, ['is_coursepack_student'])
    if coursepack_student:
        if  not frappe.db.get_single_value("Education Settings", "enable_coursepack_fees"):
            context.fees_list = []
    else:
        if not frappe.db.get_single_value("Education Settings", "enable_program_fees"):
            context.fees_list = []
        
    return context


def get_student_balance():
    student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
    balance = - (get_balance_on(party_type="Student", party=student, in_account_currency=True) or 0)
    return balance