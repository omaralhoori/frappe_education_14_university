import frappe

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    student = frappe.db.get_value("Student", {"user": frappe.session.user}, ['name'])
    if not student: return context
    context.transcript_data, context.terms_gpa, context.cgpa = get_student_transcript_data(student)
    return context


def get_student_transcript_data(student):
    enrolled_program = frappe.db.get_value("Program Enrollment", {"student": student}, ['name'])
    if not enrolled_program: return
    course_enrollments =  frappe.db.sql("""
        select crsEnrl.enrollment_status, crsEnrl.academic_term,  crsEnrl.graduation_grade , crsEnrl.course, crs.course_name, crs.total_course_hours
            FROM `tabCourse Enrollment` as crsEnrl
            INNER JOIN `tabCourse` as crs ON crs.name = crsEnrl.course
        WHERE crsEnrl.program_enrollment=%(enrolled_program)s AND crsEnrl.enrollment_status NOT IN ("Pulled")
        ORDER BY crsEnrl.graduation_date desc
    """, {"enrolled_program": enrolled_program},as_dict=True)
    
    terms = {}
    terms_gpa = {}
    for enrollment in course_enrollments:
        if not terms.get(enrollment['academic_term']):
            terms[enrollment['academic_term']] = []
        if enrollment['enrollment_status'] not in ['Graduated', 'Failed']:
            enrollment['enrollment_status'] = ''
        terms[enrollment['academic_term']].append(enrollment)
        if enrollment['graduation_grade']:
            if not terms_gpa.get(enrollment['academic_term']):
                terms_gpa[enrollment['academic_term']] = {}
                terms_gpa[enrollment['academic_term']]['count'] = float(enrollment['total_course_hours'])
                terms_gpa[enrollment['academic_term']]['grade'] = float(enrollment['graduation_grade']) * float(enrollment['total_course_hours'])
            else:
                terms_gpa[enrollment['academic_term']]['count'] += float(enrollment['total_course_hours'])
                terms_gpa[enrollment['academic_term']]['grade'] += (float(enrollment['graduation_grade']) * float(enrollment['total_course_hours']))
    total_grades = 0
    total_courses = 0
    cgpa = 0
    for term in terms_gpa.values():
        term['gpa'] = term['grade'] / term['count']
        total_grades += term['grade']
        total_courses += term['count']
    if total_courses > 0:
        cgpa = total_grades / total_courses
    return terms, terms_gpa, cgpa