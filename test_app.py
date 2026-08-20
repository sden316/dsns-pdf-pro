import io

from PIL import Image
from pypdf import PdfReader, PdfWriter

from app import app, safe_output_name


def make_pdf(widths):
    output = io.BytesIO()
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=200)
    writer.write(output)
    writer.close()
    return output.getvalue()


def make_image(size=(320, 240), mode="RGB", color="orange", image_format="PNG"):
    output = io.BytesIO()
    Image.new(mode, size, color).save(output, format=image_format)
    return output.getvalue()


def test_index_and_health():
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json == {"status": "ok"}


def test_merge_preserves_file_and_page_order():
    client = app.test_client()
    response = client.post(
        "/api/merge",
        data={
            "files": [
                (io.BytesIO(make_pdf([101, 102])), "first.pdf"),
                (io.BytesIO(make_pdf([201])), "second.pdf"),
            ],
            "output_name": "combined.pdf",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    reader = PdfReader(io.BytesIO(response.data))
    assert [float(page.mediabox.width) for page in reader.pages] == [101, 102, 201]


def test_merge_requires_two_files():
    client = app.test_client()
    response = client.post(
        "/api/merge",
        data={"files": [(io.BytesIO(make_pdf([100])), "one.pdf")]},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.json["error"] == "Select at least two files."


def test_invalid_pdf_returns_readable_error():
    client = app.test_client()
    response = client.post(
        "/api/merge",
        data={
            "files": [
                (io.BytesIO(b"not a pdf"), "bad.pdf"),
                (io.BytesIO(make_pdf([100])), "good.pdf"),
            ]
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.json["error"]


def test_mixed_merge_preserves_pdf_and_image_order():
    client = app.test_client()
    response = client.post(
        "/api/merge",
        data={
            "files": [
                (io.BytesIO(make_pdf([101])), "first.pdf"),
                (io.BytesIO(make_image(size=(200, 100))), "image.png"),
                (io.BytesIO(make_pdf([301])), "last.pdf"),
            ],
            "page_size": "a4",
            "orientation": "portrait",
            "margin_mm": "8",
            "fit": "contain",
            "background": "white",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    reader = PdfReader(io.BytesIO(response.data))
    widths = [round(float(page.mediabox.width)) for page in reader.pages]
    assert widths == [101, 595, 301]


def test_images_to_pdf_supports_transparency_and_landscape_letter():
    client = app.test_client()
    response = client.post(
        "/api/images-to-pdf",
        data={
            "files": [
                (io.BytesIO(make_image(mode="RGBA", color=(255, 0, 0, 100))), "alpha.png"),
                (io.BytesIO(make_image(image_format="JPEG")), "photo.jpg"),
            ],
            "page_size": "letter",
            "orientation": "landscape",
            "margin_mm": "10",
            "fit": "contain",
            "background": "black",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    reader = PdfReader(io.BytesIO(response.data))
    assert len(reader.pages) == 2
    assert [(round(float(page.mediabox.width)), round(float(page.mediabox.height))) for page in reader.pages] == [
        (792, 612),
        (792, 612),
    ]


def test_output_name_is_sanitized():
    assert safe_output_name("../quarter:final") == "quarter_final.pdf"