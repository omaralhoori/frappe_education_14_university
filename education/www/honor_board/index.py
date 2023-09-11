import frappe

def get_context(context):
    context.academic_term = frappe.db.get_single_value("Education Settings", "honor_board_academic_term")
    context.students = frappe.db.sql("""
            SELECT tbl2.student_name, tbl1.gpa, tbl3.user_image FROM `tabAcademic Term Result` as tbl1
            INNER JOIN `tabStudent` as tbl2 ON tbl1.student=tbl2.name
            INNER JOIN `tabUser` as tbl3 ON tbl2.user=tbl3.name
            WHERE tbl1.academic_term=%(academic_term)s AND gpa >= {min_gpa}
            ORDER BY tbl1.gpa DESC
    """.format(min_gpa=frappe.db.get_single_value("Education Settings", "honor_board_min_gpa")),
      {"academic_term": frappe.db.get_single_value("Education Settings", "honor_board_academic_term")},
      as_dict=True)