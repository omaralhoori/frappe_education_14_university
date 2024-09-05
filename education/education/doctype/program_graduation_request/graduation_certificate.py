from reportlab.pdfgen import canvas # pip install reportlab
from reportlab.lib.pagesizes import C9
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from PyPDF2 import PdfReader, PdfWriter

import arabic_reshaper # pip install arabic-reshaper
from bidi.algorithm import get_display # pip install python-bidi
import unittest
import frappe
from frappe.tests.test_commands import BaseTestCommands
import io
from frappe.utils import get_site_name
# Create a canvas to draw on the PDF
from frappe.utils import cstr
class TestCommands(BaseTestCommands, unittest.TestCase):
    def test_execute(self):
        test_create_certificate()

# bench --site alrewaq.erp  execute education.certificate.test_create_certificate
def test_create_certificate():
    template_path = 'program_certificate_template.pdf'  # Change this to the path of your template PDF
    output_path = 'test_certificate/output_certificate.pdf'  # Change this to the desired output path

    # Define text to be added (example with Arabic name)
    student_name = "عمر أحمد ياسين الحوري"
    date = "2024-07-09"
    period1 = "2024-07-09"
    period2 = "2024-07-09"
    rate = "ممتاز"
    grade = "%95.88"

    # Define text positions (these need to be adjusted based on your template)
    name_position = (350, 280)
    date_position = (275, 50)
    period1_position = (225, 123)
    period2_position = (100, 123)
    grade_position = (528, 123)
    rate_position = (400, 123)

    create_pdf_certificate(
        template_path=template_path, output_path=output_path, 
        configs=frappe._dict({
            "name_position": name_position,
            "date_position": date_position,
            "grade_position": grade_position,
            "rate_position": rate_position,
            "period2_position": period2_position,
            "period1_position": period1_position,
        }),
        data= frappe._dict({
            "student_name": student_name,
            "date": date,
            "grade": grade,
            "rate": rate,
            "period1": period1,
            "period2": period2,
        })
        )
    
def create_program_certificate(program_enrollment, certificate_date):
    enrollment_data = frappe.db.get_value("Program Enrollment", program_enrollment, ["student", "academic_term", "cgpa"], as_dict=True)
    student_name_arabic = frappe.db.get_value("Student", enrollment_data['student'], ["first_name_arabic", "middle_name_arabic", "last_name_arabic", "student_name"], as_dict=True)
    if not student_name_arabic.first_name_arabic:
        student_name = student_name_arabic.student_name
    else:
        student_name = student_name_arabic.first_name_arabic + " " + student_name_arabic.middle_name_arabic +" " + student_name_arabic.last_name_arabic
    term_start = frappe.db.get_value("Academic Term", enrollment_data.academic_term, "term_start_date")
    term_end = frappe.db.sql("""
        SELECT tbl2.term_end_date 
            FROM `tabCourse Enrollment` as tbl1
        INNER JOIN `tabAcademic Term` as tbl2 ON tbl1.academic_term=tbl2.name
        WHERE tbl1.program_enrollment=%(program_enrollment)s
        ORDER BY tbl2.term_end_date desc
        LIMIT 1
""", {"program_enrollment": program_enrollment},as_dict=True)[0]['term_end_date']
    name_position = (350, 280)
    date_position = (275, 50)
    period1_position = (225, 123)
    period2_position = (100, 123)
    grade_position = (528, 123)
    rate_position = (400, 123)
    site_name = cstr(frappe.local.site)
    output = site_name + '/public/files/certificates/' + program_enrollment + ".pdf"
    file_name = "/files/certificates/" + program_enrollment + ".pdf"
    create_pdf_certificate(
        template_path='program_certificate_template.pdf', output_path=output, 
        configs=frappe._dict({
            "name_position": name_position,
            "date_position": date_position,
            "grade_position": grade_position,
            "rate_position": rate_position,
            "period2_position": period2_position,
            "period1_position": period1_position,
        }),
        data= frappe._dict({
            "student_name": student_name,
            "date": str(certificate_date),
            "grade":"%" +'%.2f' % enrollment_data.cgpa,
            "rate": get_rate(enrollment_data.cgpa),
            "period1": str(term_start),
            "period2": str(term_end),
        })
        )
    return file_name
    
def get_rate(cgpa):
    if cgpa >= 90:
        return 'ممتاز'
    elif cgpa >= 80:
        return 'جيد جدا'
    elif cgpa >= 70: 
        return 'جيد'
    elif cgpa >= 60:
        return 'مقبول'
    else:
        return 'ضعيف'
def create_pdf_certificate(template_path, output_path, configs, data):
    name_config = {
        "font": "andalus",
        "size": 40,
        "color": "#c3923e"
    }
    date_config = {
        "font": "AlHurraTxtreg",
        "size": 20,
        "color": "#2b2b2b"
    }
    grade_config = {
        "font": "decotypenaskh",
        "size": 25,
        "color": "#2b2b2b"
    }
    reader = PdfReader(template_path)
    writer = PdfWriter()
    template_page = reader.pages[0]
    writer.add_page(template_page)
    template_width = template_page.mediabox.width
    template_height = template_page.mediabox.height
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(template_width,  template_height), lang="ar")
    print(template_width, template_height)
    # Register and set the font (ensure this font supports Arabic characters)
    font_path = f"assets/education/fonts/{name_config['font']}.ttf"  # Change this to the path of your .ttf font file that supports Arabic
    pdfmetrics.registerFont(TTFont(name_config['font'], font_path))
    font_path = f"assets/education/fonts/{date_config['font']}.ttf"  # Change this to the path of your .ttf font file that supports Arabic
    pdfmetrics.registerFont(TTFont(date_config['font'], font_path))
    font_path = f"assets/education/fonts/{grade_config['font']}.ttf"  # Change this to the path of your .ttf font file that supports Arabic
    pdfmetrics.registerFont(TTFont(grade_config['font'], font_path))

    # Draw Name
    c.setFont(name_config['font'], name_config["size"])

    # Draw text on the canvas
    # c.drawString(configs.get("name_position")[0], configs.get("name_position")[1], f"{data.student_name}")
    # c.drawString(configs.date_position[0], configs.date_position[1], f"Date: {data.date}")
    # c.drawString(configs.grade_position[0], configs.grade_position[1], f"Grade: {data.grade}")
    reshaped_text = arabic_reshaper.reshape(data.student_name)
    bidi_text = get_display(reshaped_text)
    text_width = pdfmetrics.stringWidth(bidi_text, name_config['font'], name_config['size'])

    x_position = (float(template_width) - float(text_width)) / 2  
    draw_arabic_text(c, data.student_name, (x_position,configs.get("name_position")[1]), name_config["color"])
    c.setFont(date_config['font'], date_config['size'])
    draw_arabic_text(c, data.date, configs.date_position, date_config['color'])
    draw_arabic_text(c, data.period1, configs.period1_position, date_config['color'])
    draw_arabic_text(c, data.period2, configs.period2_position, date_config['color'])
    draw_arabic_text(c, data.grade, configs.grade_position, date_config['color'])
    c.setFont(grade_config['font'], grade_config['size'])
    
    draw_arabic_text(c, data.rate, configs.rate_position, date_config["color"])

    # Save the canvas to the output file
    c.save()

    # with open(output_path, "wb") as f:
    #     writer.write(f)
    packet.seek(0)

    # Create a new PDF with the text overlay
    overlay_pdf = PdfReader(packet)
    overlay_page = overlay_pdf.pages[0]

    # Merge the overlay PDF with the template PDF
    writer = PdfWriter()

    # Add the template page
    template_page.merge_page(overlay_page)
    writer.add_page(template_page)

    # Save the final output to a file
    with open(output_path, "wb") as output_file:
        writer.write(output_file)


    print(f"Certificate saved as {output_path}")


def draw_arabic_text(canvas, text, position, color):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    canvas.setFillColor(color)
    canvas.drawString(position[0], position[1], bidi_text)