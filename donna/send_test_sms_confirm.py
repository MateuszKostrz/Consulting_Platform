#!/usr/bin/env python3
"""Send a test SMS after local confirmation popups."""

from __future__ import annotations

import platform
import subprocess
import sys

from dotenv import load_dotenv

from send_sms import default_env_file, send_sms

DEFAULT_PHONE = "663337793"
DEFAULT_SENDER = "DONNA"
DEFAULT_MESSAGE = "Test wiadomosc DONNA - sprawdzenie wysylki SMS."

CONFIRMATION_STEPS = (
    ("Are you sure you want to send SMS?", "yes"),
    ("What's the name of the best gf in the world?", "ola"),
    ("Also known as...", "baby girl"),
)


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_answer(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _ask_macos(prompt: str) -> str | None:
    escaped_prompt = _escape_applescript(prompt)
    script = (
        f'text returned of (display dialog "{escaped_prompt}" default answer "" '
        'buttons {"Cancel", "Continue"} default button "Cancel")'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return None

    return result.stdout.strip()


def _ask_terminal(prompt: str) -> str | None:
    try:
        return input(f"{prompt} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _show_macos_alert(title: str, message: str) -> None:
    escaped_title = _escape_applescript(title)
    escaped_message = _escape_applescript(message)
    subprocess.run(
        [
            "osascript",
            "-e",
            f'display alert "{escaped_title}" message "{escaped_message}"',
        ],
        check=False,
    )


def confirm_send() -> bool:
    use_macos = platform.system() == "Darwin"
    if use_macos:
        probe = subprocess.run(["osascript", "-e", "return \"ok\""], capture_output=True, text=True)
        if probe.returncode != 0:
            print("osascript unavailable; falling back to terminal confirmation.", file=sys.stderr)
            use_macos = False

    for prompt, expected in CONFIRMATION_STEPS:
        while True:
            answer = _ask_macos(prompt) if use_macos else _ask_terminal(prompt)
            if answer is None:
                return False
            if _normalize_answer(answer) == _normalize_answer(expected):
                break
            if use_macos:
                _show_macos_alert("Wrong answer", "Wrong answer")
            else:
                print("Wrong answer. Try again.")

    return True


def main() -> int:
    load_dotenv(default_env_file())

    if not confirm_send():
        print("SMS not sent.")
        return 0

    try:
        result = send_sms(
            [DEFAULT_PHONE],
            DEFAULT_MESSAGE,
            sender=DEFAULT_SENDER,
            campaign_name="manual-test",
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    message_id = result.get("messageId", result)
    print(f"SMS sent to {DEFAULT_PHONE}. SMS Planet messageId: {message_id}")

    if platform.system() == "Darwin":
        alert_message = _escape_applescript(
            f"Message sent to {DEFAULT_PHONE}.\nSMS Planet messageId: {message_id}"
        )
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display alert "SMS sent" message "{alert_message}" as informational',
            ],
            check=False,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
