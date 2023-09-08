import frappe

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    student = frappe.db.get_value("Student", {"user": frappe.session.user}, ['name'])
    if not student: return context
    selected_term = frappe.form_dict.academic_term or frappe.db.get_single_value("Education Settings", "current_academic_term")
    context.avilable_terms = frappe.db.get_all("Assessment Result", {"docstatus": 1, "student": student}, ['academic_term'], group_by="academic_term")
    context.term_grades = []
    for term in context.avilable_terms:
        if selected_term == term['academic_term']:
            context.term_grades = get_term_grades(selected_term, student)
            break
    if not context.term_grades:
        selected_term = None
    context.selected_term = selected_term
    return context

def get_term_grades(academic_term, student):
    grades =  frappe.db.sql("""
        SELECT assmnt.assessment_plan, crs.course_name as course, assmnt.total_score, assmnt.maximum_score,
        crit.assessment_criteria, crit.maximum_score as criteria_maximum_score, crit.score
        FROM `tabAssessment Result` as assmnt
        INNER JOIN `tabAssessment Result Detail` as crit ON crit.parent=assmnt.name
        INNER JOIN `tabCourse` as crs ON crs.name=assmnt.course
        WHERE assmnt.academic_term=%(academic_term)s AND assmnt.student=%(student)s AND assmnt.docstatus=1
    """, {"academic_term": academic_term, "student": student}, as_dict=True)

    term_grades = {}

    for grade in grades:
        if not term_grades.get(grade['assessment_plan']):
            term_grades[grade['assessment_plan']] = {}
            term_grades[grade['assessment_plan']]['courses'] = {}
            term_grades[grade['assessment_plan']]['criterias'] = frappe.db.get_all("Assessment Plan Criteria",{"parent": grade['assessment_plan']}, ['assessment_criteria'], order_by="idx")
        if not term_grades[grade['assessment_plan']]['courses'].get(grade['course']):
            term_grades[grade['assessment_plan']]['courses'][grade['course']] = []
        term_grades[grade['assessment_plan']]['courses'][grade['course']].append(grade)
    return term_grades