# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import cint, cstr, strip_html_tags

# Realtime event names (must match the frontend subscriptions)
PROGRESS_EVENT = "new_registered_students_delete_progress"
DONE_EVENT = "new_registered_students_delete_done"
# Cache key used to flag that a background "delete all" job is currently running
RUNNING_CACHE_KEY = "new_registered_students_delete_running"

# Doctypes that link to a Student and must be removed before the Student itself.
# Order matters: dependents first, Student last, User after the Student.
STUDENT_DEPENDENTS = [
	"Fees",
	#"Course Enrollment",
	"Course Enrollment Applicant",
	"Drop Course",
	"Drop Coursepack",
	"Study Postponement",
	"Program Enrollment",
]


def _check_permission():
	"""Only System Managers may use this page and its server methods."""
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_page_html():
	"""Return the rendered HTML body of the page."""
	_check_permission()
	return frappe.render_template(
		"education/page/new_registered_students/new_registered_students.html", {}
	)


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def _parse_filters(filters):
	if isinstance(filters, str):
		filters = json.loads(filters or "{}")
	return filters or {}


def _build_conditions(filters):
	"""Build the WHERE conditions and parameters for the student query.

	A student qualifies as a deletable "new registered student" when they:
	  * are NOT a scholarship student (no Program Enrollment with has_scholarship),
	  * have NEVER made any payment (no Fees with a paid amount or an uploaded receipt),
	  * have NO course enrollment.
	"""
	conditions = [
		# Not a scholarship student
		"""s.name NOT IN (
			SELECT pe.student FROM `tabProgram Enrollment` pe
			WHERE pe.has_scholarship = 1 AND pe.student IS NOT NULL
		)""",
		# Never made any payment: no fee with money received or a receipt attached
		"""s.name NOT IN (
			SELECT f.student FROM `tabFees` f
			WHERE f.student IS NOT NULL
			AND (
				(f.grand_total - f.outstanding_amount) > 0
				OR IFNULL(f.receipt_amount, 0) > 0
				OR IFNULL(f.receipt_uploaded, 0) = 1
			)
		)""",
		# No course enrollment
		"""s.name NOT IN (
			SELECT ce.student FROM `tabCourse Enrollment` ce
			WHERE ce.student IS NOT NULL
		)""",
		# No Journal Entry Account
		"""s.name NOT IN (
			SELECT ja.party FROM `tabJournal Entry Account` ja
			WHERE ja.party IS NOT NULL
		)""",
	]
	values = {}

	if filters.get("educational_year"):
		conditions.append("s.educational_year = %(educational_year)s")
		values["educational_year"] = filters["educational_year"]

	if filters.get("program"):
		# A student's program lives in their Program Enrollment(s) (a student may
		# have several, or none). Match on the enrollment rather than the
		# unreliable Student.program field.
		conditions.append(
			"""s.name IN (
				SELECT pe.student FROM `tabProgram Enrollment` pe
				WHERE pe.program = %(program)s AND pe.student IS NOT NULL
			)"""
		)
		values["program"] = filters["program"]

	if filters.get("from_date"):
		conditions.append("s.joining_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("s.joining_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	if filters.get("search"):
		conditions.append(
			"""(s.name LIKE %(search)s
				OR s.student_name LIKE %(search)s
				OR s.student_email_id LIKE %(search)s)"""
		)
		values["search"] = "%" + filters["search"] + "%"

	return " AND ".join(conditions), values


@frappe.whitelist()
def get_students(filters=None, page_length=50, page_start=0):
	"""Return the paginated list of deletable new registered students."""
	_check_permission()
	filters = _parse_filters(filters)
	where_clause, values = _build_conditions(filters)

	total_count = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabStudent` s WHERE {where_clause}", values
	)[0][0]

	values["page_length"] = cint(page_length)
	values["page_start"] = cint(page_start)

	data = frappe.db.sql(
		f"""
		SELECT
			s.name AS student_id,
			s.student_name,
			CONCAT_WS(' ', s.first_name, s.middle_name, s.last_name) AS full_name,
			s.student_email_id AS email,
			s.student_mobile_number AS mobile_no,
			s.joining_date,
			s.educational_year,
			s.user,
			s.creation
		FROM `tabStudent` s
		WHERE {where_clause}
		ORDER BY s.creation DESC
		LIMIT %(page_length)s OFFSET %(page_start)s
		""",
		values,
		as_dict=True,
	)

	return {
		"data": data,
		"total_count": total_count,
		"page_length": cint(page_length),
		"page_start": cint(page_start),
		"delete_running": bool(frappe.cache().get_value(RUNNING_CACHE_KEY)),
	}


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


def _delete_student_data(student_id):
	"""Delete a single student and everything linked to them.

	All work happens inside a savepoint so that a failure on any one student
	leaves that student fully intact (all-or-nothing per student).

	Returns a tuple ``(success: bool, error: str)``.
	"""
	savepoint = "del_" + frappe.generate_hash(length=8)
	frappe.db.savepoint(savepoint)
	try:
		# 1. Remove all dependent documents that link to the student
		for doctype in STUDENT_DEPENDENTS:
			if not frappe.db.exists("DocType", doctype):
				continue
			for name in frappe.get_all(doctype, filters={"student": student_id}, pluck="name"):
				doc = frappe.get_doc(doctype, name)
				if getattr(doc, "docstatus", 0) == 1:
					doc.cancel()
				frappe.delete_doc(doctype, name, ignore_permissions=True, delete_permanently=True)

		# 2. Capture the linked user before deleting the student
		user = frappe.db.get_value("Student", student_id, "user")

		# 3. Delete the student
		frappe.delete_doc("Student", student_id, ignore_permissions=True, delete_permanently=True)

		# 4. Delete the linked user (and its access logs first)
		if user and frappe.db.exists("User", user):
			for log in frappe.get_all("Access Log", filters={"user": user}, pluck="name"):
				frappe.delete_doc("Access Log", log, ignore_permissions=True, delete_permanently=True)
			# Notification Settings
			for nts in frappe.get_all("Notification Settings", filters={"user": user}, pluck="name"):
				print("Deleting Notification Settings", nts)
				frappe.delete_doc("Notification Settings", nts, ignore_permissions=True, delete_permanently=True)
			frappe.delete_doc("User", user, ignore_permissions=True, delete_permanently=True)

		return True, ""
	except Exception as e:
		# Undo every change made for this student so it is left untouched
		frappe.db.rollback(save_point=savepoint)
		frappe.log_error(frappe.get_traceback(), f"Delete New Registered Student: {student_id}")
		err = strip_html_tags(cstr(e)).strip() or e.__class__.__name__
		frappe.clear_messages()
		return False, err


@frappe.whitelist()
def delete_student(student):
	"""Delete a single student synchronously (used by the per-row delete button)."""
	_check_permission()
	if not frappe.db.exists("Student", student):
		return {"success": False, "error": _("Student {0} no longer exists").format(student)}

	student_name = frappe.db.get_value("Student", student, "student_name")
	success, error = _delete_student_data(student)
	if success:
		frappe.db.commit()
	return {
		"success": success,
		"error": error,
		"student": student,
		"student_name": student_name,
	}


@frappe.whitelist()
def delete_all(filters=None):
	"""Enqueue a background job that deletes every student matching the filters."""
	_check_permission()

	if frappe.cache().get_value(RUNNING_CACHE_KEY):
		return {"enqueued": False, "message": _("A deletion job is already running.")}

	filters = _parse_filters(filters)
	where_clause, values = _build_conditions(filters)
	student_ids = frappe.db.sql(
		f"SELECT s.name FROM `tabStudent` s WHERE {where_clause} ORDER BY s.creation DESC",
		values,
		pluck=True,
	)

	if not student_ids:
		return {"enqueued": False, "message": _("No matching students to delete.")}

	# Flag the job as running (1 hour ttl as a safety net)
	frappe.cache().set_value(RUNNING_CACHE_KEY, 1, expires_in_sec=3600)

	frappe.enqueue(
		"education.education.page.new_registered_students.new_registered_students.delete_all_background",
		queue="long",
		timeout=14400,
		student_ids=student_ids,
		user=frappe.session.user,
	)

	return {"enqueued": True, "total": len(student_ids)}


def delete_all_background(student_ids, user):
	"""Background worker: delete all students and stream progress to the user."""
	total = len(student_ids)
	deleted = 0
	failures = []

	try:
		for index, student_id in enumerate(student_ids, start=1):
			student_name = frappe.db.get_value("Student", student_id, "student_name") or student_id
			success, error = _delete_student_data(student_id)
			if success:
				deleted += 1
			else:
				failures.append(
					{"student": student_id, "student_name": student_name, "error": error}
				)

			frappe.publish_realtime(
				PROGRESS_EVENT,
				{
					"current": index,
					"total": total,
					"deleted": deleted,
					"failed": len(failures),
					"student": student_id,
					"student_name": student_name,
				},
				user=user,
			)

			# Commit in batches so progress is durable and locks stay short
			if index % 10 == 0:
				frappe.db.commit()

		frappe.db.commit()
	finally:
		frappe.cache().delete_value(RUNNING_CACHE_KEY)
		frappe.publish_realtime(
			DONE_EVENT,
			{"total": total, "deleted": deleted, "failures": failures},
			user=user,
		)


@frappe.whitelist()
def is_delete_running():
	"""Return whether a background deletion job is currently running."""
	_check_permission()
	return {"running": bool(frappe.cache().get_value(RUNNING_CACHE_KEY))}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@frappe.whitelist()
def export_students(filters=None):
	"""Stream an XLSX file of the matching students and their data."""
	_check_permission()
	from frappe.utils.xlsxutils import build_xlsx_response

	filters = _parse_filters(filters)
	where_clause, values = _build_conditions(filters)

	students = frappe.db.sql(
		f"""
		SELECT
			s.name AS student_id,
			s.student_name,
			CONCAT_WS(' ', s.first_name, s.middle_name, s.last_name) AS full_name,
			s.student_email_id AS email,
			s.student_mobile_number AS mobile_no,
			s.user,
			s.joining_date,
			s.educational_year,
			s.academic_year,
			(SELECT GROUP_CONCAT(DISTINCT pe.program SEPARATOR ', ')
				FROM `tabProgram Enrollment` pe WHERE pe.student = s.name) AS program,
			s.nationality,
			s.gender,
			s.date_of_birth,
			s.creation
		FROM `tabStudent` s
		WHERE {where_clause}
		ORDER BY s.creation DESC
		""",
		values,
		as_dict=True,
	)

	headers = [
		_("Student ID"),
		_("Student Name"),
		_("Full Name"),
		_("Email"),
		_("Mobile No"),
		_("User"),
		_("Joining Date"),
		_("Educational Year"),
		_("Academic Year"),
		_("Program"),
		_("Nationality"),
		_("Gender"),
		_("Date of Birth"),
		_("Registered On"),
	]

	rows = [headers]
	for s in students:
		rows.append(
			[
				s.student_id,
				s.student_name,
				s.full_name,
				s.email,
				s.mobile_no,
				s.user,
				cstr(s.joining_date),
				s.educational_year,
				s.academic_year,
				s.program,
				s.nationality,
				s.gender,
				cstr(s.date_of_birth),
				cstr(s.creation),
			]
		)

	build_xlsx_response(rows, "New Registered Students")
