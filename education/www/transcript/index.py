import frappe

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    student = frappe.db.get_value("Student", {"user": frappe.session.user}, ['name'])
    if not student: return context
    context.transcript_data = get_student_transcript_data(student)
    return context


def get_student_transcript_data(student):
    enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student}, ['name'])
    if not enrolled_program: return
    course_enrollments =  frappe.db.sql("""
        select crsEnrl.enrollment_status, crsEnrl.academic_term,  crsEnrl.graduation_grade , crsEnrl.course, crs.course_name
            FROM `tabCourse Enrollment` as crsEnrl
            INNER JOIN `tabCourse` as crs ON crs.name = crsEnrl.course
        WHERE crsEnrl.program_enrollment=%(enrolled_program)s AND crsEnrl.enrollment_status NOT IN ("Pulled")
        ORDER BY crsEnrl.graduation_date desc
    """, {"enrolled_program": enrolled_program},as_dict=True)
    
    terms = {}
    for enrollment in course_enrollments:
        if not terms.get(enrollment['academic_term']):
            terms[enrollment['academic_term']] = []
        if enrollment['enrollment_status'] not in ['Graduated', 'Failed']:
            enrollment['enrollment_status'] = ''
        terms[enrollment['academic_term']].append(enrollment)
    return terms