import pytest
import io
import json
from pypdf import PdfReader

import src.projects.reports as reports

@pytest.fixture
def sample_results():
    with open("tests/sample_results.json", "r") as f:
        return f.read()

def test_generate_report(sample_results):
    buffer = io.BytesIO()
    
    reports.generate_report(
        project_id="test_project",
        project_name="Test Project",
        project_description="Test Description",
        num_rounds=10,
        project_type="classification",
        data=sample_results,
        path=buffer
    )

    pdf_out = buffer.getvalue()
    assert pdf_out is not None
    assert len(pdf_out) > 0
    assert pdf_out.startswith(b"%PDF-")

def test_classification_report_content(sample_results):
    buffer = io.BytesIO()

    
    reports.generate_report(
        project_id="test_project",
        project_name="Test Project",
        project_description="Test Description",
        num_rounds=10,
        project_type="classification",
        data=sample_results,
        path=buffer
    )

    pdf_out = buffer.getvalue()
    reader = PdfReader(io.BytesIO(pdf_out))
    
    assert len(reader.pages) >= 1
    page = reader.pages[0]
    text = page.extract_text()
    
    assert text is not None
    assert "Test Project" in text
    assert "Test Description" in text
    assert "10" in text
    assert "classification" in text
    res = json.loads(sample_results)
    assert str(res[0]["config"]["strategy"]) in text
    assert str(res[0]["config"]["epochs"]) in text
    assert str(res[0]["config"]["batch_size"]) in text
    assert str(res[0]["config"]["learning_rate"]) in text
    assert str(res[0]["config"]["optimizer"]) in text
    assert str(res[0]["config"]["loss"]) in text
    assert str(res[0]["config"]["classes"]) in text

def test_invalid_report_type(sample_results):
    buffer = io.BytesIO()
    
    with pytest.raises(ValueError, match="Invalid report type"):
        reports.generate_report(
            project_id="test_project",
            project_name="Test Project",
            project_description="Test Description",
            num_rounds=10,
            project_type="invalid",
            data=sample_results,
            path=buffer
        )
