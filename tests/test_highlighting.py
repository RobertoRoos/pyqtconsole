from collections.abc import Generator

import pytest
from qtpy.QtWidgets import QPlainTextEdit
from qtpy.QtGui import QTextDocument, QTextLayout

from pyqtconsole.highlighter import PythonHighlighter

from utils import QtTestCase


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
        self.highlighter = PythonHighlighter(
            self.text_edit.document()
        )
        yield self.highlighter

    def get_doc_layouts(self) -> Generator[QTextLayout, None, None]:
        """The best way to retrieve formatting results.

        We retrieve layout blocks (typically one per line). Each layout consists
        for format ranges.
        """
        block = self.text_edit.document().firstBlock()
        while block.isValid():
            yield block.layout()
            block = block.next()

    def test_demo(self):
        """Small sample, mostly for manual testing."""

        self.text_edit.setPlainText("""# Leading comment
def test(my_arg: int = 0):
    # Some comment
    str_literal = "hello world"
    my_variable = my_arg + 420
    return my_variable

outcome = test(5)
        """)

        expected_format_ranges = [
            (17, ),  # <comment>
            (3, 4, 3, 1, 1), # def + test + int + '=' + 0
            (14, ),  # <comment>
            (1, 13),  # '=' + "hello world"
            (1, 1, 3),  # '=' + '+' + 420
            (6, ),  # return
            (),
            (1, 1),  # '=' + 5
            (),
        ]

        with self.bot.waitExposed(self.text_edit):
            pass

        def check():
            actual_ranges = [
                tuple(fmt_ranges.length for fmt_ranges in layout.formats())
                for layout in self.get_doc_layouts()
            ]
            assert actual_ranges == expected_format_ranges

        self.bot.waitUntil(check)
