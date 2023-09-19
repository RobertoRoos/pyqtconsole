from qtpy.QtWidgets import QApplication
from pyqtconsole.console import PythonConsole


app = QApplication([])


def test_widget_application():
    """Try to create a PyQtConsole instance.

    No real asserts are done, this will mainly test rough compatibility with the
    installed QT platform.
    """
    console = PythonConsole()
    console.show()
    console.eval_in_thread()
