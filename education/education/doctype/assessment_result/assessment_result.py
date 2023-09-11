# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.csvutils import getlink

import education.education
from education.education.api import get_assessment_details, get_grade


class AssessmentResult(Document):
	def validate(self):
		education.education.validate_student_belongs_to_group(
			self.student, self.student_group
		)
		self.validate_maximum_score()
		self.validate_grade()
		self.validate_duplicate()
	def on_update_after_submit(self):
		self.validate_grade()
		self.update_course_enrollment_grade()
	def on_submit(self):
		self.update_course_enrollment_grade()

	def update_course_enrollment_grade(self):
		if enrollment := frappe.db.exists("Course Enrollment", {"course": self.course, "student": self.student,"program": self.program, "academic_term": self.academic_term}):
			course_enrollment = frappe.get_doc("Course Enrollment", enrollment)
			if not course_enrollment.graduation_grade or course_enrollment.graduation_grade != self.total_score:
				course_enrollment.graduation_grade = self.total_score
				if not course_enrollment.graduation_date:
					course_enrollment.graduation_date = frappe.utils.datetime.date.today()
				if self.total_score >= frappe.db.get_single_value("Education Settings", "course_graduation_threshold"):
					course_enrollment.enrollment_status = "Graduated"
				else:
					course_enrollment.enrollment_status = "Failed"
				course_enrollment.save(ignore_permissions=True)

	def validate_maximum_score(self):
		assessment_details = get_assessment_details(self.assessment_plan)
		max_scores = {}
		for d in assessment_details:
			max_scores.update({d.assessment_criteria: d.maximum_score})

		for d in self.details:
			d.maximum_score = max_scores.get(d.assessment_criteria)
			if d.score > d.maximum_score:
				d.score = d.maximum_score
				#frappe.throw(_("Score cannot be greater than Maximum Score"))

	def validate_grade(self):
		self.total_score = 0.0
		for d in self.details:
			d.grade = get_grade(self.grading_scale, (flt(d.score) / d.maximum_score) * 100)
			self.total_score += d.score
		self.grade = get_grade(
			self.grading_scale, (self.total_score / self.maximum_score) * 100
		)
		self.db_set("total_score", self.total_score)
		#frappe.db.commit()

	def validate_duplicate(self):
		return True
		assessment_result = frappe.get_list(
			"Assessment Result",
			filters={
				"name": ("not in", [self.name]),
				"student": self.student,
				"assessment_plan": self.assessment_plan,
				"docstatus": ("!=", 2),
			},
		)
		if assessment_result:
			frappe.throw(
				_("Assessment Result record {0} already exists.").format(
					getlink("Assessment Result", assessment_result[0].name)
				)
			)
