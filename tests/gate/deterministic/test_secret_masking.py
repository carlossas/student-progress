"""Secrets never reach the LLM: the prompt is built from masked text (gate/ai/prompt_builder.py)."""

from gate.ai.prompt_builder import user_prompt
from gate.deterministic.secrets_scan import REDACTED, mask_secrets
from gate.diff import DiffContext

# Built in pieces so this file doesn't trip the secret scanner it tests. Shape of golden PR #5.
KEY = "SG" + ".kx9mPqT4RhaW2nZvBcYdEg" + ".7JfLs3uNo8QwXeKtViMbAyD1cH5rGpZjUmS0aTnRq6wE"
NOTIFICATIONS = f'import logging\n\nSENDGRID_API_KEY = "{KEY}"\nFROM = "reminders@openenglish.com"\n'


def test_mask_secrets_keeps_lines_and_code():
    masked = mask_secrets(NOTIFICATIONS)
    assert KEY not in masked and REDACTED in masked
    assert masked.count("\n") == NOTIFICATIONS.count("\n")
    assert 'SENDGRID_API_KEY = "' in masked  # the model still sees that a key is hard-coded
    credential = "pass" + 'word = "' + "hunter2" * 2 + '"'
    assert mask_secrets(credential) == "pass" + f'word = "{REDACTED}"'
    assert mask_secrets("timeout = 30") == "timeout = 30"


def test_prompt_never_contains_the_secret(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "notifications.py").write_text(NOTIFICATIONS, encoding="utf-8")
    ctx = DiffContext(
        tmp_path, {"app/notifications.py": None}, "fixture", pr_title="Reminders", pr_body=f"Uses key {KEY}"
    )
    prompt = user_prompt(ctx, [], [])
    assert KEY not in prompt
    assert prompt.count(REDACTED) == 2  # file + PR body
