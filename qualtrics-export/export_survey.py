#!/usr/bin/env python3
"""Export Qualtrics survey responses in one pass using OAuth client credentials.

Reads server, client id/secret, and survey id from a JSON config file, then:
token → start export → poll until complete → download zip → extract → preview.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import logging
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LOGGER = logging.getLogger("qualtrics-export")

POLL_INTERVAL_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 300.0
HTTP_TIMEOUT_SECONDS = 60.0
PREVIEW_ROWS = 20
REQUIRED_CONFIG_KEYS = (
    "server",
    "client_id",
    "client_secret",
    "survey_id",
)


class QualtricsError(RuntimeError):
    """Raised when Qualtrics returns an error or an unexpected payload."""


@dataclass(frozen=True)
class QualtricsConfig:
    """Connection settings loaded from the local config file."""

    server: str
    client_id: str
    client_secret: str
    survey_id: str
    scope: str = "read:survey_responses"
    export_format: str = "csv"


def load_config(path: Path) -> QualtricsConfig:
    """Load and validate Qualtrics settings from a JSON file.

    Args:
        path: Path to the JSON config file.

    Returns:
        A validated configuration object.

    Raises:
        FileNotFoundError: If the config file does not exist.
        QualtricsError: If required keys are missing or empty.
    """
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)

    missing = [key for key in REQUIRED_CONFIG_KEYS if not str(raw.get(key, "")).strip()]
    if missing:
        raise QualtricsError(f"Config {path} is missing required keys: {', '.join(missing)}")

    return QualtricsConfig(
        server=_normalise_server(str(raw["server"])),
        client_id=str(raw["client_id"]).strip(),
        client_secret=str(raw["client_secret"]).strip(),
        survey_id=str(raw["survey_id"]).strip(),
        scope=str(raw.get("scope") or "read:survey_responses").strip(),
        export_format=str(raw.get("format") or "csv").strip(),
    )


def _normalise_server(server: str) -> str:
    """Return a Qualtrics origin with no trailing slash.

    Accepts either a full URL (`https://eu.qualtrics.com`) or a
    hostname / datacenter id (`eu`).
    """
    value = server.strip().rstrip("/")
    if not value:
        raise QualtricsError("Config `server` must not be empty")
    if "://" not in value:
        if "." not in value:
            value = f"{value}.qualtrics.com"
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise QualtricsError(f"Config `server` is not a valid URL: {server}")
    return f"{parsed.scheme}://{parsed.netloc}"


class QualtricsClient:
    """Thin Qualtrics REST client for OAuth and response export."""

    def __init__(self, config: QualtricsConfig) -> None:
        self._config = config

    def fetch_access_token(self) -> str:
        """Request an OAuth access token using client credentials.

        Returns:
            A bearer token with the configured survey-response scope.
        """
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "scope": self._config.scope,
            }
        ).encode("utf-8")
        credentials = base64.b64encode(
            f"{self._config.client_id}:{self._config.client_secret}".encode("utf-8")
        ).decode("ascii")
        payload = self._request_json(
            "POST",
            f"{self._config.server}/oauth2/token",
            body=body,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        token = payload.get("access_token")
        if not token:
            raise QualtricsError(f"Token response did not include access_token: {payload}")
        LOGGER.info("Obtained access token (scope=%s)", payload.get("scope", self._config.scope))
        return str(token)

    def start_export(self, token: str) -> str:
        """Start an asynchronous response export and return its progress id.

        Args:
            token: OAuth bearer token.

        Returns:
            The Qualtrics `progressId` for polling.
        """
        payload = self._request_json(
            "POST",
            self._survey_url("export-responses"),
            body=json.dumps({"format": self._config.export_format}).encode("utf-8"),
            headers=self._bearer_headers(token, content_type="application/json"),
        )
        progress_id = (payload.get("result") or {}).get("progressId")
        if not progress_id:
            raise QualtricsError(f"Export start did not return progressId: {payload}")
        LOGGER.info("Started export progressId=%s", progress_id)
        return str(progress_id)

    def wait_for_file_id(self, token: str, progress_id: str) -> str:
        """Poll export progress until Qualtrics reports a downloadable file.

        Args:
            token: OAuth bearer token.
            progress_id: Id returned by :meth:`start_export`.

        Returns:
            The Qualtrics `fileId` used to download the zip.

        Raises:
            QualtricsError: If the export fails, 404s, or exceeds the timeout.
        """
        deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
        url = self._survey_url(f"export-responses/{urllib.parse.quote(progress_id, safe='')}")
        while time.monotonic() < deadline:
            payload = self._request_json("GET", url, headers=self._bearer_headers(token))
            result = payload.get("result") or {}
            status = str(result.get("status") or "").lower()
            percent = result.get("percentComplete")
            LOGGER.info("Export status=%s percentComplete=%s", status, percent)
            if status == "failed":
                raise QualtricsError(f"Qualtrics export failed: {payload}")
            if status == "complete":
                file_id = result.get("fileId")
                if not file_id:
                    raise QualtricsError(f"Export completed without fileId: {payload}")
                return str(file_id)
            time.sleep(POLL_INTERVAL_SECONDS)
        raise QualtricsError(
            f"Export {progress_id} did not complete within {POLL_TIMEOUT_SECONDS:.0f}s"
        )

    def download_export_zip(self, token: str, file_id: str, destination: Path) -> Path:
        """Download the completed export zip to `destination`.

        Args:
            token: OAuth bearer token.
            file_id: Id returned by :meth:`wait_for_file_id`.
            destination: File path for the zip (parent directories must exist).

        Returns:
            The path that was written.
        """
        url = self._survey_url(
            f"export-responses/{urllib.parse.quote(file_id, safe='')}/file"
        )
        body = self._request_bytes("GET", url, headers=self._bearer_headers(token))
        written = _atomic_write_bytes(destination, body)
        LOGGER.info("Wrote %s (%s bytes)", written, written.stat().st_size)
        return written

    def _survey_url(self, suffix: str) -> str:
        survey_id = urllib.parse.quote(self._config.survey_id, safe="")
        return f"{self._config.server}/API/v3/surveys/{survey_id}/{suffix}"

    @staticmethod
    def _bearer_headers(token: str, content_type: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        raw = self._request_bytes(method, url, body=body, headers=headers)
        if not raw:
            return {}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise QualtricsError(f"Non-JSON response from {url}: {raw[:500]!r}") from exc
        if not isinstance(parsed, dict):
            raise QualtricsError(f"Unexpected JSON from {url}: {parsed!r}")
        return parsed

    def _request_bytes(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise QualtricsError(f"{method} {url} failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise QualtricsError(f"{method} {url} failed: {exc.reason}") from exc


def extract_zip(zip_path: Path, output_dir: Path) -> list[Path]:
    """Extract a Qualtrics export zip into `output_dir`.

    Args:
        zip_path: Downloaded zip file.
        output_dir: Directory that will receive extracted members.

    Returns:
        Paths of extracted files, in zip order.

    Raises:
        QualtricsError: If the archive is empty or contains unsafe paths.
    """
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        if not members:
            raise QualtricsError(f"{zip_path} did not contain any files")
        for info in members:
            target = _safe_extract_path(output_dir, info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source:
                written = _atomic_write_bytes(target, source.read())
            extracted.append(written)
            LOGGER.info("Extracted %s", written)
    return extracted


def export_responses(config: QualtricsConfig, output_root: Path) -> list[Path]:
    """Download and extract a full Qualtrics response export.

    Args:
        config: Validated Qualtrics connection settings.
        output_root: Parent directory; files are written under
            ``output_root / survey_id``.

    Returns:
        Paths of extracted files, in zip order.
    """
    output_dir = output_root / config.survey_id
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{config.survey_id}.{config.export_format}.zip"

    client = QualtricsClient(config)
    token = client.fetch_access_token()
    progress_id = client.start_export(token)
    file_id = client.wait_for_file_id(token, progress_id)
    client.download_export_zip(token, file_id, zip_path)
    return extract_zip(zip_path, output_dir)


def _atomic_write_bytes(destination: Path, body: bytes) -> Path:
    """Write bytes to ``destination`` via a unique sibling temp file.

    Unique temp names avoid Windows file-lock failures when a previous
    export or dashboard reader still has the target open. If replacing the
    existing path fails, the bytes are written to a unique sibling instead
    and that sibling path is returned.

    Args:
        destination: Preferred final path.
        body: File contents.

    Returns:
        The path that actually contains ``body``.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.with_name(f"{destination.name}.{uuid.uuid4().hex}.partial")
    tmp_path.write_bytes(body)
    try:
        tmp_path.replace(destination)
        return destination
    except OSError:
        fallback = destination.with_name(f"{destination.stem}.{uuid.uuid4().hex}{destination.suffix}")
        tmp_path.replace(fallback)
        LOGGER.warning("Could not replace %s; wrote %s instead", destination, fallback)
        return fallback


def _safe_extract_path(output_dir: Path, member_name: str) -> Path:
    """Resolve a zip member under `output_dir`, rejecting path traversal."""
    target = (output_dir / member_name).resolve()
    output_root = output_dir.resolve()
    if target != output_root and output_root not in target.parents:
        raise QualtricsError(f"Refusing to extract unsafe zip path: {member_name}")
    return target


def preview_tabular_file(path: Path, *, max_rows: int = PREVIEW_ROWS) -> None:
    """Print a compact preview of a CSV/TSV export to stdout.

    Qualtrics CSV exports typically include three header rows (question text,
    import ids, and question ids). This preview keeps those headers and a
    limited number of data rows.

    Args:
        path: Extracted tabular file.
        max_rows: Maximum data rows to print after the Qualtrics header block.
    """
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))
    if not rows:
        print(f"\n{path.name} is empty")
        return

    header_rows = rows[:3] if len(rows) >= 3 else rows[:1]
    data_rows = rows[len(header_rows) : len(header_rows) + max_rows]
    omitted = max(0, len(rows) - len(header_rows) - len(data_rows))

    print(f"\n=== {path.name}: {max(0, len(rows) - len(header_rows))} response row(s) ===")
    for row in header_rows + data_rows:
        print(" | ".join(_cell(value) for value in row))
    if omitted:
        print(f"... {omitted} more row(s) omitted")


def _cell(value: str, width: int = 40) -> str:
    text = " ".join(value.split())
    if len(text) > width:
        return text[: width - 1] + "…"
    return text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the export tool."""
    parser = argparse.ArgumentParser(
        description="Export Qualtrics survey responses using OAuth client credentials."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "config.json",
        help="JSON config with server, client_id, client_secret, and survey_id",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="Directory for the zip and extracted files",
    )
    parser.add_argument(
        "--preview-rows",
        type=int,
        default=PREVIEW_ROWS,
        help="Number of response rows to print after extract",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log HTTP progress to stderr",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run a one-pass Qualtrics response export.

    Args:
        argv: Optional argument list; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code (0 on success).
    """
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    try:
        config = load_config(args.config)
        extracted = export_responses(config, args.output_dir)
    except (OSError, QualtricsError) as exc:
        LOGGER.error("%s", exc)
        return 1

    output_dir = args.output_dir / config.survey_id
    print(f"Saved export under {output_dir}")
    for path in extracted:
        print(f"  {path}")
        if path.suffix.lower() in {".csv", ".tsv"}:
            preview_tabular_file(path, max_rows=args.preview_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
