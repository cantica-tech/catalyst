"""`catalyst serve --local --static <dir>` (roadmap R5.8; REQ-000033): a
page served beside the local API, from a directory the caller gives, with
the API kept to that page."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from catalyst import serve
from catalyst.__main__ import main
from catalyst_fixtures import make_project, write


@pytest.fixture
def page(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    site = tmp_path / "site"
    write(site / "index.html", "<!doctype html><title>Studio</title>\n")
    write(site / "app" / "main.js", "console.log('hi');\n")
    write(tmp_path / "secret.txt", "outside\n")
    httpd, token = serve.make_local(project, 0, poll=0.1, static=site)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", token
    httpd.shutdown()
    httpd.server_close()


def _get(url: str, **headers) -> tuple[int, dict, bytes]:
    try:
        req = urllib.request.Request(url, headers=headers)  # noqa: S310 (the test's localhost server)
        with urllib.request.urlopen(req, timeout=10) as res:  # noqa: S310 (the test's localhost server)
            return res.status, dict(res.headers), res.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()


def test_the_files_are_served_without_a_token(page):
    url, _ = page
    status, headers, body = _get(url + "/")
    assert status == 200 and b"<title>Studio</title>" in body
    assert headers["Content-Type"] == "text/html; charset=utf-8" and headers["X-Content-Type-Options"] == "nosniff"
    status, headers, body = _get(url + "/app/main.js")
    assert status == 200 and "javascript" in headers["Content-Type"] and body == b"console.log('hi');\n"


def test_nothing_outside_the_directory_is_served(page):
    url, _ = page
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/app/../../secret.txt", "/missing.html"):
        status, _, body = _get(url + path)
        assert status == 404 and b"outside" not in body


def test_the_api_still_needs_the_token_and_answers_its_own_page_only(page):
    url, token = page
    assert _get(url + "/v1/graph")[0] == 401
    status, _, body = _get(url + "/v1/graph", Authorization=f"Bearer {token}")
    assert status == 200 and "artifacts" in json.loads(body)
    own = url.replace("127.0.0.1", "localhost")
    for origin in (url, own):
        assert _get(url + "/v1/graph", Authorization=f"Bearer {token}", Origin=origin)[0] == 200
    status, _, body = _get(url + "/v1/graph", Authorization=f"Bearer {token}", Origin="https://elsewhere.example")
    assert status == 403 and "its own page only" in json.loads(body)["error"]


def test_the_start_line_gives_the_page_with_its_token(tmp_path):
    line = serve.start_line("http://127.0.0.1:5000", "cst_x", 42, static=True)
    assert line == {
        "url": "http://127.0.0.1:5000",
        "token": "cst_x",
        "pid": 42,
        "page": "http://127.0.0.1:5000/#token=cst_x",
    }
    assert "page" not in serve.start_line("http://127.0.0.1:5000", "cst_x", 42, static=False)


def test_without_static_nothing_changes(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{httpd.server_address[1]}"
        assert _get(url + "/")[0] == 401  # no page: every path is the API's
        # no page to protect: an Origin is not checked
        assert _get(url + "/v1/graph", Authorization=f"Bearer {token}", Origin="https://elsewhere.example")[0] == 200
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_flag_is_refused_where_it_cannot_apply(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    with pytest.raises(SystemExit, match="--static goes with --local"):
        main(["serve", "--static", str(tmp_path)])
    with pytest.raises(SystemExit, match="not a directory"):
        main(["serve", "--local", "--static", str(tmp_path / "nope")])
