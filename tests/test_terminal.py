from __future__ import annotations

import io
import unittest

from zotero_organiser.terminal import Terminal, _parse_choice_many


class TerminalTests(unittest.TestCase):
    def terminal(self, answers: list[str]) -> tuple[Terminal, io.StringIO]:
        leftover = list(answers)
        output = io.StringIO()

        def input_fn(prompt: str) -> str:
            if not leftover:
                raise AssertionError(f"no scripted answer for: {prompt}")
            return leftover.pop(0)

        return Terminal(input_fn=input_fn, output=output), output

    def test_choose_uses_default_on_empty_input(self):
        ui, _output = self.terminal([""])
        self.assertEqual(ui.choose("Pick", ["one", "two"], default=0), 0)

    def test_choose_many_parses_comma_and_space_lists(self):
        self.assertEqual(_parse_choice_many("1,3", 3), [0, 2])
        self.assertEqual(_parse_choice_many("1 2", 3), [0, 1])
        self.assertEqual(_parse_choice_many("all", 3), [0, 1, 2])
        self.assertIsNone(_parse_choice_many("", 3))
        self.assertIsNone(_parse_choice_many("0", 3))
        self.assertIsNone(_parse_choice_many("4", 3))
        self.assertIsNone(_parse_choice_many("a", 3))

    def test_choose_many_uses_defaults_on_empty_input(self):
        ui, _output = self.terminal([""])
        selected = ui.choose_many("Sizes", ["small", "medium", "large"], defaults=[0])
        self.assertEqual(selected, [0])

    def test_choose_many_retries_on_invalid_input(self):
        ui, output = self.terminal(["0", "1,2"])
        selected = ui.choose_many("Sizes", ["small", "medium", "large"])
        self.assertEqual(selected, [0, 1])
        self.assertIn("Enter numbers from 1 to 3", output.getvalue())

    def test_choose_many_deduplicates_and_keeps_order(self):
        ui, _output = self.terminal(["2,1,2"])
        self.assertEqual(ui.choose_many("Sizes", ["small", "medium"]), [1, 0])


if __name__ == "__main__":
    unittest.main()
