"""Tests for the immutable GHCR tag guard."""

from __future__ import annotations

import json
from typing import Self
from urllib.error import HTTPError, URLError

import pytest

from script.abedome.check_ghcr_tag import GhcrTagCheckError, tag_exists, validate_tag


def _version(*tags: str) -> dict[str, object]:
    return {"metadata": {"container": {"tags": list(tags)}}}


class _Response:
    def __init__(
        self,
        payload: object | None = None,
        *,
        status: int = 200,
        raw_body: bytes | None = None,
    ) -> None:
        self.status = status
        self._body = raw_body if raw_body is not None else json.dumps(payload).encode()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class _Opener:
    def __init__(self, *pages_or_errors: object) -> None:
        self._pages_or_errors = list(pages_or_errors)
        self.requests: list[object] = []

    def __call__(self, request: object, *, timeout: int) -> _Response:
        self.requests.append(request)
        self.assert_timeout(timeout)
        if not self._pages_or_errors:
            raise AssertionError("unexpected extra request")
        item = self._pages_or_errors.pop(0)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, _Response):
            return item
        return _Response(item)

    @staticmethod
    def assert_timeout(timeout: int) -> None:
        if timeout != 30:
            raise AssertionError(f"unexpected timeout: {timeout}")


def _call(opener: _Opener, tag: str = "2026.9.0.dev2") -> bool:
    return tag_exists(
        owner="Mauro2020",
        package="abedome-core",
        tag=tag,
        token="test-token",
        opener=opener,
    )


def test_exact_existing_tag_is_refused() -> None:
    """Refuse an exact existing tag."""
    assert _call(_Opener([_version("2026.9.0.dev2")]))


def test_similar_tag_does_not_match() -> None:
    """Do not confuse a similar tag with an exact match."""
    assert not _call(_Opener([_version("2026.9.0.dev20")]))


def test_all_pages_are_scanned() -> None:
    """Scan every returned page for an exact match."""
    first_page = [_version() for _ in range(100)]
    second_page = [_version("2026.9.0.dev2")]
    opener = _Opener(first_page, second_page)

    assert _call(opener)
    assert len(opener.requests) == 2


def test_untagged_versions_allow_first_publication() -> None:
    """Allow publication when existing versions are untagged."""
    assert not _call(_Opener([_version(), _version()]))


def test_http_errors_fail_closed() -> None:
    """Fail closed when the API returns an HTTP error."""
    error = HTTPError("https://api.github.test", 403, "Forbidden", {}, None)
    with pytest.raises(GhcrTagCheckError, match="HTTP 403"):
        _call(_Opener(error))


def test_unexpected_response_status_fails_closed() -> None:
    """Fail closed when the response status is unexpected."""
    with pytest.raises(GhcrTagCheckError, match="HTTP status 503"):
        _call(_Opener(_Response([], status=503)))


def test_network_errors_fail_closed() -> None:
    """Fail closed when the API cannot be reached."""
    with pytest.raises(GhcrTagCheckError, match="could not be reached"):
        _call(_Opener(URLError("offline")))


def test_malformed_schema_fails_closed() -> None:
    """Fail closed when package metadata is malformed."""
    with pytest.raises(GhcrTagCheckError, match="metadata"):
        _call(_Opener([{"metadata": {}}]))


def test_invalid_json_fails_closed() -> None:
    """Fail closed when the API response is not valid JSON."""
    with pytest.raises(GhcrTagCheckError, match="invalid JSON"):
        _call(_Opener(_Response(raw_body=b"not-json")))


def test_missing_token_fails_before_network() -> None:
    """Reject a missing token before any network request."""
    opener = _Opener([])
    with pytest.raises(GhcrTagCheckError, match="token"):
        tag_exists(
            owner="Mauro2020",
            package="abedome-core",
            tag="2026.9.0.dev2",
            token="",
            opener=opener,
        )
    assert opener.requests == []


def test_invalid_tag_fails_before_network() -> None:
    """Reject an invalid container tag before any network request."""
    with pytest.raises(GhcrTagCheckError, match="invalid container tag"):
        validate_tag("not a tag")
