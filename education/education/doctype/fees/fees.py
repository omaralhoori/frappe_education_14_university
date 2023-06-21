# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import erpnext
import frappe
from erpnext.accounts.doctype.payment_request.payment_request import \
    make_payment_request
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from frappe import _
from frappe.model.document_attach import DocumentAttach
from frappe.utils import money_in_words
from frappe.utils.csvutils import getlink
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class Fees(AccountsController ,DocumentAttach):
	def set_indicator(self):
		"""Set indicator for portal"""
		if self.outstanding_amount > 0:
			self.indicator_color = "orange"
			self.indicator_title = _("Unpaid")
		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def validate(self):
		self.calculate_total()
		self.set_missing_accounts_and_fields()

	def set_missing_accounts_and_fields(self):
		if not self.company:
			self.company = frappe.defaults.get_defaults().company
		if not self.currency:
			self.currency = erpnext.get_company_currency(self.company)
		if not (self.receivable_account and self.income_account and self.cost_center):
			accounts_details = frappe.get_all(
				"Company",
				fields=["default_receivable_account", "default_income_account", "cost_center"],
				filters={"name": self.company},
			)[0]
		if not self.receivable_account:
			self.receivable_account = accounts_details.default_receivable_account
		if not self.income_account:
			self.income_account = accounts_details.default_income_account
		if not self.cost_center:
			self.cost_center = accounts_details.cost_center
		if not self.student_email:
			self.student_email = self.get_student_emails()
	def on_update_after_submit(self):
		self.calculate_total()
		self.delete_gl_entries()
		self.make_gl_entries()

	def get_student_emails(self):
		student_emails = frappe.db.sql_list(
			"""
			select g.email_address
			from `tabGuardian` g, `tabStudent Guardian` sg
			where g.name = sg.guardian and sg.parent = %s and sg.parenttype = 'Student'
			and ifnull(g.email_address, '')!=''
		""",
			self.student,
		)

		student_email_id = frappe.db.get_value("Student", self.student, "student_email_id")
		if student_email_id:
			student_emails.append(student_email_id)
		if student_emails:
			return ", ".join(list(set(student_emails)))
		else:
			return None
	def upload_receipt(self, file_content, filename):
		self.attach(file_content, filename)
		self.db_set("receipt_uploaded", 1)
		
	def calculate_total(self):
		"""Calculates total amount."""
		self.grand_total = 0
		for d in self.components:
			self.grand_total += d.amount
		self.outstanding_amount = self.grand_total
		self.grand_total_in_words = money_in_words(self.grand_total)

	def on_submit(self):

		self.make_gl_entries()

		if self.send_payment_request and self.student_email:
			pr = make_payment_request(
				party_type="Student",
				party=self.student,
				dt="Fees",
				dn=self.name,
				recipient_id=self.student_email,
				submit_doc=True,
				use_dummy_message=True,
			)
			frappe.msgprint(
				_("Payment request {0} created").format(getlink("Payment Request", pr.name))
			)
	@frappe.whitelist()
	def pay_fee(self, amount=None):
		payment_entry = get_payment_entry("Fees", self.name, party_amount=amount or self.outstanding_amount, party_type='Student', payment_type='Receive', ignore_account_permission=True)
		payment_entry.save(ignore_permissions=True)
		payment_entry.submit()
		if self.against_doctype and self.against_doctype_name:
			try:
				frappe.db.set_value(self.against_doctype, self.against_doctype_name, {"paid": 1})
			except:
				pass
		return True
	@frappe.whitelist()
	def reject_receipt(self):
		self.db_set("receipt_uploaded", 0)
		
	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
		# frappe.db.set(self, 'status', 'Cancelled')

	def make_gl_entries(self):
		# if not self.grand_total:
		# 	return
		from erpnext.accounts.general_ledger import make_gl_entries
		for component in self.components:
			student_gl_entries = self.get_gl_dict(
				{
					"account": component.receivable_account or self.receivable_account,
					"party_type": "Student",
					"party": self.student,
					"against": component.income_account or  self.income_account,
					"debit":  component.amount,#self.grand_total,
					"debit_in_account_currency": component.amount,#self.grand_total,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
				},
				item=self,
			)

			fee_gl_entry = self.get_gl_dict(
				{
					"account": component.income_account or self.income_account,
					"against": self.student,
					"credit": component.amount,#self.grand_total,
					"credit_in_account_currency": component.amount,#self.grand_total,
					"cost_center": component.cost_center or self.cost_center,
				},
				item=self,
			)

			make_gl_entries(
				[student_gl_entries, fee_gl_entry],
				cancel=(self.docstatus == 2),
				update_outstanding="Yes",
				merge_entries=False,
			)
	
	def delete_gl_entries(self):
		frappe.db.delete("GL Entry", {
			"voucher_type": 'Fees',
			"voucher_no": self.name
		})
		frappe.db.delete("Payment Ledger Entry", {
			"voucher_type": 'Fees',
			"voucher_no": self.name
		})

	def make_extra_amount_gl_entries(self, amount, receivable_account, cost_center, income_account):
		if amount == 0: return
		if amount < 0:
			return self.make_extra_amount_reverse_gl_entries(abs(amount), receivable_account, cost_center, income_account)
		student_gl_entries = self.get_gl_dict(
			{
				"account": receivable_account or self.receivable_account,
				"party_type": "Student",
				"party": self.student,
				"against": income_account or self.income_account,
				"debit": amount,
				"debit_in_account_currency": amount,
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
			},
			item=self,
		)

		fee_gl_entry = self.get_gl_dict(
			{
				"account": income_account or self.income_account,
				"against": self.student,
				"credit": amount,
				"credit_in_account_currency": amount,
				"cost_center": cost_center or self.cost_center,
			},
			item=self,
		)

		from erpnext.accounts.general_ledger import make_gl_entries

		make_gl_entries(
			[student_gl_entries, fee_gl_entry],
			cancel=(self.docstatus == 2),
			update_outstanding="Yes",
			merge_entries=False,
		)

	def make_extra_amount_reverse_gl_entries(self, amount, receivable_account, cost_center, income_account):
		if amount <= 0:
			return
		student_gl_entries = self.get_gl_dict(
			{
				"account": receivable_account or self.receivable_account,
				"party_type": "Student",
				"party": self.student,
				"against": income_account or self.income_account,
				"credit": amount,
				"credit_in_account_currency": amount,
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
			},
			item=self,
		)

		fee_gl_entry = self.get_gl_dict(
			{
				"account": income_account or self.income_account,
				"against": self.student,
				"debit": amount,
				"debit_in_account_currency": amount,
				"cost_center": cost_center or self.cost_center,
			},
			item=self,
		)

		from erpnext.accounts.general_ledger import make_gl_entries

		make_gl_entries(
			[student_gl_entries, fee_gl_entry],
			cancel=(self.docstatus == 2),
			update_outstanding="Yes",
			merge_entries=False,
		)

def get_fee_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
	user = frappe.session.user
	student = frappe.db.sql(
		"select name from `tabStudent` where (student_email_id= %(user)s or student_mobile_number=%(user)s)", {"user":user}
	)
	limit_stmt = ""
	if student:
		if limit_start != 0 and limit_page_length != 0:
			limit_stmt = f"limit {limit_start} , {limit_page_length} "
		return frappe.db.sql(
			"""
			select name, program, due_date, grand_total - outstanding_amount as paid_amount,
			outstanding_amount, grand_total, currency, receipt_uploaded
			from `tabFees`
			where student= %s and docstatus=1
			order by due_date asc {0}""".format(
				limit_stmt
			),
			student,
			as_dict=True,
		)


def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		"no_breadcrumbs": True,
		"title": _("Fees"),
		"get_list": get_fee_list,
		"row_template": "templates/includes/fee/fee_row.html",
	}
import requests
import json
@frappe.whitelist()
def pay_fee():
	try:
		fee_doc = frappe.get_doc("Fees", frappe.form_dict.get('doc_name'))
	except:
			return {
			"error": _('These fees are not exist.')
		}
	try:
		header = {
			"authorization": frappe.db.get_single_value("Fees Payment Settings", "server_key"),
			"content-type": "application/json"
		}
		amount = frappe.form_dict.get('amount')
		if float(amount) < frappe.db.get_single_value('Fees Payment Settings', 'amount_limit') and float(fee_doc.outstanding_amount) != float(amount):
			return {
				"error": _('Cart amount is not valid')
			}
		
		data = {
			"profile_id": frappe.db.get_single_value('Fees Payment Settings', 'profile_id'),
			"tran_type": "sale",
			"tran_class": "ecom",
			"cart_description": "fees payment",
			"cart_id": fee_doc.name,
			"cart_currency": frappe.db.get_value('Company', fee_doc.company,'default_currency', cache=True),
			"cart_amount": float(amount),
			"payment_token": frappe.form_dict.token,
			"callback": f"https://rewaq-jo.com/api/method/education.education.doctype.fees.fees.payment_callback",
				"customer_details": {
					"name": frappe.form_dict.card_holder,
					"email": "jsmith@gmail.com",
					"street1": "404, 11th st, void",
					"city": "Dubai",
					"state": "DU",
					"country": "AE",
					"ip": "91.74.146.168"
				}
		}
	except:
		return {
			"error": _('Missing information')
		}
	try:
	# fee_doc.pay_fee()
		
		res = requests.post("https://secure-jordan.paytabs.com/payment/request", headers=header, data=json.dumps(data))
		results_json = json.loads(res.content)
		with open("tresults.txt", "w") as f:
			f.write(str(results_json))
		if results_json.get('redirect_url'):
			return {
				'redirect_url': results_json.get('redirect_url')
			}
	except:
		return {
			"error": _('You are not allowed to pay this fee')
		}
	return {"msg": _("The fee is paid successfully")}

@frappe.whitelist(allow_guest=True)
def payment_callback():
	with open("docname.txt", "w") as f:
		f.write(str(frappe.request.headers) + str(frappe.form_dict))
	fee_name = frappe.form_dict.get('cart_id')
	paid_amount = frappe.form_dict.get('tran_total')
	fee_doc = frappe.get_doc('Fees', fee_name)
	fee_doc.pay_fee(float(paid_amount))
	return True

@frappe.whitelist()
def upload_receipt():
	fee_name = frappe.local.form_dict.get('doc-name')
	file = frappe.request.files['receipt-file']
	if not file or not fee_name: 
		return {
			"error": _("you didn't upload file")
		}
	file_content = frappe.request.files['receipt-file'].read()
	try:
		fee_doc = frappe.get_doc("Fees", fee_name)
		fee_doc.upload_receipt(file_content, file.filename)
	except:
		return {
			"error": _('You are not allowed to pay this fee')
		}
	return {
		"msg": _("File uploaded successfully")
	}
	


@frappe.whitelist()
def get_fees_details(doc):
	details =  frappe.db.sql("""
		SELECT fees_category, description, amount FROM `tabFee Component`
		WHERE parent=%(doc)s
	""", {"doc": doc}, as_dict=True)
	for detail in details: detail['fees_category'] = _(detail['fees_category'])
	return details


def get_fees_due_date():
	fees_due_date_from = frappe.db.get_single_value("Education Settings","fees_due_date_from")
	if fees_due_date_from == "After Specific Days":
		after_days = frappe.db.get_single_value("Education Settings","fees_due_after_days") or 0
		if after_days < 0: after_days = 0
		return frappe.utils.add_days(frappe.utils.nowdate(), after_days)
	elif fees_due_date_from == "Specific Date":
		return frappe.db.get_single_value("Education Settings","fees_due_date") or frappe.utils.nowdate()
	elif fees_due_date_from == "Enrollment End Date":
		academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
		if academic_term:
			enrollment_end_date = frappe.db.get_value("Academic Term", academic_term, "enrollment_end_date", cache=True)
			if enrollment_end_date: return enrollment_end_date
	elif fees_due_date_from == "Academic Term End Date":
		academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
		if academic_term:
			term_end_date = frappe.db.get_value("Academic Term", academic_term, "term_end_date", cache=True)
			if term_end_date: return term_end_date
	elif fees_due_date_from == "Academic Term Fees Due Date":
		academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
		if academic_term:
			fees_due_date = frappe.db.get_value("Academic Term", academic_term, "fees_due_date", cache=True)
			if fees_due_date: return fees_due_date
	return frappe.utils.nowdate()


def get_fees_accounts(fees_category, program=None):
	"""
		return ->
			amount, receivable_account, income_account, cost_center
	"""
	current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year", cache=True)
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term", cache=True)
	results = frappe.db.sql("""
			SELECT cmpnt.amount, cmpnt.receivable_account, cmpnt.cost_center, cmpnt.income_account
				FROM `tabFee Component` as cmpnt
				INNER JOIN `tabFee Structure` as tfs ON tfs.name=cmpnt.parent
			WHERE cmpnt.fees_category=%(fees_category)s 
			AND (program=%(program)s or program='' or program is null) 
			AND (academic_year=%(current_academic_year)s or academic_year='' or academic_year is null) 
			AND (academic_term=%(current_academic_term)s or academic_term='' or academic_term is null) 
				ORDER BY program DESC, academic_year DESC, academic_term DESC LIMIT 1
	""", {
		"fees_category": fees_category,
		"program": program,
		"current_academic_year": current_academic_year,
		"current_academic_term": current_academic_term
	}, as_dict=True)

	if len(results) > 0:
		return results[0]['amount'], results[0]['receivable_account'], results[0]['income_account'], results[0]['cost_center']
	