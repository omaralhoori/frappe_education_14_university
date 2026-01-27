# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days
import os


@frappe.whitelist()
def get_page_html():
	"""Get HTML content for the fees dashboard page"""
	return frappe.render_template("education/page/fees_dashboard/fees_dashboard.html", {})
    # page_path = os.path.join(
	# 	frappe.get_module_path("education"),
	# 	"education",
	# 	"page",
	# 	"fees_dashboard",
	# 	"fees_dashboard.html"
	# )
	
	# if os.path.exists(page_path):
	# 	with open(page_path, 'r', encoding='utf-8') as f:
	# 		return f.read()
	return None


@frappe.whitelist()
def get_fees_data(filters=None, page_length=20, page_start=0):
	"""Get fees data for dashboard with filters and pagination"""
	
	if isinstance(filters, str):
		import json
		filters = json.loads(filters)
	
	filters = filters or {}
	
	# Build SQL query
	conditions = ["f.docstatus = 1"]
	
	# Date range filter
	if filters.get("from_date"):
		conditions.append(f"f.posting_date >= '{filters['from_date']}'")
	if filters.get("to_date"):
		conditions.append(f"f.posting_date <= '{filters['to_date']}'")
	
	# Receipt uploaded filter
	if filters.get("receipt_uploaded") == "Yes":
		conditions.append("f.receipt_uploaded = 1")
	elif filters.get("receipt_uploaded") == "No":
		conditions.append("(f.receipt_uploaded = 0 OR f.receipt_uploaded IS NULL)")
	
	# Unpaid filter
	if filters.get("unpaid_only") == "Yes":
		conditions.append("f.outstanding_amount > 0")
	
	where_clause = " AND ".join(conditions)
	
	# Get total count
	count_query = f"""
		SELECT COUNT(*) as total
		FROM `tabFees` f
		WHERE {where_clause}
	"""
	total_count = frappe.db.sql(count_query, as_dict=True)[0].total
	
	# Get data with pagination
	query = f"""
		SELECT 
			f.name as fee_number,
			f.student,
			f.student_name,
			s.name as student_number,
			f.mode_of_payment,
			f.receipt_amount,
			f.outstanding_amount,
			f.grand_total,
			f.receipt_payment_date,
			f.receipt_payer_name,
			f.receipt_uploaded,
			f.posting_date,
			f.due_date,
			f.payment_type
		FROM `tabFees` f
		LEFT JOIN `tabStudent` s ON s.name = f.student
		WHERE {where_clause}
		ORDER BY f.posting_date DESC, f.name DESC
		LIMIT {page_length} OFFSET {page_start}
	"""
	
	data = frappe.db.sql(query, as_dict=True)
	
	# Get attachments for fees with receipts
	fee_names = [d.fee_number for d in data if d.receipt_uploaded]
	if fee_names:
		attachments = frappe.get_all(
			"File",
			fields=["name", "file_name", "file_url", "attached_to_name"],
			filters={
				"attached_to_doctype": "Fees",
				"attached_to_name": ["in", fee_names]
			}
		)
		
		# Map attachments to fees
		attachments_map = {}
		for att in attachments:
			if att.attached_to_name not in attachments_map:
				attachments_map[att.attached_to_name] = []
			attachments_map[att.attached_to_name].append({
				"name": att.name,
				"file_name": att.file_name,
				"file_url": att.file_url
			})
		
		# Add attachments to data
		for d in data:
			d.attachments = attachments_map.get(d.fee_number, [])
	return {
		"data": data,
		"total_count": total_count,
		"page_length": page_length,
		"page_start": page_start
	}


@frappe.whitelist()
def get_dashboard_summary(filters=None):
	"""Get summary statistics for dashboard cards"""
	
	if isinstance(filters, str):
		import json
		filters = json.loads(filters)
	
	filters = filters or {}
	
	conditions = ["f.docstatus = 1"]
	
	if filters.get("from_date"):
		conditions.append(f"f.posting_date >= '{filters['from_date']}'")
	if filters.get("to_date"):
		conditions.append(f"f.posting_date <= '{filters['to_date']}'")
	
	if filters.get("receipt_uploaded") == "Yes":
		conditions.append("f.receipt_uploaded = 1")
	elif filters.get("receipt_uploaded") == "No":
		conditions.append("(f.receipt_uploaded = 0 OR f.receipt_uploaded IS NULL)")
	
	if filters.get("unpaid_only") == "Yes":
		conditions.append("f.outstanding_amount > 0")
	
	where_clause = " AND ".join(conditions)
	
	summary_query = f"""
		SELECT 
			COUNT(*) as total_fees,
			SUM(f.grand_total) as total_amount,
			SUM(f.outstanding_amount) as total_outstanding,
			SUM(CASE WHEN f.receipt_uploaded = 1 THEN 1 ELSE 0 END) as fees_with_receipts,
			SUM(CASE WHEN f.outstanding_amount > 0 THEN 1 ELSE 0 END) as unpaid_fees,
			SUM(f.receipt_amount) as total_receipt_amount
		FROM `tabFees` f
		WHERE {where_clause}
	"""
	
	result = frappe.db.sql(summary_query, as_dict=True)[0]
	
	return {
		"total_fees": result.total_fees or 0,
		"total_amount": flt(result.total_amount) or 0,
		"total_outstanding": flt(result.total_outstanding) or 0,
		"fees_with_receipts": result.fees_with_receipts or 0,
		"unpaid_fees": result.unpaid_fees or 0,
		"total_receipt_amount": flt(result.total_receipt_amount) or 0,
		"paid_amount": flt(result.total_amount) - flt(result.total_outstanding) or 0
	}


@frappe.whitelist()
def accept_receipt_and_pay(fee_name, payment_amount):
	"""Accept receipt and register payment"""
	try:
		fee_doc = frappe.get_doc("Fees", fee_name)
		
		if not fee_doc.receipt_uploaded:
			return {"error": _("No receipt uploaded for this fee")}
		
		payment_amount = flt(payment_amount)
		if payment_amount <= 0:
			return {"error": _("Payment amount must be greater than zero")}
		
		# Register payment
		fee_doc.pay_fee(payment_amount)
		
		return {
			"success": True,
			"message": _("Payment registered successfully")
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Accept Receipt Error")
		return {"error": str(e)}


@frappe.whitelist()
def reject_receipt(fee_name):
	"""Reject receipt"""
	try:
		fee_doc = frappe.get_doc("Fees", fee_name)
		fee_doc.reject_receipt()
		frappe.db.commit()
		
		return {
			"success": True,
			"message": _("Receipt rejected successfully")
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Reject Receipt Error")
		return {"error": str(e)}


@frappe.whitelist()
def get_fee_details(fee_name):
	"""Get detailed fee information"""
	try:
		fee_doc = frappe.get_doc("Fees", fee_name)
		
		# Get fee components
		components = []
		for comp in fee_doc.components:
			components.append({
				"fees_category": comp.fees_category,
				"description": comp.description,
				"fee_rate": comp.fee_rate,
				"discount": comp.discount,
				"amount": comp.amount
			})
		
		# Get attachments
		attachments = frappe.get_all(
			"File",
			fields=["name", "file_name", "file_url"],
			filters={
				"attached_to_doctype": "Fees",
				"attached_to_name": fee_name
			}
		)
		return {
			"fee_number": fee_doc.name,
			"student": fee_doc.student,
			"student_name": fee_doc.student_name,
			"posting_date": fee_doc.posting_date,
			"due_date": fee_doc.due_date,
			"grand_total": fee_doc.grand_total,
			"outstanding_amount": fee_doc.outstanding_amount,
			"paid_amount": fee_doc.grand_total - fee_doc.outstanding_amount,
			"receipt_uploaded": fee_doc.receipt_uploaded,
			"receipt_amount": fee_doc.receipt_amount,
			"receipt_payer_name": fee_doc.receipt_payer_name,
			"receipt_payment_date": fee_doc.receipt_payment_date,
			"payment_type": fee_doc.payment_type,
			"mode_of_payment": fee_doc.payment_type,
			"components": components,
			"attachments": attachments
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Fee Details Error")
		return {"error": str(e)}

