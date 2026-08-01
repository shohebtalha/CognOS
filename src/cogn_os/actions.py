from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ActionResult:
    ok: bool
    message: str
    requires_confirmation: bool = False
    result: dict | None = None


class ActionExecutor:
    """Executes explicit assistant actions with confirmation gates."""

    def execute(self, kind: str, payload: dict, confirmed: bool = False) -> ActionResult:
        if kind == "ask":
            return ActionResult(True, "Prompt ready.", False, {"prompt": payload.get("prompt", "")})
        if kind == "index_file":
            path = Path(str(payload.get("path", ""))).expanduser()
            if not confirmed:
                return ActionResult(False, f"Index local file {path}?", True, {"path": str(path)})
            if not path.exists() or not path.is_file():
                return ActionResult(False, "File does not exist or is not a regular file.")
            return ActionResult(True, "File is ready for indexing.", False, {"path": str(path), "size": path.stat().st_size})
        return ActionResult(False, f"Unsupported action kind: {kind}")
