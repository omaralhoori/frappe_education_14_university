# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from functools import reduce

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class CourseEnrollment(Document):
	def validate(self):
		self.validate_duplication()

	def get_progress(self, student):
		"""
		Returns Progress of given student for a particular course enrollment

		        :param self: Course Enrollment Object
		        :param student: Student Object
		"""
		course = frappe.get_doc("Course", self.course)
		topics = course.get_topics()
		progress = []
		for topic in topics:
			progress.append(student.get_topic_progress(self.name, topic))
		if progress:
			return reduce(lambda x, y: x + y, progress)  # Flatten out the List
		else:
			return []

	def validate_duplication(self):
		enrollment = frappe.db.exists(
			"Course Enrollment",
			{
				"student": self.student,
				"course": self.course,
				"program_enrollment": self.program_enrollment,
				"academic_term": self.academic_term,
				"name": ("!=", self.name),
			},
		)
		if enrollment:
			frappe.throw(
				_("Student is already enrolled via Course Enrollment {0}").format(
					get_link_to_form("Course Enrollment", enrollment)
				),
				title=_("Duplicate Entry"),
			)

	def add_quiz_activity(
		self, quiz_name, quiz_response, answers, score, status, time_taken
	):
		result = {k: ("Correct" if v else "Wrong") for k, v in answers.items()}
		result_data = []
		for key in answers:
			item = {}
			item["question"] = key
			item["quiz_result"] = result[key]
			try:
				if not quiz_response[key]:
					item["selected_option"] = "Unattempted"
				elif isinstance(quiz_response[key], list):
					item["selected_option"] = ", ".join(
						frappe.get_value("Options", res, "option") for res in quiz_response[key]
					)
				else:
					item["selected_option"] = frappe.get_value("Options", quiz_response[key], "option")
			except KeyError:
				item["selected_option"] = "Unattempted"
			result_data.append(item)

		quiz_activity = frappe.get_doc(
			{
				"doctype": "Quiz Activity",
				"enrollment": self.name,
				"quiz": quiz_name,
				"activity_date": frappe.utils.datetime.datetime.now(),
				"result": result_data,
				"score": score,
				"status": status,
				"time_taken": time_taken,
			}
		).insert(ignore_permissions=True)

	def add_activity(self, content_type, content):
		activity = check_activity_exists(self.name, content_type, content)
		if activity:
			return activity
		else:
			activity = frappe.get_doc(
				{
					"doctype": "Course Activity",
					"enrollment": self.name,
					"content_type": content_type,
					"content": content,
					"activity_date": frappe.utils.datetime.datetime.now(),
				}
			)

			activity.insert(ignore_permissions=True)
			return activity.name
	
	@frappe.whitelist()
	def pull_enrollment(self):
		allowed_weeks = frappe.db.get_single_value("Education Settings", "pulling_allowed_weeks")
		academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
		start_date = frappe.db.get_value("Academic Term", academic_term, "term_start_date")
		allowed_date = frappe.utils.add_to_date(start_date, weeks=allowed_weeks)
		if frappe.utils.getdate() <= frappe.utils.getdate(allowed_date):
			self.db_set("enrollment_status", "Pulled")
		else:
			self.db_set("enrollment_status", "Partially Pulled")
			self.db_set("partially_pulled", 1)

def check_activity_exists(enrollment, content_type, content):
	activity = frappe.get_all(
		"Course Activity",
		filters={"enrollment": enrollment, "content_type": content_type, "content": content},
	)
	if activity:
		return activity[0].name
	else:
		return None


@frappe.whitelist()
def create_enrollment(
	course
):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name"])
	if not student: return {
		"error": _("You are not student")
	}
	program_enrollment = frappe.db.get_value("Program Enrollment", {"student": student}, ["name"])
	if not program_enrollment:
		return {
			"error": _("You did not enroll in any program")
		}
	filters = {
		"student": student,
		"program_enrollment": program_enrollment,
		"course": course,
		"academic_year": frappe.db.get_single_value("Education Settings", "current_academic_year"),
		"academic_term": frappe.db.get_single_value("Education Settings", "current_academic_term"),
	}
	if frappe.db.exists("Course Enrollment", filters):
		return {
			"error": _("You enrolled in this course before")
		}
	filters = {
		"enrollment_status": "Enrolled",
		"doctype" :"Course Enrollment",
		"enrollment_date": frappe.utils.nowdate(),
		**filters
	}
	enrollment = frappe.get_doc(
		filters
	)
	enrollment.save(ignore_permissions=True)
	progress = get_enrollment_progress(enrollment)
	if len(progress) > 0:
		enrollment.current_lesson_type = progress[0]['content_type']
		enrollment.current_lesson = progress[0]['content']
		enrollment.save(ignore_permissions=True)
	return {
		"success": 1,
		"current_lesson": enrollment.current_lesson,
		"current_lesson_type": enrollment.current_lesson_type,
	}

def get_enrollment_progress(enrollment):
	progress = frappe.db.sql("""
		select cntn.content_type, cntn.content FROM `tabTopic Content` as cntn
		INNER JOIN `tabTopic` as tpc ON tpc.name=cntn.parent
		INNER JOIN `tabCourse Topic` as crsTpc ON crsTpc.topic = tpc.name
		WHERE crsTpc.parent=%(course)s
		ORDER BY crsTpc.idx, cntn.idx
		LIMIT 1
	""", {"course": enrollment.course}, as_dict=True)
	return progress