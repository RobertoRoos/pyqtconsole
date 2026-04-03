from collections.abc import Generator
from contextlib import contextmanager

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
    def _console(self, request, _qt_bot) -> Generator[PythonConsole, None, None]:
        if "no_console" in request.keywords:
            yield None
            return  # Explicitly skipped

        self.console = PythonConsole()
        self.bot.add_widget(self.console)
        self.console.show()
        self.console.eval_in_thread()
        yield self.console

    @contextmanager
    def wait_for_output(self, ignore_exception: bool = False):
        """Block (while QtBot is running events) until the line the console is done.

        It is hard to gauge when the console is truly done and any output is put out.
        We will watch the `_current_line` variable for this.

        The output is also watched for any exception, because otherwise we would never
        see them occuring.

        :param ignore_exception: If `True`, don't mind errors in the console output
        """
        line_before = self.console._current_line
        try:
            yield None
        finally:
            self.bot.waitUntil(lambda: self.console._current_line > line_before)

            if not ignore_exception:
                content = self.console.edit.toPlainText()
                bad_words = ("Traceback", "Error", "Exception")
                assert not any(w in content for w in bad_words), (
                    "Unexpected exception in console output:\n" + content
                )

    def submit_and_wait(self, text: str, **kwargs):
        """Enter some text into the prompt, hit [Enter] and wait the output."""
        with self.wait_for_output(**kwargs):
            self.console.edit.insertPlainText(text)
            self.hit_enter()

    def hit_enter(self):
        """Trigger of hitting the [Enter] key inside the prompt."""
        self.bot.keyClick(self.console.edit, Qt.Key.Key_Enter)

    @property
    def doc_layouts(self) -> Generator[QTextLayout, None, None]:
        yield from self.get_doc_layouts(self.console.edit)


class TestConsoleBasics(ConsoleTestCase):
    """A collection of integration tests, directly on the console."""

    def test_basic(self):
        """Test a single, very basic input."""
        self.submit_and_wait("print(1 + 1)")

        lines = self.console.edit.toPlainText().splitlines()
        assert lines == [
            "print(1 + 1)",
            "2",
            "",
        ]

    def test_multibyte_characters(self):
        """Check that e.g. emojis are handled correctly."""
        self.submit_and_wait("my_text = '😎'")
        self.submit_and_wait("print(my_text)")

        lines = self.console.edit.toPlainText().splitlines()
        assert lines[-2].strip() == "😎"

        # Now make sure no weird syntax errors occur:
        self.submit_and_wait("import sys")


class TestConsoleHighlighting(ConsoleTestCase):
    """Integration tests focussing on formatting."""

    def test_syntax_in_output(self):
        """Make sure console output isn't being formatted."""
        # Print a complicated string including Python syntax:
        self.submit_and_wait("print(\"return 'hi!'\\ndef my_func(x): ...\")")

        fmt_ranges = [len(layout.formats()) for layout in self.doc_layouts]
        assert fmt_ranges == [4, 0, 0, 0, 0]
        # The input has two format groups, make sure the output has none


@pytest.mark.no_console
class TestStyles(ConsoleTestCase):
    """Test construction of different styles.

    Skip the `console` auto-fixture.
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

        fmts = next(self.doc_layouts).formats()
        class_format = fmts[0].format  # The formatting of the `class` keyword
        actual_color = class_format.foreground().color()
        assert actual_color.name().lower() == class_hex_color.lower()
        # A little convoluted, but this is a very complete method of asserting the
        # style effect
