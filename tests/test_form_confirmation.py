"""C1 tests: submission is reported successful only with real confirmation evidence.

Uses tiny duck-typed fakes instead of a real browser (Playwright page API surface
used by the helpers is small and stable).
"""
from src import form_filler as ff


class FakeElement:
    def __init__(self, *, visible=True, attrs=None, value="", text=""):
        self._visible = visible
        self._attrs = attrs or {}
        self._value = value
        self._text = text

    def is_visible(self):
        return self._visible

    def get_attribute(self, name):
        return self._attrs.get(name)

    def input_value(self):
        return self._value

    def inner_text(self):
        return self._text


class FakePage:
    def __init__(self, url="http://x/apply", content="", submit_el=None, required=None, labels=None):
        self.url = url
        self._content = content
        self._submit_el = submit_el
        self._required = required or []
        self._labels = labels or {}

    def content(self):
        return self._content

    def query_selector(self, selector):
        # Only used by _submission_confirmed for the submit button.
        return self._submit_el

    def query_selector_all(self, selector):
        # _unanswered_required_fields asks for required fields;
        # _get_label asks for label[for=...] (return none → falls back to attrs).
        if "required" in selector:
            return self._required
        return []


# ── _submission_confirmed ────────────────────────────────────────────────────

def test_confirmed_when_url_changes():
    page = FakePage(url="http://x/thank-you")
    assert ff._submission_confirmed(page, url_before="http://x/apply") is True


def test_confirmed_when_confirmation_text_present():
    page = FakePage(url="http://x/apply", content="<h1>Thank you for applying</h1>")
    assert ff._submission_confirmed(page, url_before="http://x/apply") is True


def test_confirmed_when_submit_button_disappears():
    page = FakePage(url="http://x/apply", content="<div>form</div>", submit_el=None)
    assert ff._submission_confirmed(page, url_before="http://x/apply",
                                    submit_selector="button[type=submit]") is True


def test_not_confirmed_when_nothing_changed():
    still_there = FakeElement(visible=True)
    page = FakePage(url="http://x/apply", content="<div>same form</div>", submit_el=still_there)
    assert ff._submission_confirmed(page, url_before="http://x/apply",
                                    submit_selector="button[type=submit]") is False


# ── _unanswered_required_fields ──────────────────────────────────────────────

def test_empty_required_text_field_is_flagged():
    el = FakeElement(visible=True, attrs={"type": "text", "name": "years_experience"}, value="")
    page = FakePage(required=[el])
    missing = ff._unanswered_required_fields(page)
    assert any("years_experience" in m for m in missing)


def test_filled_required_field_not_flagged():
    el = FakeElement(visible=True, attrs={"type": "text", "name": "name"}, value="Saeed")
    page = FakePage(required=[el])
    assert ff._unanswered_required_fields(page) == []


def test_file_input_is_excluded():
    el = FakeElement(visible=True, attrs={"type": "file", "name": "cv"}, value="")
    page = FakePage(required=[el])
    assert ff._unanswered_required_fields(page) == []
