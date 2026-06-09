"""Regression tests for ACBAR submission-method extraction.

Synthetic HTML mirrors the real patterns observed on acbar.org/en/jobs/details/*
(emails/hosts genericized to example.* — fixtures must not embed real contacts):
- "Submission Email:" posts
- "Submission Guideline" posts pointing to a Google Form (incl. forms.gle short links)
- custom ATS/apply URLs (e.g. /apply, /public-position-view, ims.* hosts)
- the site-nav collision ("Job Centre · Application Form · Contact") that must NOT
  be mistaken for the real submission section.
"""
from src.sites.acbar import _extract_submission_email, _extract_submission_url

# Every real page starts with this nav/boilerplate (contains "Application Form").
NAV = "<div>RFP JOBS Job Centre Application Form CONTACT SEARCH ACBAR</div>"


def page(body: str) -> str:
    return f"<html><body>{NAV}<div class='post'>{body}</div>" \
           f"<footer>webinfo@acbar.org</footer></body></html>"


def test_submission_email_block():
    html = page("<p>Submission Email: hr@hiringorg.test</p>")
    assert _extract_submission_email(html) == "hr@hiringorg.test"


def test_google_form_short_link_via_guideline():
    html = page("<p>Submission Guideline: apply through the link below: "
                "https://forms.gle/abc123XYZ</p>")
    assert _extract_submission_email(html) is None
    assert _extract_submission_url(html) == "https://forms.gle/abc123XYZ"


def test_custom_ats_apply_url():
    html = page("<p>Submission Guideline: submit your application at "
                "https://ats.example.org/apply/infrastructure-engineer-174</p>")
    assert _extract_submission_url(html) == "https://ats.example.org/apply/infrastructure-engineer-174"


def test_custom_ims_form_not_confused_by_nav():
    # The nav contains "Application Form"; the real link is in the guideline lower down.
    html = page("<p>Submission Guideline: fill our applications form through the link "
                "below: https://ims.example.org/public-position-view/MTU5</p>")
    assert _extract_submission_url(html) == "https://ims.example.org/public-position-view/MTU5"


def test_email_lower_in_guideline_not_nav():
    html = page("<p>Submission Guideline: send your application (CV and cover letter) "
                "to hr@hiringorg.test before the deadline.</p>")
    assert _extract_submission_email(html) == "hr@hiringorg.test"


def test_acbar_and_webinfo_emails_excluded():
    html = page("<p>Submission Guideline: contact webinfo@acbar.org for site issues. "
                "Send your application to jobs@hiringorg.test</p>")
    assert _extract_submission_email(html) == "jobs@hiringorg.test"


def test_social_links_not_treated_as_application_url():
    html = page("<p>Submission Guideline: see https://www.facebook.com/example for news. "
                "Apply at https://forms.gle/abc123XYZ</p>")
    assert _extract_submission_url(html) == "https://forms.gle/abc123XYZ"
