from collections.abc import Generator

import pytest
from pygments.style import Style
from pygments.styles import get_style_by_name
from pygments.token import Token
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


class TestStyles(QtTestCase):
    """Test construction of different styles.

    Skip the ``ConsoleTestCase`` test-case so we can construct our own console.
    """

    class CustomStyle(Style):
        styles = {
            Token.Keyword: "#FFFF00",
        }

    @pytest.mark.parametrize(
        "style, class_hex_color",
        [
            ("default", "#008000"),
            (None, "#008000"),
            ("xcode", "#A90D91"),
            (get_style_by_name("sas"), "#2c2cff"),
            (CustomStyle, "#FFFF00"),
            # Color codes for the "class" Python keyword, taken from pygments.styles
        ],
    )
    def test_other_styles(self, style, class_hex_color):
        """Test how a particular color changes across multiple styles."""
        self.console = PythonConsole(style=style)
        self.bot.add_widget(self.console)
        self.console.show()

        self.console.edit.insertPlainText("class MyClass: ...")
        self.bot.keyClick(self.console.edit, Qt.Key.Key_Enter)

        def check():
            fmts = next(self.get_doc_layouts(self.console.edit)).formats()
            class_format = fmts[0].format  # The formatting of the `class` keyword
            actual_color = class_format.foreground().color()
            assert actual_color.name().lower() == class_hex_color.lower()
            # A little convoluted, but this is a very complete method of asserting the
            # style effect

        self.bot.waitUntil(check)
