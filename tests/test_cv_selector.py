import fitz

from src.cv_selector import extract_cv_text, validate_cv_upload


class Upload:
    name = "candidate.pdf"

    def __init__(self, value):
        self.value = value

    def getvalue(self):
        return self.value


def test_extract_cv_text(tmp_path):
    path = tmp_path / "candidate.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Data Engineer Python")
    document.save(path)
    document.close()
    assert "Data Engineer" in extract_cv_text(path)


def test_validate_cv_upload_rejects_non_pdf():
    upload = Upload(b"not a pdf")
    upload.name = "candidate.txt"
    valid, message = validate_cv_upload(upload)
    assert not valid
    assert "PDF" in message