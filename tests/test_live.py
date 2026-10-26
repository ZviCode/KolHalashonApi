"""Tests against the real servers. Run with: uv run pytest -m live"""

from __future__ import annotations

import pytest

from kolhalashon import CloudflareChallengeError, KolHalashonAPI

pytestmark = pytest.mark.live


def test_live_rss() -> None:
    feed = KolHalashonAPI().load_rss(5761, rav_id=7)
    assert feed.title
    assert feed.items


def test_live_search() -> None:
    try:
        result = KolHalashonAPI().search_items("אשר וייס")
    except CloudflareChallengeError:
        pytest.skip("API is behind a Cloudflare challenge for this client")
    assert result.rabanim
