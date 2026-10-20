"""Safe downloader for public GitHub repositories used by the import API.

Repository code is treated as data: this module never executes imported code.
"""
from __future__ import annotations

import io
import json
import stat
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from app.parser.registry import detect_language, UnsupportedLanguageError


class GitHubRepositoryImportError(ValueError):
    """Raised when a GitHub repository cannot be imported safely."""


class GitHubRepositoryImporter:
    MAX_DOWNLOAD_BYTES = 30 * 1024 * 1024
    MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
    MAX_ARCHIVE_ENTRIES = 10_000
    MAX_SOURCE_FILES = 5_000
    MAX_SOURCE_FILE_BYTES = 2 * 1024 * 1024
    USER_AGENT = "Code-Dependency-Graph/1.0"

    def import_repository(
        self,
        repository_url: str,
        destination_dir: str | Path,
        branch: str | None = None,
    ) -> dict:
        owner, repo, url_branch = self._parse_repository_url(repository_url)
        branch = branch or url_branch

        metadata_url = (
            "https://api.github.com/repos/"
            f"{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
        )
        metadata = self._read_json(metadata_url)
        if metadata.get("private"):
            raise GitHubRepositoryImportError(
                "Private repositories are not supported by this endpoint yet."
            )

        branch = branch or metadata.get("default_branch")
        if not branch:
            raise GitHubRepositoryImportError(
                "Could not determine the repository's default branch."
            )

        archive_url = (
            f"{metadata_url}/zipball/"
            f"{urllib.parse.quote(branch, safe='')}"
        )
        archive_bytes = self._read_bytes(archive_url, self.MAX_DOWNLOAD_BYTES)

        destination = Path(destination_dir).resolve()
        destination.mkdir(parents=True, exist_ok=True)

        files = []
        skipped_files = 0
        total_uncompressed = 0

        try:
            archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
        except zipfile.BadZipFile as error:
            raise GitHubRepositoryImportError(
                "GitHub returned an invalid repository archive."
            ) from error

        with archive:
            entries = archive.infolist()
            if len(entries) > self.MAX_ARCHIVE_ENTRIES:
                raise GitHubRepositoryImportError(
                    f"Repository archive has too many entries (limit: "
                    f"{self.MAX_ARCHIVE_ENTRIES})."
                )

            for entry in entries:
                total_uncompressed += entry.file_size
                if total_uncompressed > self.MAX_UNCOMPRESSED_BYTES:
                    raise GitHubRepositoryImportError(
                        "Repository archive exceeds the 100 MB expanded-size limit."
                    )

                if entry.is_dir():
                    continue

                # GitHub ZIP archives contain a single top-level directory.
                parts = PurePosixPath(entry.filename).parts
                if (len(parts) < 2 or ".." in parts or entry.filename.startswith("/")
                        or "\\" in entry.filename):
                    skipped_files += 1
                    continue

                relative_parts = parts[1:]
                if not relative_parts:
                    skipped_files += 1
                    continue

                relative_path = PurePosixPath(*relative_parts).as_posix()
                if relative_path.startswith(".git/") or relative_path == ".git":
                    skipped_files += 1
                    continue

                # Ignore symbolic links; never follow paths supplied by the archive.
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode):
                    skipped_files += 1
                    continue

                try:
                    language = detect_language(relative_path)
                except UnsupportedLanguageError:
                    skipped_files += 1
                    continue

                if entry.file_size > self.MAX_SOURCE_FILE_BYTES:
                    skipped_files += 1
                    continue

                if len(files) >= self.MAX_SOURCE_FILES:
                    raise GitHubRepositoryImportError(
                        f"Repository contains more than {self.MAX_SOURCE_FILES} "
                        "supported source files."
                    )

                try:
                    source_code = archive.read(entry).decode("utf-8")
                except (UnicodeDecodeError, RuntimeError):
                    skipped_files += 1
                    continue

                output_path = destination.joinpath(*relative_parts).resolve()
                try:
                    output_path.relative_to(destination)
                except ValueError:
                    skipped_files += 1
                    continue

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(source_code, encoding="utf-8")

                files.append({
                    "path": relative_path,
                    "language": language,
                    "size_bytes": entry.file_size,
                })

        if not files:
            raise GitHubRepositoryImportError(
                "No supported source files were found in this repository."
            )

        return {
            "owner": owner,
            "repository": repo,
            "branch": branch,
            "files": files,
            "skipped_files": skipped_files,
        }

    def _parse_repository_url(self, repository_url: str) -> tuple[str, str, str | None]:
        try:
            parsed = urllib.parse.urlparse(repository_url.strip())
        except (AttributeError, ValueError) as error:
            raise GitHubRepositoryImportError("Enter a valid GitHub repository URL.") from error

        if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
            raise GitHubRepositoryImportError(
                "Only HTTPS URLs from github.com are supported."
            )

        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            raise GitHubRepositoryImportError(
                "Use a repository URL such as https://github.com/owner/repository."
            )

        owner = parts[0]
        repo = parts[1].removesuffix(".git")
        url_branch = None

        # Also accept a link copied from GitHub's /tree/<branch> page.
        if len(parts) > 2:
            if len(parts) >= 4 and parts[2] == "tree":
                url_branch = parts[3]
            else:
                raise GitHubRepositoryImportError(
                    "Paste the repository URL or a /tree/branch URL, not a file URL."
                )

        if not owner or not repo:
            raise GitHubRepositoryImportError("The repository URL is missing its owner or name.")

        return owner, repo, url_branch

    def _read_json(self, url: str) -> dict:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = response.read(2 * 1024 * 1024 + 1)
            if len(payload) > 2 * 1024 * 1024:
                raise GitHubRepositoryImportError("GitHub metadata response was too large.")
            return json.loads(payload.decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise GitHubRepositoryImportError(
                    "Repository not found. Check the URL and make sure it is public."
                ) from error
            if error.code == 403:
                raise GitHubRepositoryImportError(
                    "GitHub denied the request or its API rate limit was reached."
                ) from error
            raise GitHubRepositoryImportError(
                f"GitHub metadata request failed (HTTP {error.code})."
            ) from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise GitHubRepositoryImportError(
                "Could not contact GitHub. Check the network connection and try again."
            ) from error

    def _read_bytes(self, url: str, max_bytes: int) -> bytes:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": self.USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise GitHubRepositoryImportError(
                    f"Repository archive exceeds the {max_bytes // (1024 * 1024)} MB download limit."
                )
            return payload
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise GitHubRepositoryImportError(
                    "The requested branch was not found in this repository."
                ) from error
            if error.code == 403:
                raise GitHubRepositoryImportError(
                    "GitHub denied the archive request or its rate limit was reached."
                ) from error
            raise GitHubRepositoryImportError(
                f"GitHub archive download failed (HTTP {error.code})."
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise GitHubRepositoryImportError(
                "Could not download the repository from GitHub."
            ) from error