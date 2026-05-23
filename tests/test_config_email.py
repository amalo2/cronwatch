"""Integration tests: config loader recognises email channel definitions."""

import textwrap
from pathlib import Path

import pytest

from cronwatch.config import load_config
from cronwatch.email_channel import EmailChannel


@pytest.fixture()
def cfg_file(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        jobs:
          nightly_backup:
            schedule: "0 2 * * *"
            silence_threshold_s: 7200

        alerts:
          channels:
            - type: email
              smtp_host: smtp.example.com
              smtp_port: 587
              sender: cronwatch@example.com
              recipients:
                - ops@example.com
                - backup@example.com
              use_tls: true
    """)
    p = tmp_path / "cronwatch.yaml"
    p.write_text(content)
    return p


def test_load_config_creates_email_channel(cfg_file):
    cfg = load_config(cfg_file)
    channels = cfg["dispatcher"].channels
    assert len(channels) == 1
    assert isinstance(channels[0], EmailChannel)


def test_email_channel_has_correct_host(cfg_file):
    cfg = load_config(cfg_file)
    ch: EmailChannel = cfg["dispatcher"].channels[0]
    assert ch.smtp_host == "smtp.example.com"


def test_email_channel_has_multiple_recipients(cfg_file):
    cfg = load_config(cfg_file)
    ch: EmailChannel = cfg["dispatcher"].channels[0]
    assert len(ch.recipients) == 2
    assert "ops@example.com" in ch.recipients


def test_load_config_creates_job(cfg_file):
    cfg = load_config(cfg_file)
    assert "nightly_backup" in cfg["jobs"]


def test_unknown_channel_type_skipped(tmp_path):
    content = textwrap.dedent("""\
        jobs: {}
        alerts:
          channels:
            - type: slack
              url: https://hooks.slack.com/xxx
    """)
    p = tmp_path / "cronwatch.yaml"
    p.write_text(content)
    cfg = load_config(p)
    assert cfg["dispatcher"].channels == []


def test_bad_email_config_skipped(tmp_path, caplog):
    content = textwrap.dedent("""\
        jobs: {}
        alerts:
          channels:
            - type: email
              smtp_host: ""
    """)
    p = tmp_path / "cronwatch.yaml"
    p.write_text(content)
    cfg = load_config(p)
    assert cfg["dispatcher"].channels == []
    assert "email" in caplog.text
