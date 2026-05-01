"""Synchronous Claude CLI invocation for one-shot structured extractions.

Distinct from `claude_service.spawn_claude` which is fire-and-forget for
long-running skills. This is for fast (~5-15s) text-in / JSON-out tasks
like CV parsing and portfolio extraction.

Auth comes from the `claude` CLI's OAuth login on the host (no API key
needed). Same binary resolution as `claude_service`.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from typing import Any

from app.services.claude_service import _resolve_claude_binary

log = logging.getLogger(__name__)


class LLMExtractError(RuntimeError):
    """Generic failure invoking the CLI or parsing its output."""


def extract_json_via_cli(
    system_prompt: str,
    user_message: str,
    *,
    model: str = "claude-haiku-4-5",
    timeout_s: int = 180,
) -> dict[str, Any]:
    """Invoke `claude --print` synchronously, return the parsed JSON object.

    The system prompt is written to a temp file (CLI flag is
    `--append-system-prompt-file` per CLAUDE.md gotchas — inline string
    flag exists in some CLI versions but the file approach is portable).
    The user message is passed as the positional prompt argument.

    Strips ``` code fences from the model output before json.loads.
    Raises LLMExtractError on subprocess failure, timeout, non-zero exit,
    or invalid JSON output.
    """
    if not user_message or not user_message.strip():
        raise LLMExtractError("Empty user message — nothing to send to CLI")

    binary = _resolve_claude_binary()

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(system_prompt)
        tmp.flush()
        tmp.close()
        sys_prompt_path = tmp.name

        cmd = [
            binary,
            "--print",
            "--output-format", "text",
            "--append-system-prompt-file", sys_prompt_path,
            "--model", model,
            # Required for non-interactive subprocess: there's no human to
            # approve any tool calls (extraction shouldn't trigger any, but
            # defensive).
            "--dangerously-skip-permissions",
            user_message,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                env={**os.environ},
            )
        except subprocess.TimeoutExpired as e:
            raise LLMExtractError(
                f"Claude CLI timed out after {timeout_s}s"
            ) from e
        except FileNotFoundError as e:
            raise LLMExtractError(
                f"Claude CLI binary not found ({binary}): {e}"
            ) from e

        if result.returncode != 0:
            stderr_tail = (result.stderr or "")[-500:]
            raise LLMExtractError(
                f"Claude CLI exited {result.returncode}: {stderr_tail}"
            )

        raw = (result.stdout or "").strip()

        # Strip ```json ... ``` fences if model wrapped output despite prompt
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            log.warning("CLI returned invalid JSON: %s", raw[:500])
            raise LLMExtractError(
                f"Failed to parse Claude CLI JSON output: {e}"
            ) from e
    finally:
        try:
            os.unlink(sys_prompt_path)
        except (OSError, NameError):
            pass
