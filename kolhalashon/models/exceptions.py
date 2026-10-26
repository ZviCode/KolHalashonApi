from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .enums import QualityLevel


class KolHalashonError(Exception):
    """Base class for every error raised by this library."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class APIError(KolHalashonError):
    """The server answered with an unexpected status code."""

    def __init__(
        self, message: str, status_code: int | None = None, url: str | None = None
    ) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(message)


class CloudflareChallengeError(APIError):
    """The request was answered with a Cloudflare challenge page instead of data."""

    def __init__(self, url: str, status_code: int | None = None) -> None:
        super().__init__(
            f"Cloudflare returned a challenge page for {url}. "
            "Retry later or pass a different session; see the README section 'Cloudflare'.",
            status_code,
            url,
        )


class SessionDisabledException(KolHalashonError):
    def __init__(
        self,
        message: str = (
            "This action requires a logged-in account. Pass username/password, "
            "set KOL_HALASHON_USERNAME/KOL_HALASHON_PASSWORD, or call login()."
        ),
    ) -> None:
        super().__init__(message)


class AuthenticationError(KolHalashonError):
    def __init__(
        self, message: str = "Authentication failed. Please check your credentials."
    ) -> None:
        super().__init__(message)


class TokenExpiredException(AuthenticationError):
    def __init__(self, message: str = "Token expired. Please login again.") -> None:
        super().__init__(message)


class DownloadKeyNotFoundException(APIError):
    def __init__(self, file_id: int, status_code: int | None = None) -> None:
        self.file_id = file_id
        super().__init__(f"Download key for file ID {file_id} was not found.", status_code)


class ShiurDetailsNotFoundException(APIError):
    def __init__(self, file_id: int, status_code: int | None = None) -> None:
        self.file_id = file_id
        super().__init__(f"Details for Shiur with file ID {file_id} were not found.", status_code)


class SessionNotLoadedException(KolHalashonError):
    def __init__(self, message: str = "Session file not found or failed to load.") -> None:
        super().__init__(message)


class SearchFailedException(APIError):
    def __init__(
        self, message: str, status_code: int | None = None, url: str | None = None
    ) -> None:
        super().__init__(
            f"Search failed with status code {status_code}: {message}", status_code, url
        )


class DownloadFailedException(APIError):
    def __init__(
        self,
        message: str,
        status_code: int | None,
        file_id: int,
        quality_level: QualityLevel,
    ) -> None:
        self.file_id = file_id
        self.quality_level = quality_level
        super().__init__(message, status_code)


class RssError(KolHalashonError):
    """The RSS feed could not be fetched or parsed."""


__all__ = [
    "APIError",
    "AuthenticationError",
    "CloudflareChallengeError",
    "DownloadFailedException",
    "DownloadKeyNotFoundException",
    "KolHalashonError",
    "RssError",
    "SearchFailedException",
    "SessionDisabledException",
    "SessionNotLoadedException",
    "ShiurDetailsNotFoundException",
    "TokenExpiredException",
]
