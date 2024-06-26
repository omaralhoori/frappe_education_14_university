# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from education.education.utils import validate_duplicate_student


class StudentGroup(Document):
	def validate(self):
		self.validate_mandatory_fields()
		self.validate_strength()
		self.validate_students()
		self.validate_and_set_child_table_fields()
		validate_duplicate_student(self.students)

	def validate_mandatory_fields(self):
		if self.group_based_on == "Course" and not self.course:
			frappe.throw(_("Please select Course"))
		if self.group_based_on == "Course" and (not self.program and self.batch):
			frappe.throw(_("Please select Program"))
		if self.group_based_on == "Batch" and not self.program:
			frappe.throw(_("Please select Program"))

	def validate_strength(self):
		if cint(self.max_strength) < 0:
			frappe.throw(_("""Max strength cannot be less than zero."""))
		if self.max_strength and len(self.students) > self.max_strength:
			frappe.throw(
				_("""Cannot enroll more than {0} students for {1} student group.""").format(
					self.max_strength, self.name
				)
			)

	def validate_students(self):
		program_enrollment = get_program_enrollment(
			self.academic_year,
			self.academic_term,
			self.program,
			self.batch,
			self.student_category,
			self.course,
		)
		students = [d.student for d in program_enrollment] if program_enrollment else []
		for d in self.students:
			if (
				not frappe.db.get_value("Student", d.student, "enabled")
				and d.active
				and not self.disabled
			):
				frappe.throw(
					_("{0} - {1} is inactive student").format(d.group_roll_number, d.student_name)
				)

			if (
				(self.group_based_on == "Batch")
				and cint(frappe.defaults.get_defaults().validate_batch)
				and d.student not in students
			):
				frappe.throw(
					_("{0} - {1} is not enrolled in the Batch {2}").format(
						d.group_roll_number, d.student_name, self.batch
					)
				)

			if (
				(self.group_based_on == "Course")
				and cint(frappe.defaults.get_defaults().validate_course)
				and (d.student not in students)
			):
				frappe.throw(
					_("{0} - {1} is not enrolled in the Course {2}").format(
						d.group_roll_number, d.student_name, self.course
					)
				)

	def validate_and_set_child_table_fields(self):
		roll_numbers = [d.group_roll_number for d in self.students if d.group_roll_number]
		max_roll_no = max(roll_numbers) if roll_numbers else 0
		roll_no_list = []
		for d in self.students:
			if not d.student_name:
				d.student_name = frappe.db.get_value("Student", d.student, "student_name")
			if not d.group_roll_number:
				max_roll_no += 1
				d.group_roll_number = max_roll_no
			if d.group_roll_number in roll_no_list:
				frappe.throw(_("Duplicate roll number for student {0}").format(d.student_name))
			else:
				roll_no_list.append(d.group_roll_number)


def get_course_enrolled_students(academic_year, academic_term, program, course):
	return frappe.db.get_all("Course Enrollment", {"academic_year": academic_year, "academic_term": academic_term, "program": program, "course": course}, ["student", "student_name"])


@frappe.whitelist()
def get_students(
	academic_year,
	group_based_on,
	academic_term=None,
	program=None,
	batch=None,
	student_category=None,
	course=None,
):
	if group_based_on == 'Course':
		enrolled_students = get_course_enrolled_students(academic_year, academic_term, program, course)
	else:
		enrolled_students = get_program_enrollment(
			academic_year, academic_term, program, batch, student_category, course
		)
	print(len(enrolled_students))
	if enrolled_students:
		student_list = []
		for s in enrolled_students:
			if frappe.db.get_value("Student", s.student, "enabled"):
				s.update({"active": 1})
			else:
				s.update({"active": 0})
			student_list.append(s)
		return student_list
	else:
		frappe.msgprint(_("No students found"))
		return []


def get_program_enrollment(
	academic_year,
	academic_term=None,
	program=None,
	batch=None,
	student_category=None,
	course=None,
):

	condition1 = " "
	condition2 = " "
	# if academic_term:
	# 	condition1 += " and pec.academic_term = %(academic_term)s"
	# pe.academic_year = %(academic_year)s  
	if program:
		condition1 += " and pe.program = %(program)s"
	if batch:
		condition1 += " and pe.student_batch_name = %(batch)s"
	if student_category:
		condition1 += " and pe.student_category = %(student_category)s"
	if course:
		condition1 += " and pe.name = pec.program_enrollment and pec.course = %(course)s"
		condition1 += " and pec.academic_term = %(academic_term)s"
		condition2 = ", `tabCourse Enrollment` pec"
	print(condition1)
	print(condition2)
	results = frappe.db.sql(
		"""
		select
			pe.student, pe.student_name
		from
			`tabProgram Enrollment` pe {condition2}
		where pe.docstatus = 1 {condition1}
		order by
			pe.student_name asc
		""".format(
			condition1=condition1, condition2=condition2
		),
		(
			{
				"academic_year": academic_year,
				"academic_term": academic_term,
				"program": program,
				"batch": batch,
				"student_category": student_category,
				"course": course,
			}
		),
		as_dict=1,
	)
	for item in results:
		if item.get('student_name') == 'yassmin ahmed saeed':
			print(item)
	print(len(results))
	return results

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fetch_students(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("group_based_on") != "Activity":
		enrolled_students = get_program_enrollment(
			filters.get("academic_year"),
			filters.get("academic_term"),
			filters.get("program"),
			filters.get("batch"),
			filters.get("student_category"),
			filters.get("course"),
		)
		student_group_student = frappe.db.sql_list(
			"""select student from `tabStudent Group Student` where parent=%s""",
			(filters.get("student_group")),
		)
		students = (
			[d.student for d in enrolled_students if d.student not in student_group_student]
			if enrolled_students
			else [""]
		) or [""]
		return frappe.db.sql(
			"""select name, student_name from tabStudent
			where name in ({0}) and (`{1}` LIKE %s or student_name LIKE %s)
			order by idx desc, name
			limit %s, %s""".format(
				", ".join(["%s"] * len(students)), searchfield
			),
			tuple(students + ["%%%s%%" % txt, "%%%s%%" % txt, start, page_len]),
		)
	else:
		return frappe.db.sql(
			"""select name, student_name from tabStudent
			where `{0}` LIKE %s or title LIKE %s
			order by idx desc, name
			limit %s, %s""".format(
				searchfield
			),
			tuple(["%%%s%%" % txt, "%%%s%%" % txt, start, page_len]),
		)


def get_course_registered_group(course):
	current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year")
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	group = frappe.db.sql("""
		select enrlAppCrs.group as application_group FROM `tabCourse Enrollment Applied Course` as enrlAppCrs
		INNER JOIN `tabCourse Enrollment Applicant` as crsEnrlApp ON  crsEnrlApp.name=enrlAppCrs.parent
		WHERE crsEnrlApp.student=%(student)s AND academic_term=%(academic_term)s AND academic_year=%(academic_year)s and course=%(course)s
	""", {
		"student": student,
		"academic_term": current_academic_term, 
       "academic_year": current_academic_year, 
	   "course": course}, as_dict=True)
	if len(group) > 0: return group[0]

def get_course_groups(course):
	current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year")
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
	student_gender = frappe.db.get_value("Student", {"user": frappe.session.user}, ['gender'])
	where_stmt = ""
	if student_gender:
		where_stmt = f"AND (tsg.group_gender='{student_gender}' or tsg.group_gender is NULL)"
	return frappe.db.sql("""
		select tsg.name as group_id, tsg.student_group_name,tsg.max_strength, crs_scd.course_day, IFNULL(grp_std.student_count,0) as student_count ,
		crs_scd.from_time, crs_scd.to_time, crs_scd.instructor FROM `tabStudent Group` tsg
		LEFT JOIN
		(select tcs.student_group, WEEKDAY(tcs.schedule_date) as course_day, tcs.from_time, tcs.to_time, tcs.instructor
		FROM `tabCourse Schedule` tcs) as crs_scd
		ON crs_scd.student_group=tsg.name
		LEFT JOIN
		(select IFNULL(count(name), 0) as student_count, parent  FROM `tabStudent Group Student` tsgs
		GROUP BY parent
		) as grp_std ON grp_std.parent=tsg.name
		WHERE tsg.course=%(course)s AND tsg.academic_year=%(academic_year)s AND tsg.academic_term=%(academic_term)s {where_stmt}
		GROUP By tsg.name, crs_scd.course_day, crs_scd.from_time
	""".format(where_stmt=where_stmt), {"academic_term": current_academic_term, "academic_year": current_academic_year, "course": course}, as_dict=True)

def get_student_course_group(course):
	current_academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year")
	current_academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, ['name'])
	
	return frappe.db.sql("""
		select tsg.name as group_id, tsg.student_group_name,tsg.max_strength, crs_scd.course_day,tsg.virtual_room_link, crs.resource_link,
		crs_scd.from_time, crs_scd.to_time, crs_scd.instructor FROM `tabStudent Group` tsg
		INNER JOIN `tabStudent Group Student` tsgs ON tsgs.parent=tsg.name
		LEFT JOIN
		(select tcs.student_group, WEEKDAY(tcs.schedule_date) as course_day, tcs.from_time, tcs.to_time, tcs.instructor
		FROM `tabCourse Schedule` tcs) as crs_scd
		ON crs_scd.student_group=tsg.name
		INNER JOIN `tabCourse` as crs ON crs.name = tsg.course
		WHERE tsg.course=%(course)s AND tsg.academic_year=%(academic_year)s AND tsg.academic_term=%(academic_term)s AND tsgs.student=%(student)s
		LIMIT 1
	""", {"academic_term": current_academic_term, "academic_year": current_academic_year, "course": course, "student": student}, as_dict=True)