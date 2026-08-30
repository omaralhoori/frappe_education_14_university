# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _


DIMENSIONS = (
	"nationality",
	"country",
	"gender",
	"major",
	"educational_level",
	"age_group",
)

AGE_GROUP_ORDER = (
	"Under 18",
	"18-22",
	"23-27",
	"28-35",
	"36+",
	"Unknown",
)

AGE_GROUP_SQL = """
	CASE
		WHEN s.date_of_birth IS NULL THEN 'Unknown'
		WHEN TIMESTAMPDIFF(YEAR, s.date_of_birth, CURDATE()) < 18 THEN 'Under 18'
		WHEN TIMESTAMPDIFF(YEAR, s.date_of_birth, CURDATE()) BETWEEN 18 AND 22 THEN '18-22'
		WHEN TIMESTAMPDIFF(YEAR, s.date_of_birth, CURDATE()) BETWEEN 23 AND 27 THEN '23-27'
		WHEN TIMESTAMPDIFF(YEAR, s.date_of_birth, CURDATE()) BETWEEN 28 AND 35 THEN '28-35'
		ELSE '36+'
	END
"""


@frappe.whitelist()
def get_page_html():
	"""Render Student Dashboard HTML template."""
	return frappe.render_template(
		"education/page/student_dashboard/student_dashboard.html", {}
	)


@frappe.whitelist()
def get_student_analytics(program=None, academic_term=None):
	"""Demographics for first-time CEA applicants in the selected term (no prior registration)."""
	if not program:
		frappe.throw(_("Please select a Program"))

	if not academic_term:
		academic_term = frappe.db.get_single_value(
			"Education Settings", "current_academic_term"
		)

	empty = {dim: {"labels": [], "values": []} for dim in DIMENSIONS}
	if not academic_term:
		return {
			"total_students": 0,
			"academic_term": None,
			**empty,
		}

	filters = {
		"program": program,
		"academic_term": academic_term,
	}

	# First-time in selected term:
	# has non-rejected CEA in this term, and no non-rejected CEA in any earlier term
	# (by Academic Term.term_start_date) for the same program.
	# Later terms do not disqualify the student when viewing a past term.
	first_time_where = """
		cea.program = %(program)s
		AND cea.academic_term = %(academic_term)s
		AND IFNULL(cea.application_status, '') != 'Rejected'
		AND cea.student IS NOT NULL
		AND NOT EXISTS (
			SELECT 1
			FROM `tabCourse Enrollment Applicant` prev
			INNER JOIN `tabAcademic Term` prev_at
				ON prev_at.name = prev.academic_term
			INNER JOIN `tabAcademic Term` sel_at
				ON sel_at.name = %(academic_term)s
			WHERE prev.student = cea.student
				AND prev.program = %(program)s
				AND IFNULL(prev.application_status, '') != 'Rejected'
				AND prev.student IS NOT NULL
				AND prev_at.term_start_date < sel_at.term_start_date
		)
	"""

	total_students = frappe.db.sql(
		f"""
		SELECT COUNT(DISTINCT cea.student)
		FROM `tabCourse Enrollment Applicant` cea
		WHERE {first_time_where}
		""",
		filters,
	)[0][0]

	result = {
		"total_students": int(total_students or 0),
		"academic_term": academic_term,
	}

	for dim in DIMENSIONS:
		dim_expr = (
			AGE_GROUP_SQL
			if dim == "age_group"
			else f"COALESCE(NULLIF(s.{dim}, ''), 'Unknown')"
		)
		dim_rows = frappe.db.sql(
			f"""
			SELECT
				{dim_expr} AS dim_value,
				COUNT(DISTINCT s.name) AS student_count
			FROM `tabStudent` s
			INNER JOIN `tabCourse Enrollment Applicant` cea
				ON cea.student = s.name
			WHERE {first_time_where}
			GROUP BY {dim_expr}
			""",
			filters,
			as_dict=True,
		)
		labels_values = {
			(row.dim_value or "Unknown"): int(row.student_count or 0) for row in dim_rows
		}
		if dim == "age_group":
			labels = [l for l in AGE_GROUP_ORDER if l in labels_values]
			labels += sorted(l for l in labels_values if l not in AGE_GROUP_ORDER)
		else:
			labels = sorted(labels_values.keys(), key=lambda l: (-labels_values[l], l))

		result[dim] = {
			"labels": labels,
			"values": [labels_values[l] for l in labels],
		}

	return result



@frappe.whitelist()
def get_course_registration_stats(program=None, academic_term=None):
	"""Course registration stats from Course Enrollment Applicant for a term."""
	if not program:
		frappe.throw(_("Please select a Program"))

	if not academic_term:
		academic_term = frappe.db.get_single_value(
			"Education Settings", "current_academic_term"
		)

	academic_year = None
	if academic_term:
		academic_year = frappe.db.get_value("Academic Term", academic_term, "academic_year")
	if not academic_year:
		academic_year = frappe.db.get_single_value(
			"Education Settings", "current_academic_year"
		)

	if not academic_term:
		return {
			"academic_year": academic_year,
			"academic_term": academic_term,
			"applicant_count": 0,
			"courses": [],
		}

	filters = {
		"program": program,
		"academic_term": academic_term,
	}

	applicant_count = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT cea.student)
		FROM `tabCourse Enrollment Applicant` cea
		WHERE cea.program = %(program)s
			AND cea.academic_term = %(academic_term)s
			AND IFNULL(cea.application_status, '') != 'Rejected'
			AND cea.student IS NOT NULL
		""",
		filters,
	)[0][0]

	courses = frappe.db.sql(
		"""
		SELECT
			ceac.course,
			COALESCE(NULLIF(c.course_name, ''), ceac.course) AS course_name,
			COUNT(DISTINCT cea.student) AS student_count
		FROM `tabCourse Enrollment Applicant` cea
		INNER JOIN `tabCourse Enrollment Applied Course` ceac
			ON ceac.parent = cea.name
		LEFT JOIN `tabCourse` c
			ON c.name = ceac.course
		WHERE cea.program = %(program)s
			AND cea.academic_term = %(academic_term)s
			AND IFNULL(cea.application_status, '') != 'Rejected'
			AND cea.student IS NOT NULL
			AND ceac.course IS NOT NULL
		GROUP BY ceac.course, COALESCE(NULLIF(c.course_name, ''), ceac.course)
		ORDER BY student_count DESC, course_name ASC
		""",
		filters,
		as_dict=True,
	)

	return {
		"academic_year": academic_year,
		"academic_term": academic_term,
		"applicant_count": int(applicant_count or 0),
		"courses": courses,
	}
