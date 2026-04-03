from collections.abc import Generator

import pytest
from pytestqt.qtbot import QtBot
from qtpy.QtGui import QTextLayout


class QtTestCase:
    """A testcase base-class around a Qt-bot.

    This is a shared class so all tests can easily use it.
    """

    bot: QtBot

    @pytest.fixture(autouse=True)
    def _qt_bot(self, qtbot):
        """Automatically include qtbot for all test-methods."""
        self.bot = qtbot

    @staticmethod
    def get_doc_layouts(text_edit) -> Generator[QTextLayout, None, None]:
        """The best way to retrieve formatting results.

        We retrieve layout blocks (typically one per line). Each layout consists
        for format ranges.
        """
        block = text_edit.document().firstBlock()
        while block.isValid():
            yield block.layout()
            block = block.next()
