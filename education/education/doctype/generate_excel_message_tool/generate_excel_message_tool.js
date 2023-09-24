// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Generate Excel Message Tool", {
	refresh(frm) {
        
	},
    generate_messages(frm){
        frappe.call({
            "method": "education.education.doctype.generate_excel_message_tool.generate_excel_message_tool.generate_messages",
            "args": {
                "excel_file": frm.doc.excel_file,
                "used_column_names": frm.doc.used_column_names,
                "message_field_names": frm.doc.message_field_names,
                "message": frm.doc.message
            },
            callback: (res)=> {
                frm.events.render_excel_table(frm, res)
            }
        })
    },
    render_excel_table(frm, res){
        if (res && res.message){
            var header = frm.events.render_excel_table_header(frm, res.message[0])
            var body = frm.events.render_excel_table_body(frm, res.message)
            var table = `<table class="table table-striped">
                ${header}
                ${body}
            </table>`;
            $(frm.fields_dict['excel_container'].wrapper)
				.html(
                    table
                )
        }
    },
    render_excel_table_header(frm, first_row){
        var columns= '';
        for (var column in first_row){
            columns += `<th>${column}</th>`
        }
        var html = `
            <thead> 
            <tr>
                ${columns}
            </tr>
            </thead>
        `;
        return html;
    },
    render_excel_table_body(frm, data){
        var html = ``
        for (var row of data){
            var columns = ''
            for (var column in row){
                if (column == 'message'){
                    columns += `<td><a target="_blank" class="btn btn-primary" href="${row[column]}">Send Message</a></td>`
    
                }else{
                    columns += `<td>${row[column]}</td>`
                }
            }
            html += ` <tr>
                ${columns}
            </tr>
            `
        }

        return `<tbody>${html}</tbody>`
    }

});
