import frappe


@frappe.whitelist()
def post_ms_forms_result():
    with open("results.txt", "w") as f:
        f.write(str(frappe.form_dict))

