"""Tests for the outcome-typed apply contract and browser-session lifecycle."""
from src.sites.base import ApplyResult, interpret_apply_result
from src import browser_utils


# ── interpret_apply_result ───────────────────────────────────────────────────

def test_bool_true_is_submitted_not_retryable():
    assert interpret_apply_result(True) == (True, False)


def test_bool_false_is_not_applied_not_retryable():
    assert interpret_apply_result(False) == (False, False)


def test_none_is_not_applied():
    assert interpret_apply_result(None) == (False, False)


def test_submitted_enum():
    assert interpret_apply_result(ApplyResult.SUBMITTED) == (True, False)


def test_transient_is_retryable_not_applied():
    assert interpret_apply_result(ApplyResult.TRANSIENT_ERROR) == (False, True)


def test_needs_review_not_applied_not_retryable():
    assert interpret_apply_result(ApplyResult.NEEDS_REVIEW) == (False, False)


def test_not_applicable():
    assert interpret_apply_result(ApplyResult.NOT_APPLICABLE) == (False, False)


# ── browser_session: teardown is guaranteed even on exception ────────────────

class _FakeBrowser:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeContext:
    def new_page(self):
        return "PAGE"


class _FakeChromium:
    def __init__(self, browser):
        self._browser = browser

    def launch(self, headless=True):
        return self._browser


class _FakePlaywright:
    def __init__(self, browser):
        self.chromium = _FakeChromium(browser)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_playwright(monkeypatch, browser):
    import playwright.sync_api as sync_api
    monkeypatch.setattr(sync_api, "sync_playwright", lambda: _FakePlaywright(browser))
    monkeypatch.setattr(browser_utils, "new_stealth_context", lambda *a, **k: _FakeContext())


def test_browser_session_yields_page_and_closes(monkeypatch):
    browser = _FakeBrowser()
    _patch_playwright(monkeypatch, browser)
    with browser_utils.browser_session() as page:
        assert page == "PAGE"
    assert browser.closed is True


def test_browser_session_closes_on_exception(monkeypatch):
    browser = _FakeBrowser()
    _patch_playwright(monkeypatch, browser)
    try:
        with browser_utils.browser_session():
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert browser.closed is True
