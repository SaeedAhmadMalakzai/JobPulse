"""Cover-letter generation: no placeholder gaps, role/company tailoring, signature."""
from src.sites.base import JobListing
from src import cover_letter as cl


def _job(**kw):
    base = dict(id="acbar_1", title="Project Manager", company="ACBAR Member", url="http://x")
    base.update(kw)
    return JobListing(**base)


def _no_placeholders(text: str):
    assert "{{" not in text and "}}" not in text
    low = text.lower()
    assert "your university" not in low
    assert "my previous organization" not in low


def test_empty_bio_fields_leave_no_filler(monkeypatch):
    monkeypatch.setattr(cl, "COVER_LETTER_UNIVERSITY", "")
    monkeypatch.setattr(cl, "COVER_LETTER_PREVIOUS_ORGANIZATION", "")
    monkeypatch.setattr(cl, "FULL_NAME", "Test Applicant")
    monkeypatch.setattr(cl, "SUBMISSION_EMAIL", "me@hiringorg.test")
    text = cl.generate_cover_letter(_job())
    _no_placeholders(text)
    # tailored: names the role
    assert "Project Manager" in text
    # generic ACBAR company is addressed neutrally, not "at ACBAR Member"
    assert "ACBAR Member" not in text
    # signature present
    assert "Test Applicant" in text


def test_bio_fields_are_used_when_present(monkeypatch):
    # UN template carries both {{UNIVERSITY}} and {{PREVIOUS_ORGANIZATION}}.
    monkeypatch.setattr(cl, "COVER_LETTER_UNIVERSITY", "Kabul University")
    monkeypatch.setattr(cl, "COVER_LETTER_PREVIOUS_ORGANIZATION", "Acme NGO")
    monkeypatch.setattr(cl, "FULL_NAME", "Test Applicant")
    monkeypatch.setattr(cl, "SUBMISSION_EMAIL", "me@hiringorg.test")
    text = cl.generate_cover_letter(_job(id="unjobs_1", title="Programme Officer", company="UNDP"))
    assert "Kabul University" in text
    assert "Acme NGO" in text
    _no_placeholders(text)


def test_previous_org_used_in_custom_letter(monkeypatch):
    monkeypatch.setattr(cl, "COVER_LETTER_PREVIOUS_ORGANIZATION", "Acme NGO")
    monkeypatch.setattr(cl, "FULL_NAME", "Test Applicant")
    monkeypatch.setattr(cl, "SUBMISSION_EMAIL", "me@hiringorg.test")
    text = cl.generate_cover_letter(_job(id="other_1", title="Software Engineer", company="Acme"))
    assert "Acme NGO" in text
    _no_placeholders(text)


def test_un_template_for_un_jobs(monkeypatch):
    monkeypatch.setattr(cl, "COVER_LETTER_UNIVERSITY", "")
    monkeypatch.setattr(cl, "COVER_LETTER_PREVIOUS_ORGANIZATION", "")
    monkeypatch.setattr(cl, "FULL_NAME", "Test Applicant")
    monkeypatch.setattr(cl, "SUBMISSION_EMAIL", "")
    text = cl.generate_cover_letter(_job(id="unjobs_1", title="Programme Officer", company="UNDP"))
    _no_placeholders(text)
    assert "Sincerely" in text
