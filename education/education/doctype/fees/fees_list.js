frappe.listview_settings['Fees'] = {
	add_fields: ["grand_total", "outstanding_amount", "due_date", "receipt_uploaded"],
	get_indicator: function(doc) {
		if(flt(doc.outstanding_amount)<=0) {
			return [__("Paid"), "green", "outstanding_amount,=,0"];
		} 
		else if (doc.receipt_uploaded == 1 && flt(doc.outstanding_amount) > 0 && doc.due_date >= frappe.datetime.get_today()) {
			return [__("Receipt Uploaded"), "orange", "outstanding_amount,>,0|due_date,>,Today"];
		} 
		else if (doc.receipt_uploaded == 0 && flt(doc.outstanding_amount) > 0 && doc.due_date >= frappe.datetime.get_today()) {
			return [__("Unpaid"), "orange", "outstanding_amount,>,0|due_date,>,Today"];
		} 
		else if (flt(doc.outstanding_amount) > 0 && doc.due_date < frappe.datetime.get_today()) {
			return [__("Overdue"), "red", "outstanding_amount,>,0|due_date,<=,Today"];
		}
	}
};
