import pytest
from pytestqt.qtbot import QtBot


class QtTestCase:
    """A testcase base-class around a Qt-bot.

    This is a shared class so all tests can easily use it.
    """

    bot: QtBot

    @pytest.fixture(autouse=True)
    def _qt_bot(self, qtbot):
        """Automatically include qtbot for all test-methods."""
        self.bot = qtbot
