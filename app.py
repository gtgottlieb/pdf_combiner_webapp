import os
import fitz
from flask import Flask, request, render_template, send_file, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_pdf_aspect_ratio(file_path):
    with fitz.open(file_path) as doc:
        rect = doc[0].rect
        return rect.width / rect.height

def embed_slides_on_template(input_files, output_path, template_path, positions, zoom_factor):
    slides_per_page = 4
    output_doc = fitz.open()
    template_doc = fitz.open(template_path)
    slide_count = 0

    for file in input_files:
        if file.lower().endswith('.pdf'):
            doc = fitz.open(file)
            for page_num in range(len(doc)):
                if slide_count % slides_per_page == 0:
                    output_page = output_doc.new_page(width=template_doc[0].rect.width,
                                                      height=template_doc[0].rect.height)
                    output_page.show_pdf_page(output_page.rect, template_doc, 0)

                pos = positions[slide_count % slides_per_page]
                slide = doc.load_page(page_num)
                center_x = (pos[0] + pos[2]) / 2
                center_y = (pos[1] + pos[3]) / 2
                width = (pos[2] - pos[0]) * zoom_factor
                height = (pos[3] - pos[1]) * zoom_factor

                zoomed_rect = fitz.Rect(center_x - width / 2, center_y - height / 2,
                                        center_x + width / 2, center_y + height / 2)
                output_page.show_pdf_page(zoomed_rect, doc, page_num)
                slide_count += 1

    output_doc.save(output_path)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        files = request.files.getlist('pdfs')
        zoom = float(request.form.get('zoom', '1.0'))
        output_name = secure_filename(request.form.get('output_name', 'output_notes.pdf'))

        input_paths = []
        for file in files:
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
            input_paths.append(path)

        if not input_paths:
            return "No PDF files uploaded", 400

        aspect_ratio = get_pdf_aspect_ratio(input_paths[0])
        template_path = 'template.pdf'

        # Position logic (metric in mm, converted to points if needed)
        x0_left = 17.15
        y0 = 18.075
        square_length = 13.85
        line_width = 0.55
        n_squares = 13
        add_y_pixels = n_squares * square_length + (n_squares - 1) * line_width
        y_coords = [y0 + i * (add_y_pixels + square_length + 2 * line_width) for i in range(4)]
        positions = [(x0_left, y, x0_left + aspect_ratio * add_y_pixels, y + add_y_pixels) for y in y_coords]

        output_path = os.path.join(OUTPUT_FOLDER, output_name)
        embed_slides_on_template(input_paths, output_path, template_path, positions, zoom)

        return redirect(url_for('download_file', filename=output_name))
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
