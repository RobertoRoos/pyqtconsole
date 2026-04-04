from collections.abc import Generator

import pytest
from pygments.token import Token
from qtpy.QtGui import QTextCursor, QTextLayout
from qtpy.QtWidgets import QPlainTextEdit
from utils import QtTestCase

from pyqtconsole.highlighter import HighlightKind, PythonHighlighter


class TestHighlighting(QtTestCase):
    """Collection of tests that focus the highlighting.

    No full console is spawned, tests are done simplified.

    There is a fundamental issue here: testing the formatting is trial to do manually,
    just by looking at the window. It's a pain to do this programmatically. On top of
    this, Qt makes it next to impossible to retrieve an e.g. full HTML result of a
    QSyntaxHighlighter.
    So instead these tests serve mostly to touch the code and make sure there's no
    exceptions.
    You can visually check a test yourself by inserting a statement like this at the
    end:
    ```
    self.bot.wait(2000)
    ```
    """

    text_edit: QPlainTextEdit
    highlighter: PythonHighlighter

    @pytest.fixture(autouse=True)
    def _text_edit(self, _qt_bot):
        self.text_edit = QPlainTextEdit()
        self.text_edit.show()
        yield self.text_edit

    @pytest.fixture(autouse=True)
    def _highlighter(self, _text_edit):
        self.highlighter = PythonHighlighter(self.text_edit.document())
        yield self.highlighter

    @property
    def doc_layouts(self) -> Generator[QTextLayout, None, None]:
        yield from self.get_doc_layouts(self.text_edit)

    @property
    def formatting_ranges(self) -> list[list[int]]:
        """Get a list of list for formatting rule ranges."""
        return [[fmt.length for fmt in layout.formats()] for layout in self.doc_layouts]

    def test_demo(self):
        """Small sample, mostly for manual testing."""

        self.text_edit.setPlainText("""# Leading comment
def test(my_arg: int = 0):
    # Some comment
    str_literal = "hello world"
    my_variable = my_arg + 420
    return my_variable

outcome = test(5)""")

        expected_format_ranges = [
            [17],  # <comment>
            [3, 4, 3, 1, 1],  # def + test + int + '=' + 0
            [14],  # <comment>
            [1, 13],  # '=' + "hello world"
            [1, 1, 3],  # '=' + '+' + 420
            [6],  # return
            [],
            [1, 1],  # '=' + 5
        ]

        def check():
            assert self.formatting_ranges == expected_format_ranges

        self.bot.waitUntil(check)

    def test_format_group(self):
        """Test the formatting rules exactly."""

        content = 'return 99 + my_var + str("1234")'
        self.text_edit.setPlainText(content)

        qt_styles = self.highlighter.formatter.qt_styles

        def breakup_qt_format(fmt):
            """QCharTextFormat instances cannot be well compared, break them up here."""
            return (
                fmt.foreground().color().name(),
                fmt.fontItalic(),
                fmt.fontWeight(),
            )

        expected_formats_raw = [
            ("return", qt_styles[Token.Keyword]),
            ("99", qt_styles[Token.Literal.Number.Integer]),
            ("+", qt_styles[Token.Operator]),
            ("+", qt_styles[Token.Operator]),
            ("str", qt_styles[Token.Name.Builtin]),
            ('"1234"', qt_styles[Token.Literal.String.Double]),
        ]
        expected_formats = [
            (txt, breakup_qt_format(style)) for txt, style in expected_formats_raw
        ]

        def check():
            layout = next(self.doc_layouts)
            actual_formats = [
                (
                    content[fmt.start : (fmt.start + fmt.length)],
                    breakup_qt_format(fmt.format),
                )
                for fmt in layout.formats()
            ]
            assert actual_formats == expected_formats

        self.bot.waitUntil(check)

    def test_no_highlighting(self):
        """Test the exception class."""

        message = "'happy' return to Python!"

        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        HighlightKind.PLAIN.add_as_user_data(cursor)
        cursor.insertText(message)

        def check_1():
            fmt_ranges = [len(layout.formats()) for layout in self.doc_layouts]
            assert fmt_ranges == [0]

        self.bot.waitUntil(check_1)

        self.text_edit.appendPlainText("print('Hello World!')")

        def check_2():
            fmt_counts = [len(layout.formats()) for layout in self.doc_layouts]
            assert fmt_counts == [0, 2]

        self.bot.waitUntil(check_2)

    def test_emojis(self):
        """Test formatting including multi-byte characters."""

        content = """
def my_func():
    var = "😎"
    return "Smiley: " + var"""
        self.text_edit.setPlainText(content)

        expected_format_ranges = [
            [],
            [3, 7],  # def + my_func
            [1, 3],  # '=' + string literal
            [6, 10, 1],  # return + string literal + '+'
        ]

        def check():
            assert self.formatting_ranges == expected_format_ranges

        self.bot.waitUntil(check)
