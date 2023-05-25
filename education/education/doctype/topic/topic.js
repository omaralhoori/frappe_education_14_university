// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Topic', {
	refresh: function(frm) {
		if (!cur_frm.doc.__islocal) {
			frm.add_custom_button(__('Add Contents'), function() {
				frm.trigger('add_contents');
			}, __('Action'));
			frm.add_custom_button(__('Add to Courses'), function() {
				frm.trigger('add_topic_to_courses');
			}, __('Action'));
		}
	},
	add_contents: function(frm){
		frappe.prompt([
			{
				fieldname: 'title',
				label: __('Title'),
				fieldtype: 'Data',
			},
			{
				fieldname: 'author',
				label: __('Author'),
				fieldtype: 'Data',
			},
			{
				fieldname: 'pages',
				label: __('pages'),
				fieldtype: 'Int',
			},
			{
				fieldname: 'parts',
				label: __('Parts'),
				fieldtype: 'Int',
			},
			{
				fieldname: 'content',
				label: __('Content'),
				fieldtype: 'Text Editor',
			},
		], function(data) {
			frappe.call({
				method: 'education.education.doctype.topic.topic.add_multicontents',
				args: {
					topic: frm.doc.name,
					title: data.title,
					author: data.author,
					pages: data.pages,
					parts: data.parts,
					content: data.content
				},
				freeze: true,
				freeze_message: __('...Adding Contents to Topic'),
				callback: (res) => {
					if (res.message){

						frm.reload_doc()
					}
				}
			})
		})
	},
	add_topic_to_courses: function(frm) {
		get_courses_without_topic(frm.doc.name).then(r => {
			if (r.message.length) {
				frappe.prompt([
					{
						fieldname: 'courses',
						label: __('Courses'),
						fieldtype: 'MultiSelectPills',
						get_data: function() {
							return r.message;
						}
					}
				],
				function(data) {
					frappe.call({
						method: 'education.education.doctype.topic.topic.add_topic_to_courses',
						args: {
							'topic': frm.doc.name,
							'courses': data.courses
						},
						callback: function(r) {
							if (!r.exc) {
								frm.reload_doc();
							}
						},
						freeze: true,
						freeze_message: __('...Adding Topic to Courses')
					});
				}, __('Add Topic to Courses'), __('Add'));
			} else {
				frappe.msgprint(__('This topic is already added to the existing courses'));
			}
		});
	}
});

let get_courses_without_topic = function(topic) {
	return frappe.call({
		type: 'GET',
		method: 'education.education.doctype.topic.topic.get_courses_without_topic',
		args: {'topic': topic}
	});
};
