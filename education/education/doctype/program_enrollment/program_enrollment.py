# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder.functions import Min
from frappe.utils import comma_and, get_link_to_form, getdate
from education.education.doctype.program_graduation_request.graduation_certificate import create_program_certificate

class ProgramEnrollment(Document):
	def validate(self):
		self.validate_duplication()
		self.validate_academic_year()
		if self.academic_term:
			self.validate_academic_term()		
		if not self.student_name:
			self.student_name = frappe.db.get_value("Student", self.student, "title")
		# if not self.courses:
		# 	self.extend("courses", self.get_courses())

	@frappe.whitelist()
	def generate_certificate(self, certificate_date=None):
		certificate_file = create_program_certificate(self.name, certificate_date or frappe.utils.nowdate() , self.program)
		# frappe.db.set_value("Program Enrollment",student.enrollment, {
		# 	"graduated": 1,
		# 	"graduation_date": self.certificate_creation_date,
		# 	"certificate": certificate_file
		# 	})
		self.db_set("graduated", 1)
		self.db_set("graduation_date", certificate_date or frappe.utils.nowdate())
		self.db_set("certificate", certificate_file)

	def on_submit(self):
		self.update_student_joining_date()
		self.make_fee_records()
		self.create_course_enrollments()
		self.update_student_program_type()

	def update_student_program_type(self):
		if frappe.db.get_value("Program", self.program, ['is_coursepack']):
			frappe.db.set_value("Student", self.student, 'is_coursepack_student', 1)

	def validate_academic_year(self):
		start_date, end_date = frappe.db.get_value(
			"Academic Year", self.academic_year, ["year_start_date", "year_end_date"]
		)
		if self.enrollment_date:
			if start_date and getdate(self.enrollment_date) < getdate(start_date):
				frappe.throw(
					_(
						"Enrollment Date cannot be before the Start Date of the Academic Year {0}"
					).format(get_link_to_form("Academic Year", self.academic_year))
				)

			if end_date and getdate(self.enrollment_date) > getdate(end_date):
				frappe.throw(
					_("Enrollment Date cannot be after the End Date of the Academic Term {0}").format(
						get_link_to_form("Academic Year", self.academic_year)
					)
				)

	def validate_academic_term(self):
		start_date, end_date = frappe.db.get_value(
			"Academic Term", self.academic_term, ["term_start_date", "term_end_date"]
		)
		if self.enrollment_date:
			# if start_date and getdate(self.enrollment_date) < getdate(start_date):
			# 	frappe.throw(
			# 		_(
			# 			"Enrollment Date cannot be before the Start Date of the Academic Term {0}"
			# 		).format(get_link_to_form("Academic Term", self.academic_term))
			# 	)

			if end_date and getdate(self.enrollment_date) > getdate(end_date):
				frappe.throw(
					_("Enrollment Date cannot be after the End Date of the Academic Term {0}").format(
						get_link_to_form("Academic Term", self.academic_term)
					)
				)

	def validate_duplication(self):
		enrollment = frappe.get_all(
			"Program Enrollment",
			filters={
				"student": self.student,
				"program": self.program,
				"academic_year": self.academic_year,
				"academic_term": self.academic_term,
				"docstatus": ("<", 2),
				"name": ("!=", self.name),
			},
		)
		if enrollment:
			frappe.throw(_("Student is already enrolled."))

	def update_student_joining_date(self):
		table = frappe.qb.DocType("Program Enrollment")
		date = (
			frappe.qb.from_(table)
			.select(Min(table.enrollment_date).as_("enrollment_date"))
			.where(table.student == self.student)
		).run(as_dict=True)

		if date:
			frappe.db.set_value("Student", self.student, "joining_date", date[0].enrollment_date)

	def make_fee_records(self):
		from education.education.api import get_fee_components

		fee_list = []
		for d in self.fees:
			fee_components = get_fee_components(d.fee_structure)
			if fee_components:
				fees = frappe.new_doc("Fees")
				fees.update(
					{
						"student": self.student,
						"academic_year": self.academic_year,
						"academic_term": d.academic_term,
						"fee_structure": d.fee_structure,
						"program": self.program,
						"due_date": d.due_date,
						"student_name": self.student_name,
						"program_enrollment": self.name,
						"components": fee_components,
					}
				)

				fees.save()
				fees.submit()
				fee_list.append(fees.name)
		if fee_list:
			fee_list = [
				"""<a href="/app/Form/Fees/%s" target="_blank">%s</a>""" % (fee, fee)
				for fee in fee_list
			]
			msgprint(_("Fee Records Created - {0}").format(comma_and(fee_list)))

	@frappe.whitelist()
	def get_courses(self):
		return frappe.db.sql(
			"""select course from `tabProgram Course` where parent = %s and required = 1""",
			(self.program),
			as_dict=1,
		)

	def create_course_enrollments(self):
		for course in self.courses:
			filters = {
				"student": self.student,
				"course": course.course,
				"program_enrollment": self.name
			}
			if not frappe.db.exists("Course Enrollment", filters):
				filters.update({
					"doctype": "Course Enrollment",
					"enrollment_date": self.enrollment_date
				})
				frappe.get_doc(filters).save()


	def get_all_course_enrollments(self):
		course_enrollment_names = frappe.get_list(
			"Course Enrollment", filters={"program_enrollment": self.name}
		)
		return [
			frappe.get_doc("Course Enrollment", course_enrollment.name)
			for course_enrollment in course_enrollment_names
		]

	def get_quiz_progress(self):
		student = frappe.get_doc("Student", self.student)
		quiz_progress = frappe._dict()
		progress_list = []
		for course_enrollment in self.get_all_course_enrollments():
			course_progress = course_enrollment.get_progress(student)
			for progress_item in course_progress:
				if progress_item["content_type"] == "Quiz":
					progress_item["course"] = course_enrollment.course
					progress_list.append(progress_item)
		if not progress_list:
			return None
		quiz_progress.quiz_attempt = progress_list
		quiz_progress.name = self.program
		quiz_progress.program = self.program
		return quiz_progress


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_program_courses(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("program"):
		frappe.msgprint(_("Please select a Program first."))
		return []

	result =  frappe.db.sql(
		"""select course, course_name from `tabProgram Course`
		where  parent = %(program)s and (course_name like %(txt)s or course like %(txt)s) {match_cond}
		order by
			if(locate(%(_txt)s, course_name), locate(%(_txt)s, course_name), 99999),
			if(locate(%(_txt)s, course), locate(%(_txt)s, course), 99999),
			idx desc,
			`tabProgram Course`.course asc
		limit {start}, {page_len}""".format(
			match_cond=get_match_cond(doctype), start=start, page_len=page_len
		),
		{
			"txt": "%{0}%".format(txt),
			"_txt": txt.replace("%", ""),
			"program": filters["program"],
		},
	)
	return result


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_students(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("academic_term"):
		filters["academic_term"] = frappe.defaults.get_defaults().academic_term

	if not filters.get("academic_year"):
		filters["academic_year"] = frappe.defaults.get_defaults().academic_year

	enrolled_students = frappe.get_list(
		"Program Enrollment",
		filters={
			"academic_term": filters.get("academic_term"),
			"academic_year": filters.get("academic_year"),
		},
		fields=["student"],
	)

	students = [d.student for d in enrolled_students] if enrolled_students else [""]

	return frappe.db.sql(
		"""select
			name, student_name from tabStudent
		where
			name not in (%s)
		and
			`%s` LIKE %s
		order by
			idx desc, name
		limit %s, %s"""
		% (", ".join(["%s"] * len(students)), searchfield, "%s", "%s", "%s"),
		tuple(students + ["%%%s%%" % txt, start, page_len]),
	)


def check_student_program_enrolled():
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name", 'student_name'])
	if not student: return False
	if frappe.db.get_value("Program Enrollment", {"student": student[0]}, ['name']):
		return True
	years = frappe.db.get_all("Educational Year", fields = ["name"], order_by="year_order asc", page_length=1)
	programs = frappe.db.get_all("Program", fields = ["name"], page_length=1)

	if not years or not programs: return False
	program_enrollment = frappe.new_doc("Program Enrollment")
	program_enrollment.student = student[0]
	program_enrollment.student_name = student[1]
	program_enrollment.program = programs[0]['name']
	program_enrollment.academic_year = frappe.db.get_single_value("Education Settings","current_academic_year")
	program_enrollment.academic_term = frappe.db.get_single_value("Education Settings","current_academic_term")
	program_enrollment.educational_year= years[0]['name']
	program_enrollment.save(ignore_permissions=True)
	program_enrollment.submit()
	frappe.db.commit()
	return True

@frappe.whitelist()
def enroll_student_in_program(program):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name", 'student_name', 'is_coursepack_student'])
	if not student: return {"is_success": 0, "error": _('You are not student')}
	if frappe.db.get_value("Program Enrollment", {"student": student[0], "program": program}, ['name']):
		return {"is_success": 0, "error": _('You are enrolled in this program before')}
	years = frappe.db.get_all("Educational Year", fields = ["name"], order_by="year_order asc", page_length=1)
	is_coursepack = frappe.db.get_value("Program", program, ['is_coursepack'])
	if student[2] and not is_coursepack:
		return {"is_success": 0, "error": _('You are not allowed to enroll for this program')}
	if not years : return {"is_success": 0, "error": _('Unable to find educational year')}
	
	program_enrollment = frappe.new_doc("Program Enrollment")
	program_enrollment.student = student[0]
	program_enrollment.student_name = student[1]
	program_enrollment.program = program
	program_enrollment.academic_year = frappe.db.get_single_value("Education Settings","current_academic_year")
	program_enrollment.academic_term = frappe.db.get_single_value("Education Settings","current_academic_term")
	program_enrollment.educational_year= years[0]['name']
	program_enrollment.save(ignore_permissions=True)
	program_enrollment.submit()
	results = {"is_success": 1, "msg": _('You have successfully registered for the program')}
	if is_coursepack:
		res = create_coursepack_enrollment_applicant(program_enrollment)
		if res.get('is_success'): results = res

	frappe.db.commit()
	return results

def create_coursepack_enrollment_applicant(program_enrollment):
	enrollment = frappe.db.exists("Course Enrollment Applicant", {"application_status": ["!=", "Rejected"], "student": program_enrollment.student, "program": program_enrollment.program})
	if enrollment: return {"is_success": 0}
	# fetch program courses
	courses = frappe.db.get_all("Program Course", {"parent": program_enrollment.program}, ['course'])
	courses_list = ["'" + course['course'] + "'" for course in courses]
	courses_list = ",".join(courses_list)
	# fetch student group for every course and student gender
	student_gender = frappe.db.get_value("Student", program_enrollment.student, ['gender'])
	where_stmt = ""
	if student_gender:
		where_stmt = f"AND (grp.group_gender='{student_gender}' or grp.group_gender is NULL)"
	
	student_groups = frappe.db.sql("""
		SELECT grp.name, grp.course FROM `tabStudent Group` as grp
		WHERE grp.course in ({courses}) AND grp.program=%(program)s AND grp.academic_term=%(academic_term)s {where_stmt}
	""".format(courses=courses_list, where_stmt=where_stmt), 
	{"academic_term": program_enrollment.academic_term, "program": program_enrollment.program},as_dict=True)
	student_groups = {group['course']: group['name'] for group in student_groups}
	# create course enrollment applicant for every course in program
	filters = {
				"doctype": "Course Enrollment Applicant",
				"application_date": frappe.utils.nowdate(),
				"student": program_enrollment.student,
				"program": program_enrollment.program,
				"academic_term": program_enrollment.academic_term,
				"academic_year": program_enrollment.academic_year
			}
	enrollment_applicant = frappe.get_doc(filters)
	for course in courses:
		course_row = enrollment_applicant.append("courses")
		course_row.course = course['course']
		if student_groups.get(course['course']):
			course_row.group = student_groups.get(course['course'])
	
	
	enrollment_applicant.save(ignore_permissions=True)
	pay_msg = get_pay_fees_msg(program_enrollment.student)
	return {"is_success": 1,"msg": _("Courses registered successfully.") + " " + pay_msg, "pay": 1 if pay_msg else 0}

def get_pay_fees_msg(student):
	fees_msg = ""
	res = frappe.db.sql("""
		select sum(outstanding_amount) as amount FROM `tabFees` WHERE student=%(student)s AND outstanding_amount > 0
	""", {"student": student}, as_dict=True)
	if res and res[0].get('amount') and  res[0].get('amount') > 0:
		fees_msg = _("Please pay courses fees {0}here{1}.").format("<a href='/fees'>", "</a>")
	return fees_msg


def set_doctype_permissions(doctype_name, role_name, perm_level=0, read=1, write=1, create=1, delete=0, submit=0, cancel=0, amend=0, printt=1, email=1, export=1, share=1):
	"""
	Sets or updates permissions for a specific DocType and Role.
	"""
	try:
	# Check if a DocPerm already exists for this DocType and Role
		docperm = frappe.get_list("Custom DocPerm", filters={
	"parent": doctype_name,
	"role": role_name,
	"permlevel": perm_level
	}, limit=1)

		if docperm:
			# Update existing DocPerm
			docperm_doc = frappe.get_doc("Custom DocPerm", docperm[0].name)
			print("exitss-----")
			frappe.msgprint(f"Updating existing DocPerm for {doctype_name} with role {role_name} and permlevel {perm_level}")
		else:
			# Create new DocPerm
			docperm_doc = frappe.new_doc("Custom DocPerm")
			docperm_doc.parent = doctype_name
			docperm_doc.parentfield = "permissions"
			docperm_doc.parenttype = "DocType"
			docperm_doc.role = role_name
			docperm_doc.permlevel = perm_level
			frappe.msgprint(f"Creating new DocPerm for {doctype_name} with role {role_name} and permlevel {perm_level}")

			docperm_doc.read = read
			# docperm_doc.write = write
			# docperm_doc.create = create
			# docperm_doc.delete = delete
			# docperm_doc.submit = submit
			# docperm_doc.cancel = cancel
			# docperm_doc.amend = amend
			# docperm_doc.print = printt
			# docperm_doc.email = email
			# docperm_doc.export = export
			# docperm_doc.share = share
			docperm_doc.save(ignore_permissions=True) # ignore_permissions is crucial for programmatic changes
			frappe.db.commit()
			frappe.msgprint(f"Permissions updated successfully for {doctype_name} and {role_name}.")

	except Exception as e:
		print("Errror")
		print(e)
		frappe.log_error(frappe.get_traceback(), "Error setting DocType permissions")
		frappe.msgprint(f"Error setting permissions: {e}")
