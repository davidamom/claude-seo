"""Cross-platform hook configuration regressions."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
HOOK_LAUNCHER = REPO_ROOT / "hooks" / "run-python-hook.js"
INSTALL_PS1 = REPO_ROOT / "install.ps1"


def _post_tool_handler() -> dict:
    config = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    return config["hooks"]["PostToolUse"][0]["hooks"][0]


def test_schema_hook_uses_exec_form_args_and_tool_input_placeholder() -> None:
    handler = _post_tool_handler()
    serialized = json.dumps(handler)

    assert handler["type"] == "command"
    assert handler["command"] == "node"
    assert "args" in handler
    assert handler["args"][0] == "${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.js"
    assert handler["args"][1] == "${CLAUDE_PLUGIN_ROOT}/hooks/validate-schema.py"
    assert handler["args"][2] == "${tool_input.file_path}"
    assert "$FILE_PATH" not in serialized
    assert "$" not in handler["command"]
    assert handler["command"] != "sh"


def test_hook_launcher_documents_python_probe_order() -> None:
    text = HOOK_LAUNCHER.read_text(encoding="utf-8")
    for marker in ("CLAUDE_SEO_PYTHON", "py", "-3", "python3", "python"):
        assert marker in text


def test_hook_launcher_preserves_blocking_exit_code_two(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available in this test environment")

    script = tmp_path / "block.py"
    script.write_text(
        "import sys\n"
        "assert sys.argv[1] == 'payload'\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["CLAUDE_SEO_PYTHON"] = sys.executable

    proc = subprocess.run(
        [node, str(HOOK_LAUNCHER), str(script), "payload"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert proc.returncode == 2


def test_windows_installer_prefers_py_launcher_and_rejects_store_stubs() -> None:
    text = INSTALL_PS1.read_text(encoding="utf-8")
    py_pos = text.index("Exe = 'py'; Args = @('-3')")
    python3_pos = text.index("Exe = 'python3'; Args = @()")
    python_pos = text.index("Exe = 'python'; Args = @()")

    assert py_pos < python3_pos < python_pos
    assert "Microsoft Store|App execution alias|was not found" in text
    # Store Python lives under WindowsApps, so the path must never count as the placeholder.
    assert "Microsoft Store|WindowsApps|App execution alias" not in text


def _launcher_probe_accepts(status: int, stdout: str, stderr: str) -> bool:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available in this test environment")

    code = (
        "const launcher = require(process.argv[1]);"
        "const [status, stdout, stderr] = JSON.parse(process.argv[2]);"
        "process.stdout.write(String(launcher.probeAccepts(status, stdout, stderr)));"
    )
    proc = subprocess.run(
        [node, "-e", code, str(HOOK_LAUNCHER), json.dumps([status, stdout, stderr])],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip() == "true"


STORE_PYTHON_PROBE = (
    "C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\"
    "PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\python.exe\n3.13.14\n"
)
STORE_PLACEHOLDER_HINT = (
    "Python was not found; run without arguments to install from the Microsoft Store, "
    "or disable this shortcut from Settings > Apps > Advanced app settings > "
    "App execution aliases."
)


def test_hook_launcher_accepts_store_python_under_windowsapps() -> None:
    assert _launcher_probe_accepts(0, STORE_PYTHON_PROBE, "")


def test_hook_launcher_rejects_store_placeholder() -> None:
    assert not _launcher_probe_accepts(9009, STORE_PLACEHOLDER_HINT, "")
    assert not _launcher_probe_accepts(0, STORE_PLACEHOLDER_HINT, "")
    assert not _launcher_probe_accepts(0, STORE_PYTHON_PROBE, STORE_PLACEHOLDER_HINT)
