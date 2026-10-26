from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import requests

from kolhalashon import KolHalashonAPI

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@dataclass
class Call:
    method: str
    url: str
    headers: dict[str, str]
    json: Any


@dataclass
class FakeSession(requests.Session):
    """`requests.Session` that answers from a list of (method, url regex) routes."""

    routes: list[tuple[str, re.Pattern[str], Any]] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__()

    def add(
        self,
        method: str,
        pattern: str,
        body: Any = None,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.routes.append((method, re.compile(pattern), (body, status, headers or {})))

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:  # type: ignore[override]
        self.calls.append(Call(method, url, dict(kwargs.get("headers") or {}), kwargs.get("json")))
        for route_method, pattern, (body, status, headers) in reversed(self.routes):
            if route_method == method and pattern.search(url):
                response = requests.Response()
                response.status_code = status
                response.url = url
                response.headers.update(headers)
                response._content_consumed = True  # type: ignore[attr-defined]
                if isinstance(body, bytes):
                    response._content = body
                elif body is None:
                    response._content = b""
                else:
                    response._content = json.dumps(body).encode()
                    response.headers.setdefault("content-type", "application/json")
                return response
        raise AssertionError(f"Unexpected request: {method} {url}")


@pytest.fixture
def fake() -> FakeSession:
    return FakeSession()


@pytest.fixture
def api(fake: FakeSession) -> KolHalashonAPI:
    return KolHalashonAPI(username="", password="", session=fake)
