"""Small dependency-free terminal prompts used by the guided commands."""

from __future__ import annotations

import sys


class Terminal:
    def __init__(self, *, input_fn=input, output=None):
        self.input_fn = input_fn
        self.output = output or sys.stdout
        self.colour = bool(getattr(self.output, "isatty", lambda: False)())

    def heading(self, text: str) -> None:
        self.write(text, style="1;36")

    def write(self, text: str = "", *, style: str | None = None) -> None:
        if style and self.colour:
            text = f"\033[{style}m{text}\033[0m"
        print(text, file=self.output)

    def ask(self, prompt: str, default: str | None = None) -> str:
        suffix = f" [{default}]" if default is not None else ""
        value = self.input_fn(f"{prompt}{suffix}: ").strip()
        return value or (default or "")

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        hint = "Y/n" if default else "y/N"
        while True:
            value = self.ask(f"{prompt} ({hint})").lower()
            if not value:
                return default
            if value in {"y", "yes"}:
                return True
            if value in {"n", "no"}:
                return False
            self.write("Please answer yes or no.")

    def choose(self, prompt: str, choices: list[str], *, default: int | None = None) -> int:
        self.write(prompt)
        for index, choice in enumerate(choices, start=1):
            self.write(f"  {index}. {choice}")
        hint = str(default + 1) if default is not None else None
        while True:
            value = self.ask("Choose a number", hint)
            try:
                selected = int(value)
            except ValueError:
                selected = 0
            if 1 <= selected <= len(choices):
                return selected - 1
            self.write(f"Enter a number from 1 to {len(choices)}.")

    def choose_many(
        self, prompt: str, choices: list[str], *, defaults: list[int] | None = None
    ) -> list[int]:
        self.write(prompt)
        for index, choice in enumerate(choices, start=1):
            self.write(f"  {index}. {choice}")
        hint = ",".join(str(index + 1) for index in defaults) if defaults else None
        while True:
            value = self.ask(
                "Choose one or more numbers (comma or space separated, or 'all')", hint
            )
            selected = _parse_choice_many(value, len(choices))
            if selected is not None:
                return selected
            self.write(f"Enter numbers from 1 to {len(choices)}, or 'all'.")


def _parse_choice_many(value: str, count: int) -> list[int] | None:
    text = value.strip().lower()
    if not text:
        return None
    if text == "all":
        return list(range(count))
    parts = [part for part in text.replace(",", " ").split() if part]
    selected: list[int] = []
    for part in parts:
        try:
            number = int(part)
        except ValueError:
            return None
        if not 1 <= number <= count:
            return None
        index = number - 1
        if index not in selected:
            selected.append(index)
    return selected or None
