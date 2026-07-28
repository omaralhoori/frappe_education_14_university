# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict


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
def get_student_analytics(program=None):
	"""Aggregate enrolled students by educational year and demographics."""
	if not program:
		frappe.throw(_("Please select a Program"))

	year_order_map = {
		d.name: d.year_order or 9999
		for d in frappe.get_all("Educational Year", fields=["name", "year_order"])
	}

	student_years = frappe.db.sql(
		"""
		SELECT DISTINCT
			s.name AS student,
			COALESCE(
				NULLIF(pe.educational_year, ''),
				NULLIF(s.educational_year, ''),
				'Unknown'
			) AS educational_year
		FROM `tabStudent` s
		INNER JOIN `tabProgram Enrollment` pe
			ON pe.student = s.name
		WHERE pe.program = %(program)s
			AND pe.docstatus < 2
			AND pe.student IS NOT NULL
		""",
		{"program": program},
		as_dict=True,
	)

	all_students_per_year = defaultdict(set)
	for sy in student_years:
		all_students_per_year[sy.educational_year].add(sy.student)

	year_data = defaultdict(lambda: {dim: defaultdict(int) for dim in DIMENSIONS})

	edu_year_expr = """
		COALESCE(
			NULLIF(pe.educational_year, ''),
			NULLIF(s.educational_year, ''),
			'Unknown'
		)
	"""

	for dim in DIMENSIONS:
		dim_expr = (
			AGE_GROUP_SQL
			if dim == "age_group"
			else f"COALESCE(NULLIF(s.{dim}, ''), 'Unknown')"
		)
		dim_rows = frappe.db.sql(
			f"""
			SELECT
				{edu_year_expr} AS educational_year,
				{dim_expr} AS dim_value,
				COUNT(DISTINCT s.name) AS student_count
			FROM `tabStudent` s
			INNER JOIN `tabProgram Enrollment` pe
				ON pe.student = s.name
			WHERE pe.program = %(program)s
				AND pe.docstatus < 2
				AND pe.student IS NOT NULL
			GROUP BY {edu_year_expr}, {dim_expr}
			""",
			{"program": program},
			as_dict=True,
		)
		for row in dim_rows:
			year = row.educational_year or "Unknown"
			label = row.dim_value or "Unknown"
			year_data[year][dim][label] = int(row.student_count or 0)

	# Include years that have students even if a dimension query returned nothing
	for year in all_students_per_year:
		_ = year_data[year]

	years = []
	for year in sorted(
		year_data.keys(),
		key=lambda y: (year_order_map.get(y, 9999), y),
	):
		entry = {
			"educational_year": year,
			"total": len(all_students_per_year.get(year, set())),
		}
		for dim in DIMENSIONS:
			labels_values = year_data[year][dim]
			if dim == "age_group":
				ordered_labels = [l for l in AGE_GROUP_ORDER if l in labels_values]
				extra = sorted(l for l in labels_values if l not in AGE_GROUP_ORDER)
				labels = ordered_labels + extra
			else:
				labels = sorted(
					labels_values.keys(),
					key=lambda l: (-labels_values[l], l),
				)
			entry[dim] = {
				"labels": labels,
				"values": [labels_values[l] for l in labels],
			}
		years.append(entry)

	total_students = len(
		{s for students in all_students_per_year.values() for s in students}
	)

	return {
		"years": years,
		"total_students": total_students,
	}


@frappe.whitelist()
def get_course_registration_stats(program=None):
	"""Course registration stats from Course Enrollment Applicant for current term."""
	if not program:
		frappe.throw(_("Please select a Program"))

	academic_year = frappe.db.get_single_value(
		"Education Settings", "current_academic_year"
	)
	academic_term = frappe.db.get_single_value(
		"Education Settings", "current_academic_term"
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
