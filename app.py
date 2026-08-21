from __future__ import annotations

import io
import os
import re

from flask import Flask, jsonify, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("PDF_PRO_MAX_BYTES", 500 * 1024 * 1024)
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PAGE_SIZES = {"a4": A4, "letter": LETTER}


class InvalidInput(ValueError):
    pass


def safe_output_name(value: str | None) -> str:
    name = os.path.basename((value or "merged.pdf").strip())
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    return name or "merged.pdf"


def parse_image_options(form, *, image_only: bool) -> dict:
    default_page_size = "a4" if image_only else "image"
    default_margin = "8" if image_only else "0"
    page_size = form.get("page_size", default_page_size).lower()
    orientation = form.get("orientation", "auto").lower()
    fit = form.get("fit", "contain").lower()
    background = form.get("background", "white").lower()

    if page_size not in {"image", *PAGE_SIZES}:
        raise InvalidInput("Unsupported page size.")
    if orientation not in {"auto", "portrait", "landscape"}:
        raise InvalidInput("Unsupported page orientation.")
    if fit not in {"contain", "cover"}:
        raise InvalidInput("Unsupported image fit mode.")
    if background not in {"white", "black"}:
        raise InvalidInput("Unsupported image background.")
    try:
        margin_mm = float(form.get("margin_mm", default_margin))
    except ValueError as error:
        raise InvalidInput("Margin must be a number.") from error
    if not 0 <= margin_mm <= 50:
        raise InvalidInput("Margin must be between 0 and 50 mm.")

    return {
        "page_size": page_size,
        "orientation": orientation,
        "fit": fit,
        "background": background,
        "margin_points": margin_mm * 72 / 25.4,
    }


def image_page_size(image: Image.Image, options: dict) -> tuple[float, float]:
    margin = options["margin_points"]
    if options["page_size"] == "image":
        raw_dpi = image.info.get("dpi", (96, 96))
        try:
            horizontal_dpi = min(max(float(raw_dpi[0]), 36), 600)
            vertical_dpi = min(max(float(raw_dpi[1]), 36), 600)
        except (TypeError, ValueError, IndexError):
            horizontal_dpi = vertical_dpi = 96
        width = image.width * 72 / horizontal_dpi + 2 * margin
        height = image.height * 72 / vertical_dpi + 2 * margin
    else:
        width, height = PAGE_SIZES[options["page_size"]]

    orientation = options["orientation"]
    if orientation == "auto":
        orientation = "landscape" if image.width > image.height else "portrait"
    if orientation == "landscape" and width < height:
        width, height = height, width
    elif orientation == "portrait" and width > height:
        width, height = height, width
    return width, height


def image_to_pdf(stream, filename: str, options: dict) -> io.BytesIO:
    try:
        stream.seek(0)
        with Image.open(stream) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
            if getattr(image, "n_frames", 1) != 1:
                raise InvalidInput(f'"{filename}" contains multiple image frames.')
            background_value = 255 if options["background"] == "white" else 0
            if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new(
                    "RGBA", rgba.size, (background_value, background_value, background_value, 255)
                )
                background.alpha_composite(rgba)
                image = background.convert("RGB")
            else:
                image = image.convert("RGB")

            page_width, page_height = image_page_size(image, options)
            margin = options["margin_points"]
            usable_width = page_width - 2 * margin
            usable_height = page_height - 2 * margin
            if usable_width <= 0 or usable_height <= 0:
                raise InvalidInput("Margins leave no usable page area.")

            scale_x = usable_width / image.width
            scale_y = usable_height / image.height
            scale = min(scale_x, scale_y) if options["fit"] == "contain" else max(scale_x, scale_y)
            draw_width = image.width * scale
            draw_height = image.height * scale
            left = (page_width - draw_width) / 2
            bottom = (page_height - draw_height) / 2

            output = io.BytesIO()
            document = canvas.Canvas(output, pagesize=(page_width, page_height))
            document.setFillColorRGB(background_value / 255, background_value / 255, background_value / 255)
            document.rect(0, 0, page_width, page_height, stroke=0, fill=1)
            document.drawImage(
                ImageReader(image),
                left,
                bottom,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True,
                mask="auto",
            )
            document.showPage()
            document.save()
            output.seek(0)
            return output
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidInput(f'"{filename}" is not a readable JPG or PNG image.') from error


def append_pdf(writer: PdfWriter, stream, filename: str) -> None:
    stream.seek(0)
    reader = PdfReader(stream, strict=False)
    if reader.is_encrypted and reader.decrypt("") == 0:
        raise InvalidInput(f'"{filename}" is password protected.')
    if not reader.pages:
        raise InvalidInput(f'"{filename}" has no pages.')
    for page in reader.pages:
        writer.add_page(page)


def build_output(uploads, *, image_only: bool) -> io.BytesIO:
    minimum_files = 1 if image_only else 2
    if len(uploads) < minimum_files:
        message = "Select at least one image." if image_only else "Select at least two files."
        raise InvalidInput(message)

    options = parse_image_options(request.form, image_only=image_only)
    writer = PdfWriter()
    try:
        for upload in uploads:
            extension = os.path.splitext(upload.filename or "")[1].lower()
            if extension == ".pdf" and not image_only:
                append_pdf(writer, upload.stream, upload.filename)
            elif extension in IMAGE_EXTENSIONS:
                converted = image_to_pdf(upload.stream, upload.filename, options)
                append_pdf(writer, converted, upload.filename)
            else:
                expected = "JPG, JPEG, or PNG" if image_only else "PDF, JPG, JPEG, or PNG"
                raise InvalidInput(f'"{upload.filename}" is unsupported. Select {expected} files.')

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output
    finally:
        writer.close()


def build_blank_pdf() -> io.BytesIO:
    writer = PdfWriter()
    try:
        writer.add_blank_page(width=A4[0], height=A4[1])
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output
    finally:
        writer.close()


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/merge")
def merge_pdfs():
    uploads = [upload for upload in request.files.getlist("files") if upload.filename]
    try:
        output = build_output(uploads, image_only=False)
    except (InvalidInput, PdfReadError, ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 400
    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=safe_output_name(request.form.get("output_name")),
        max_age=0,
    )


@app.post("/api/images-to-pdf")
def images_to_pdf():
    uploads = [upload for upload in request.files.getlist("files") if upload.filename]
    try:
        output = build_output(uploads, image_only=True)
    except (InvalidInput, PdfReadError, ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 400
    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=safe_output_name(request.form.get("output_name") or "images.pdf"),
        max_age=0,
    )


@app.post("/api/blank-pdf")
def blank_pdf():
    return send_file(
        build_blank_pdf(),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=safe_output_name(request.form.get("output_name") or "blank.pdf"),
        max_age=0,
    )


@app.errorhandler(413)
def request_too_large(_error):
    limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return jsonify({"error": f"The selected files exceed the {limit_mb} MB limit."}), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    print(f"Starting DSNS PDF Pro on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)