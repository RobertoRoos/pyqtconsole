from collections.abc import Generator

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextLayout
from utils import QtTestCase

from pyqtconsole.console import PythonConsole


class ConsoleTestCase(QtTestCase):
    """Extended test case specifically for our console."""

    console: PythonConsole

    @pytest.fixture(autouse=True)
    def _console(self, _qt_bot) -> Generator[PythonConsole, None, None]:
        self.console = PythonConsole()
        self.bot.add_widget(self.console)
        self.console.show()
        self.console.eval_in_thread()
        yield self.console

    def hit_enter(self):
        """Trigger of hitting the [Enter] key inside the prompt."""
        self.bot.keyClick(self.console.edit, Qt.Key.Key_Enter)


class TestConsoleBasics(ConsoleTestCase):
    """A collection of integration tests, directly on the console."""

    def test_basic(self):
        """Test a single, very basic input."""
        self.console.edit.insertPlainText("print(1 + 1)")
        self.hit_enter()

        def check():
            content = self.console.edit.toPlainText()
            lines = content.splitlines()
            assert len(lines) == 3
            assert lines == [
                "print(1 + 1)",
                "2",
                "",
            ]

        self.bot.waitUntil(check)


class TestConsoleHighlighting(ConsoleTestCase):
    """Integration tests focussing on formatting."""

    @property
    def doc_layouts(self) -> Generator[QTextLayout, None, None]:
        yield from self.get_doc_layouts(self.console.edit)

    def test_syntax_in_output(self):
        """Make sure console output isn't being formatted."""
        # Print a complicated string including Python syntax:
        self.console.edit.insertPlainText(
            "print(\"return 'hi!'\\ndef my_func(x): ...\")"
        )
        self.hit_enter()

        def check():
            fmt_ranges = [len(layout.formats()) for layout in self.doc_layouts]
            assert fmt_ranges == [4, 0, 0, 0, 0]
            # The input has two format groups, make sure the output has none

        self.bot.waitUntil(check)
