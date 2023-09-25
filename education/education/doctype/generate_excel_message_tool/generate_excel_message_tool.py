# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import pandas as pd
from frappe.utils import get_site_name

class GenerateExcelMessageTool(Document):
	pass


@frappe.whitelist()
def generate_messages(excel_file, used_column_names, message_field_names, message, base_message):
	file = pd.read_excel(get_site_name(frappe.local.request.host) + excel_file)
	columns = used_column_names.split("\n")
	mapped_columns = message_field_names.split("\n")
	
	all_data = []
	for index, row in file.iterrows():
		row.at['Student Name']
		student_data = {}
		for column, mapped_column in zip(columns, mapped_columns):
			student_data[mapped_column] = row.at[column]
		formated_base_msg = base_message.format(**student_data)
		formated_message = message.format(**student_data)
		student_data['message'] = formated_base_msg + formated_message
		all_data.append(student_data)
	
	return all_data