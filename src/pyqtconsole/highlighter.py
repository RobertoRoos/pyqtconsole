import re
from collections.abc import Generator
from enum import Enum
from typing import Any

from pygments.formatter import Formatter
from pygments.lexers import PythonLexer
from pygments.style import StyleMeta
from pygments.token import Token, _TokenType, string_to_tokentype
from qtpy.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextBlockUserData,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)

StyleDict = dict[_TokenType, Any]
QtStyleDict = dict[_TokenType, QTextCharFormat]


class HighlightKind(Enum):
    """Mark text for the highlighter in a particular way."""

    REGULAR = 0
    PLAIN = 1
    ERROR = 2

    @property
    def user_data(self) -> "HighlightUserData":
        """Make instance of custom userdata from this enum."""
        return HighlightUserData(self)

    def add_as_user_data(self, cursor: QTextCursor) -> None:
        """Insert an instance of this user-data into a cursor."""
        cursor.block().setUserData(self.user_data)


class HighlightUserData(QTextBlockUserData):
    """Custom text meta-data for QSyntaxHighlighter."""

    def __init__(self, kind: HighlightKind):
        super().__init__()
        self.kind = kind


class QtFormatter(Formatter):
    """A custom Pygments formatter for Qt.

    In the Pygments context a formatter handles the conversion of a token stream
    into formatted text.

    We cannot rely on the `format()` callback as intended, so a custom callback
    is used that works better in Qt.
    """

    def __init__(self, syntax_highlighter: "PythonHighlighter", **kwargs):
        if kwargs.get("style", False) is None:
            kwargs.pop("style")  # style=None breaks the parent constructor

        super().__init__(**kwargs)
        self.highlighter = syntax_highlighter
        self.qt_styles: QtStyleDict = dict(self.make_qt_styles(self.style))

    @classmethod
    def make_qt_styles(
        cls, styles_class: StyleMeta
    ) -> Generator[tuple[_TokenType, QTextCharFormat], None, None]:
        """Convert standard Pygments style into one that's convenient for Qt.

        `self.style` is a `StyleMeta`, the default style object.
        Instead of composing Qt-styles on the fly, we create a look-up table only once.
        """
        token: _TokenType
        style: dict[str, Any]
        for token, style in styles_class:
            if token is Token.Text.Whitespace:
                continue  # We won't bother explicitly marking all whitespace
            qt_style = cls._make_qt_format_from_style(style)
            if qt_style is None:
                continue
            yield token, qt_style

    @staticmethod
    def _make_qt_format_from_style(style: dict[str, Any]) -> QTextCharFormat | None:
        """Convert an individual Pygments style rule into something for Qt.

        In case the style is entirely default, it's easier to just use no style at all,
        so then `None` is returned.
        """
        fmt = QTextCharFormat()

        is_default = True

        if style.get("bold"):
            fmt.setFontWeight(QFont.Bold)
            is_default = False

        if style.get("nobold"):
            fmt.setFontWeight(QFont.Normal)
            is_default = False

        if style.get("italic"):
            fmt.setFontItalic(True)
            is_default = False

        if style.get("noitalic"):
            fmt.setFontItalic(False)
            is_default = False

        if style.get("underline"):
            fmt.setFontUnderline(True)
            is_default = False

        if style.get("nounderline"):
            fmt.setFontUnderline(False)
            is_default = False

        if (color := style.get("color")) is not None:
            q_color = QColor("#" + color)
            fmt.setForeground(q_color)
            is_default = False

        if is_default:
            return None

        return fmt

    def format(self, *_args):
        """Default callback for a formatter, but it won't work with us."""
        msg = "Cannot format in the normal way, use `format_highlighter` instead."
        raise NotImplementedError(msg)

    def format_highlighter(
        self,
        idx: int,
        token_type: _TokenType,
        content: str,
    ) -> None:
        """Format a lexer result.

        Normally you would return a formatted string or write into the output file,
        e.g. for HTML you would get things like `<i>example</i>`. But for Qt we rely on
        a syntax highlighter class, so instead we use those methods.
        """
        # If the token type doesn't exist in the style-map we try it with the parent
        # of the token type (e.g. parent of `Token.Literal.String.Double` is
        # `Token.Literal.String`)
        while token_type not in self.qt_styles:
            token_type = token_type.parent
            if token_type is None:
                return  # We don't recognize this type, just quietly let it slide

        if fmt := self.qt_styles.get(token_type):
            self.highlighter.setFormat(idx, len(content), fmt)


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the Python language, through Pygments.

    The heavy lifting is done by the sister class, `QtFormatter`.
    """

    def __init__(self, document: QTextDocument, **kwargs):
        super().__init__(document)
        self.lexer = PythonLexer()
        self.formatter = QtFormatter(self, **kwargs)

    def highlightBlock(self, text: str) -> None:
        """Callback from QSyntextHighlighter to format some text."""
        if (
            isinstance(user_data := self.currentBlockUserData(), HighlightUserData)
            and user_data.kind == HighlightKind.PLAIN
        ):
            return  # No formatting at all here

        # We rely on `get_tokens_unprocessed()`, because that one also passes along
        # the string position, unlike the intended entrypoint `pygments.highlight()`.
        for idx, token_type, content in self.lexer.get_tokens_unprocessed(text):
            self.formatter.format_highlighter(idx, token_type, content)


# Custom Tokens for our input and output prompts:
TokenInPrompt = string_to_tokentype("Token.Generic.InPrompt")
TokenOutPrompt = string_to_tokentype("Token.Generic.OutPrompt")


class PromptHighlighter:
    """Custom highlighter for the prompt area (left-column).

    This has no real ties to Pygments, though we use their token classes for symmetry.
    """

    STYLE = {}

    def __init__(self):
        self.rules: dict[_TokenType, tuple[re.Pattern[str], int]] = {
            # Match the prompt numbering of a console:
            TokenInPrompt: (re.compile(r"IN[^:]*"), 0),
            TokenOutPrompt: (re.compile(r"OUT[^:]*"), 0),
            Token.Literal.Number: (re.compile(r"\b[+-]?[0-9]+\b"), 0),
        }  # Values are like: ( <regex>, <relevant match group> )

        if not self.STYLE:
            self.STYLE = self._create_style()

    def highlight(self, text):
        for token_type, (expression, match_idx) in self.rules.items():
            fmt = self.STYLE[token_type]
            for m in expression.finditer(text):
                yield m.start(match_idx), m.end(match_idx) - m.start(match_idx), fmt

    @classmethod
    def _create_style(cls):
        return {
            TokenInPrompt: cls.make_format("darkBlue", bold=True),
            TokenOutPrompt: cls.make_format("darkRed", bold=True),
            Token.Literal.Number: cls.make_format("brown"),
        }

    @staticmethod
    def make_format(
        color: Any = None, bold: bool = False, italic: bool = False
    ) -> QTextCharFormat:
        """Factory function for a Qt text format."""
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))

        if bold:
            fmt.setFontWeight(QFont.Bold)

        if italic:
            fmt.setFontItalic(True)

        return fmt
