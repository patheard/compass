"""Skill for cloning GitHub repositories and providing file contents as context."""

from __future__ import annotations

import logging
import mimetypes
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import git

from app.chat.skills.base import Action, AgentSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class GitHubCloneSkill(AgentSkill):
    """Skill that detects GitHub folder URLs and provides file contents as context.

    This skill does not provide user-facing actions. Instead, it enriches
    the conversation context by cloning GitHub repositories and extracting
    file contents from specified folders.
    """

    name = "github_clone"
    description = "Clone GitHub repositories and extract file contents"
    action_types: List[str] = []  # No user actions

    # Pattern matches:
    # - https://github.com/<org>/<repo>/tree/<branch>/<path>
    # - https://github.com/<org>/<repo>/blob/<branch>/<path>
    GITHUB_URL_PATTERN = re.compile(
        r"https://github\.com/([^/]+)/([^/]+)/(tree|blob)/([^/]+)(/.*)?$"
    )

    # Text file extensions to include
    DEFAULT_ALLOWED_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".sql",
        ".graphql",
        ".proto",
        ".tf",
        ".hcl",
        ".vue",
        ".svelte",
    }

    def __init__(
        self,
        enabled: bool = True,
        max_content_length: int = 10000,
        max_files: int = 20,
        timeout: int = 30,
        allowed_extensions: Optional[set[str]] = None,
    ) -> None:
        """Initialize the GitHub clone skill.

        Args:
            enabled: Whether this skill is enabled
            max_content_length: Maximum total characters to extract
            max_files: Maximum number of files to include
            timeout: Git operation timeout in seconds
            allowed_extensions: Set of file extensions to include
        """
        self.enabled = enabled
        self.max_content_length = max_content_length
        self.max_files = max_files
        self.timeout = timeout
        self.allowed_extensions = (
            allowed_extensions
            if allowed_extensions is not None
            else self.DEFAULT_ALLOWED_EXTENSIONS
        )

    async def can_execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> bool:
        """This skill does not handle actions."""
        return False

    async def execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """This skill does not execute actions."""
        return SkillResult(success=False, message="No actions available")

    async def get_available_actions(self, context: SkillContext) -> List[Action]:
        """This skill provides no user actions."""
        return []

    async def should_enhance_prompt(
        self, user_message: str, context: SkillContext
    ) -> bool:
        """Check if message contains GitHub folder URLs that should enhance the prompt."""
        if not self.enabled:
            return False
        urls = self._extract_github_urls(user_message)
        return len(urls) > 0

    async def get_prompt_enhancement(
        self, user_message: str, context: SkillContext
    ) -> Optional[str]:
        """Clone GitHub repository and extract file contents to enhance system prompt."""
        content = await self.fetch_github_content_from_message(
            user_message, context.user_id
        )
        if content:
            return f"Additional context from GitHub repository:\n{content}"
        return None

    async def fetch_github_content_from_message(
        self, user_message: str, user_id: str
    ) -> Optional[str]:
        """Extract GitHub URLs from message and fetch their content.

        Args:
            user_message: The user's message text
            user_id: The user's ID for creating temp directory

        Returns:
            Combined content from all files, or None if no URLs found
        """
        if not self.enabled:
            logger.info("GitHubCloneSkill is disabled")
            return None

        urls = self._extract_github_urls(user_message)
        if not urls:
            logger.info("No GitHub URLs found in message")
            return None

        logger.info(f"Processing {len(urls)} GitHub URL(s): {urls}")

        # Process each GitHub URL
        all_contents = []
        for url_info in urls:
            logger.info(f"Processing URL: {url_info['full_url']}")
            content = await self._process_github_url(url_info, user_id)
            if content:
                logger.info(
                    f"Successfully extracted content from {url_info['full_url']} ({len(content)} characters)"
                )
                all_contents.append(content)
            else:
                logger.warning(f"No content extracted from {url_info['full_url']}")

        if not all_contents:
            logger.warning("No content extracted from any GitHub URLs")
            return None

        combined = "\n\n---\n\n".join(all_contents)
        logger.info(f"Total combined content length: {len(combined)} characters")
        return combined

    def _extract_github_urls(self, text: str) -> List[Dict[str, str]]:
        """Extract GitHub URLs from text.

        Args:
            text: Text to search for GitHub URLs

        Returns:
            List of dictionaries with parsed URL components
        """
        matches = self.GITHUB_URL_PATTERN.finditer(text)
        urls = []

        for match in matches:
            org = match.group(1)
            repo = match.group(2)
            url_type = match.group(3)  # 'tree' or 'blob'
            branch = match.group(4)
            path = match.group(5) or "/"
            path = path.lstrip("/")

            logger.info(
                f"Found GitHub URL: org={org}, repo={repo}, type={url_type}, branch={branch}, path={path}"
            )

            # Skip blob URLs (individual files) - only process tree URLs (folders)
            if url_type == "blob":
                logger.info(f"Skipping blob URL (individual file): {match.group(0)}")
                continue

            urls.append(
                {
                    "org": org,
                    "repo": repo,
                    "branch": branch,
                    "path": path,
                    "full_url": match.group(0),
                }
            )

        logger.info(f"Extracted {len(urls)} tree URL(s)")
        return urls

    async def _process_github_url(
        self, url_info: Dict[str, str], user_id: str
    ) -> Optional[str]:
        """Process a GitHub URL by cloning and extracting content.

        Args:
            url_info: Dictionary with parsed URL components
            user_id: User ID for temp directory naming

        Returns:
            Formatted file contents or None on failure
        """
        temp_dir = None
        try:
            # Create temporary directory for this user
            temp_base = Path(tempfile.gettempdir()) / f"github_clone_{user_id}"
            logger.info(f"Temp directory path: {temp_base}")

            # Clear existing directory if present
            if temp_base.exists():
                logger.info(f"Clearing existing temp directory: {temp_base}")
                shutil.rmtree(temp_base)

            temp_base.mkdir(parents=True, exist_ok=True)
            temp_dir = temp_base

            # Clone repository
            repo_url = f"https://github.com/{url_info['org']}/{url_info['repo']}.git"
            logger.info(
                f"Cloning repository: {repo_url} (branch: {url_info['branch']})"
            )

            git.Repo.clone_from(
                repo_url,
                temp_dir,
                branch=url_info["branch"],
                depth=1,  # Shallow clone for efficiency
            )

            logger.info(f"Successfully cloned repository to {temp_dir}")

            # Navigate to specified path
            target_path = temp_dir / url_info["path"]
            logger.info(f"Target path: {target_path} (exists: {target_path.exists()})")

            if not target_path.exists():
                logger.warning(f"Path not found in repository: {url_info['path']}")
                return None

            # Extract file contents
            logger.info(f"Extracting file contents from {target_path}")
            file_contents = self._extract_file_contents(target_path, temp_dir)

            if not file_contents:
                logger.warning("No file contents extracted")
                return None

            logger.info(f"Extracted {len(file_contents)} characters of file content")

            # Format output
            header = f"Files from {url_info['org']}/{url_info['repo']} (branch: {url_info['branch']}, path: {url_info['path'] or 'root'}):\n"
            return header + file_contents

        except git.GitCommandError as exc:
            logger.error(f"Git error cloning repository: {exc}", exc_info=True)
            return f"Unable to clone repository {url_info['org']}/{url_info['repo']}. The repository may be private or the branch may not exist."
        except Exception as exc:
            logger.error(f"Error processing GitHub URL: {exc}", exc_info=True)
            return None
        finally:
            # Cleanup temporary directory
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as exc:
                    logger.warning(f"Failed to cleanup temp directory: {exc}")

    def _extract_file_contents(
        self, target_path: Path, repo_root: Path
    ) -> Optional[str]:
        """Extract contents from files in the target path.

        Args:
            target_path: Path to extract files from
            repo_root: Root of the repository

        Returns:
            Formatted file contents or None
        """
        contents = []
        total_length = 0
        file_count = 0

        # Walk directory tree
        if target_path.is_file():
            files_to_process = [target_path]
            logger.info(f"Target is a file: {target_path}")
        else:
            files_to_process = sorted(target_path.rglob("*"))
            logger.info(f"Target is a directory, found {len(files_to_process)} items")

        for file_path in files_to_process:
            # Skip if not a file
            if not file_path.is_file():
                logger.debug(f"Skipping non-file: {file_path}")
                continue

            # Skip if not in allowed extensions
            if file_path.suffix not in self.allowed_extensions:
                logger.debug(
                    f"Skipping file with disallowed extension: {file_path} (suffix: {file_path.suffix})"
                )
                continue

            # Skip hidden files and common non-source directories
            if any(part.startswith(".") for part in file_path.parts):
                logger.debug(f"Skipping hidden file: {file_path}")
                continue
            if any(
                part in {"node_modules", "__pycache__", "venv", ".git"}
                for part in file_path.parts
            ):
                logger.debug(f"Skipping file in excluded directory: {file_path}")
                continue

            # Check file count limit
            if file_count >= self.max_files:
                logger.info(f"Reached maximum file limit of {self.max_files} files")
                contents.append(
                    f"\n[Reached maximum file limit of {self.max_files} files]"
                )
                break

            # Check if file is binary
            if self._is_binary_file(file_path):
                logger.debug(f"Skipping binary file: {file_path}")
                continue

            try:
                # Read file content
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Get relative path for display
                rel_path = file_path.relative_to(repo_root)
                logger.info(f"Processing file: {rel_path} ({len(content)} characters)")

                # Format file content
                file_entry = f"\n\n--- File: {rel_path} ---\n{content}"

                # Check content length limit
                if total_length + len(file_entry) > self.max_content_length:
                    remaining = self.max_content_length - total_length
                    logger.info(
                        f"Reached content length limit. Remaining: {remaining} characters"
                    )
                    if remaining > 100:  # Only add if meaningful content remains
                        truncated_entry = file_entry[:remaining] + "\n...[truncated]"
                        contents.append(truncated_entry)
                    contents.append(
                        f"\n[Reached maximum content length of {self.max_content_length} characters]"
                    )
                    break

                contents.append(file_entry)
                total_length += len(file_entry)
                file_count += 1

            except Exception as exc:
                logger.warning(f"Error reading file {file_path}: {exc}")
                continue

        logger.info(
            f"Extracted {file_count} files, total length: {total_length} characters"
        )

        if not contents:
            logger.warning("No contents extracted from any files")
            return None

        return "".join(contents)

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary.

        Args:
            file_path: Path to file

        Returns:
            True if file appears to be binary
        """
        # Check mime type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and not mime_type.startswith("text/"):
            return True

        # Read first chunk and check for null bytes
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return True
        except Exception:
            return True

        return False
