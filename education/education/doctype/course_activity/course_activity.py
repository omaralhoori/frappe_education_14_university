# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class CourseActivity(Document):
	def validate(self):
		self.check_if_enrolled()

	def check_if_enrolled(self):
		if frappe.db.exists("Course Enrollment", self.enrollment):
			return True
		else:
			frappe.throw(_("Course Enrollment {0} does not exists").format(self.enrollment))


def create_course_enrollment_activity(course, lesson_type, lesson):
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	if not student: return
	course_enrollment = frappe.db.get_value("Course Enrollment", {"student": student, "course": course, "enrollment_status": ["in", ["Enrolled", "Partially Pulled"]]})
	if not course_enrollment:
		frappe.msgprint(_("You are not enrolled in this course"))
		return False
	if not frappe.db.exists("Course Activity", {"enrollment": course_enrollment, "content_type": lesson_type, "content": lesson}):
		frappe.get_doc({
			"doctype": "Course Activity",
			"enrollment": course_enrollment,
			"content_type": lesson_type,
			"content": lesson,
			"activity_date": frappe.utils.now(),
		}).save(ignore_permissions=True)
	progress = get_course_progress(course_enrollment, course)
	frappe.db.set_value("Course Enrollment", course_enrollment, {"current_lesson_type": lesson_type, "current_lesson": lesson, "progress": progress})
	frappe.db.commit()
	return True
	
def get_course_progress(course_enrollment, course):
	progress = frappe.db.sql("""
		select tbl1.lessons, tbl2.activities FROM
			(select count(tpcCntn.name) as lessons FROM `tabTopic Content` as tpcCntn
					INNER JOIN `tabTopic` as tpc ON tpc.name=tpcCntn.parent
					INNER JOIN `tabCourse Topic` as crsTpc ON crsTpc.topic=tpc.name
					WHERE crsTpc.parent=%(course)s
			) as tbl1,
			(select count(actv.name) as activities FROM `tabCourse Activity` as actv
					WHERE actv.enrollment=%(enrollment)s
			) as tbl2
	""", {"course": course, "enrollment": course_enrollment}, as_dict=True)

	if len(progress) == 0:
		return 0
	return progress[0]['activities'] / progress[0]['lessons'] * 100

	

