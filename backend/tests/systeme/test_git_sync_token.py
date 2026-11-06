"""Audit B2 : le token GitHub ne doit jamais figurer dans la ligne de commande de git (visible via `ps`)."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import git_sync


def test_token_is_passed_through_environment_not_argv(monkeypatch):
    monkeypatch.setattr(git_sync, "TOKEN", "ghp_secret_token_value")
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["env"] = cmd, kwargs.get("env") or {}
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(git_sync.subprocess, "run", fake_run)
    git_sync._git("fetch", "origin")

    import base64
    encoded = base64.b64encode(b"x-access-token:ghp_secret_token_value").decode()
    assert not any("ghp_secret_token_value" in a or encoded in a for a in seen["cmd"])
    assert seen["cmd"][0] == "git" and "fetch" in seen["cmd"]
    assert encoded in seen["env"]["GIT_CONFIG_VALUE_0"]
    assert seen["env"]["GIT_CONFIG_KEY_0"] == "http.extraheader"
    assert seen["env"]["GIT_CONFIG_COUNT"] == "1"


def test_failure_message_masks_token(monkeypatch):
    monkeypatch.setattr(git_sync, "TOKEN", "ghp_secret_token_value")
    monkeypatch.setattr(git_sync.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 1, stdout="", stderr="fatal: ghp_secret_token_value denied"))
    with pytest.raises(RuntimeError) as exc:
        git_sync._git("push")
    assert "ghp_secret_token_value" not in str(exc.value)
