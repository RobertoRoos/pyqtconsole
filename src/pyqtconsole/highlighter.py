import re
from collections.abc import Generator
from io import StringIO

from qtpy.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextBlockUserData,
    QTextCharFormat,
    QTextDocument,
)

from pygments import lex, highlight
from pygments.lexers import PythonLexer
from pygments.token import Token, _TokenType, string_to_tokentype
from pygments.formatter import Formatter
from typing import Any


QtStyleDict = dict[_TokenType, QTextCharFormat]


class NoHighlightData(QTextBlockUserData):
    """User data to mark blocks that should not be syntax highlighted."""
    pass


class QtFormatter(Formatter):
    """A custom Pygments formatter for Qt.

    We cannot rely on the `format()` callback as intended, so a custom callback
    is used that works better in Qt.
    """

    # PYGMENTS_STYLE_TO_QT = {
    #     "bold": fmt.setFontWeight(QFont.Bold),
    #     "nobold": fmt.setFontWeight(QFont.Normal),
    #     "italic": fmt.setFontItalic(True),
    #     "noitalic": fmt.setFontItalic(False),
    #     "underline": fmt.setFontUnderline(True),
    #     "nounderline": fmt.setFontUnderline(False),
    #     "bg": fmt.setBackground(QColor())
    # }

    def __init__(self, syntax_highlighter: "PythonHighlighter", **kwargs):
        super().__init__(**kwargs)
        self.highlighter = syntax_highlighter
        self.qt_styles: QtStyleDict = dict(self._make_styles())

    def _make_styles(self) -> Generator[tuple[_TokenType, QTextCharFormat], None, None]:
        """Convert standard Pygments style into one that's convenient for Qt."""
        token: _TokenType
        style: dict[str, Any]
        for token, style in self.style:
            if token is Token.Text.Whitespace:
                continue  # We won't bother explicitly marking all whitespace
            qt_style = self._make_qt_format_from_style(style)
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


def make_format(color: Any = None, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    """Factory function for a Qt text format."""
    fmt = QTextCharFormat()
    if color:
        fmt.setForeground(QColor(color))

    if bold:
        fmt.setFontWeight(QFont.Bold)

    if italic:
        fmt.setFontItalic(True)

    return fmt


# def format(color, style=""):
#     """Return a QTextCharFormat with the given attributes."""
#     _format = QTextCharFormat()
#     if color is not None:
#         _color = QColor(color)
#         _format.setForeground(_color)
#     if "bold" in style:
#         _format.setFontWeight(QFont.Bold)
#     if "italic" in style:
#         _format.setFontItalic(True)
#
#     return _format
#
#
# # Syntax styles that can be shared by all languages
# STYLES = {
#     "keyword": format("blue", "bold"),
#     "operator": format("red"),
#     "brace": format("darkGray"),
#     "defclass": format("black", "bold"),
#     "string": format("magenta"),
#     "string2": format("darkMagenta"),
#     "comment": format("darkGreen", "italic"),
#     "self": format("black", "italic"),
#     "numbers": format("brown"),
#     "inprompt": format("darkBlue", "bold"),
#     "outprompt": format("darkRed", "bold"),
#     "fstring": format("darkCyan", "bold"),
#     "escape": format("darkorange", "bold"),
#     "shellcmd": format(None, "bold"),
# }


# Custom Tokens for our input and output prompts:
TokenInPrompt = string_to_tokentype("Token.Generic.InPrompt")
TokenOutPrompt = string_to_tokentype("Token.Generic.OutPrompt")


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the Python language, through Pygments."""

    STYLES: QtStyleDict = {}  # Static property for default pygment styles

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self.lexer = PythonLexer()
        self.formatter = QtFormatter(self)

        if not self.STYLES:
            self.STYLES = self._create_styles()

    @staticmethod
    def _create_styles() -> QtStyleDict:
        """Create a formatting look-up.

        The result is a dictionary mapping Pygments tokens to QT formatting options.
        """
        return {}

    def highlightBlock(self, text: str) -> None:
        """Callback from QSyntextHighlighter to format some text."""

        for idx, token_type, content in self.lexer.get_tokens_unprocessed(text):
            self.formatter.format_highlighter(idx, token_type, content)
            pass

        # result = highlight(text, self.lexer, self.formatter)
        # pass

        # # Walk through all recognized tokens in the given text:
        # for token, content in lex(text, self.lexer):
        #     if fmt := self.formats.get(token):
        #         index = text.find(content)
        #         if index >= 0:
        #             self.setFormat(index, len(content), fmt)


class PromptHighlighter:
    """Custom highlighter for the prompt area (left-column)."""

    STYLES: QtStyleDict = {}  # Same as for `PythonHighlighter`

    def __init__(self, formats=None):
        self.styles = styles = dict(self.STYLES, **(formats or {}))
        self.rules: dict[_TokenType, tuple[re.Pattern[str], int]] = {
            # Match the prompt numbering of a console:
            TokenInPrompt: (re.compile(r"IN[^:]*"), 0),
            TokenOutPrompt: (re.compile(r"OUT[^:]*"), 0),
            Token.Literal.Number: (re.compile(r"\b[+-]?[0-9]+\b"), 0),
        }  # Values are like: ( <regex>, <relevant match group> )

        if not self.STYLES:
            self.STYLES = self._create_style()

    @staticmethod
    def _create_style() -> QtStyleDict:
        return {
            TokenInPrompt: make_format("darkBlue", bold=True),
            TokenOutPrompt: make_format("darkRed", bold=True),
            Token.Literal.Number: make_format("brown"),
        }

    def highlight(self, text):
        for token_type, (expression, match_idx) in self.rules.items():
            fmt = self.STYLES[token_type]
            for m in expression.finditer(text):
                yield m.start(match_idx), m.end(match_idx) - m.start(match_idx), fmt

    # # Python keywords
    # keywords = keyword.kwlist
    #
    # def __init__(self, document, formats=None, shell_cmd_prefix=None):
    #     """Initialize the syntax highlighter.
    #
    #     :param document: The doc to apply syntax highlighting to
    #     :type document: QTextDocument
    #     :param formats: Optional dict mapping style names to QTextCharFormat
    #                     objects
    #     :type formats: dict, None
    #     :param shell_cmd_prefix: Optional string prefix to identify shell
    #                              command lines
    #     :type shell_cmd_prefix: str, None
    #     """
    #     QSyntaxHighlighter.__init__(self, document)
    #
    #     self.styles = styles = dict(STYLES, **(formats or {}))
    #     self.shell_cmd_prefix = shell_cmd_prefix
    #
    #     # Multi-line strings (expression, flag, style)
    #     # FIXME: The triple-quotes in these two lines will mess up the
    #     # syntax highlighting from this point onward
    #     self.tri_single = (re.compile("'''"), 1, styles["string2"])
    #     self.tri_double = (re.compile('"""'), 2, styles["string2"])
    #
    #     rules = []
    #
    #     # Keyword, operator, and brace rules
    #     rules += [
    #         (rf"\b{w}\b", 0, styles["keyword"]) for w in PythonHighlighter.keywords
    #     ]
    #
    #     # All other rules
    #     rules += [
    #         # 'self'
    #         # (r'\bself\b', 0, STYLES['self']),
    #         # Double-quoted string, possibly containing escape sequences
    #         (r'"[^"\\]*(\\.[^"\\]*)*"', 0, styles["string"]),
    #         # Single-quoted string, possibly containing escape sequences
    #         (r"'[^'\\]*(\\.[^'\\]*)*'", 0, styles["string"]),
    #         # 'def' followed by an identifier
    #         (r"\bdef\b\s*(\w+)", 1, styles["defclass"]),
    #         # 'class' followed by an identifier
    #         (r"\bclass\b\s*(\w+)", 1, styles["defclass"]),
    #         # From '#' until a newline
    #         (r"#[^\n]*", 0, styles["comment"]),
    #         # Numeric literals
    #         (r"\b[+-]?[0-9]+[lL]?\b", 0, styles["numbers"]),
    #         (r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b", 0, styles["numbers"]),
    #         (r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b", 0, styles["numbers"]),
    #     ]
    #
    #     # Build a regex object for each pattern
    #     self.rules = [(re.compile(pat), index, fmt) for (pat, index, fmt) in rules]
    #
    #     self.fstring_pattern = re.compile(
    #         r"[fF][rR]?(['\"])([^'\"\\]*(\\.[^'\"\\]*)*?)\1"
    #     )
    #
    #     self.string_pattern = re.compile(r"(['\"])([^'\"\\]*(\\.[^'\"\\]*)*?)\1")
    #     self.escape_pattern = re.compile(
    #         r"\\(?:[\\\'\"\'abfnrtv0]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|"
    #         r"U[0-9a-fA-F]{8}|N\{[^}]+\}|[0-7]{1,3})"
    #     )
    #
    # def _to_utf16_offset(self, text, position):
    #     """Convert Python string position to UTF-16 offset for Qt.
    #
    #     Qt uses UTF-16 encoding internally, where some characters (like emoji)
    #     take 2 code units.
    #     This converts Python string indices to UTF-16 positions.
    #     """
    #     return len(text[:position].encode("utf-16-le")) // 2
    #
    # def highlightBlock(self, text):
    #     """Apply syntax highlighting to the given block of text."""
    #     # Skip highlighting if block is marked as no-highlight
    #     if isinstance(self.currentBlockUserData(), NoHighlightData):
    #         return
    #
    #     # Check if this is a shell command line
    #     if self.shell_cmd_prefix and text.lstrip().startswith(self.shell_cmd_prefix):
    #         # Highlight the entire line as a shell command
    #         start_utf16 = self._to_utf16_offset(text, 0)
    #         end_utf16 = self._to_utf16_offset(text, len(text))
    #         self.setFormat(
    #             start_utf16, end_utf16 - start_utf16, self.styles["shellcmd"]
    #         )
    #         self.setCurrentBlockState(0)
    #         return
    #
    #     s = self.styles["string"]
    #     # Find all positions inside strings (using Python string indices)
    #     string_positions = {
    #         pos
    #         for expression, nth, fmt in self.rules
    #         if fmt == s
    #         for m in expression.finditer(text)
    #         for pos in range(m.start(nth), m.end(nth))
    #     }
    #
    #     # Apply formatting, skipping non-string rules inside strings
    #     for expression, nth, format in self.rules:
    #         for m in expression.finditer(text):
    #             # Skip non-string formatting if it's inside a string
    #             # Check using Python string index, not UTF-16 offset
    #             if format != s and m.start(nth) in string_positions:
    #                 # Skip non-string formatting if it's inside a string
    #                 continue
    #             start_pos = self._to_utf16_offset(text, m.start(nth))
    #             end_pos = self._to_utf16_offset(text, m.end(nth))
    #             self.setFormat(start_pos, end_pos - start_pos, format)
    #
    #     # Highlight f-string interpolations
    #     self.highlight_fstring_interpolations(text)
    #
    #     # Highlight escape sequences in strings
    #     self.highlight_escape_sequences(text)
    #
    #     self.setCurrentBlockState(0)
    #
    #     # Do multi-line strings
    #     in_multiline = self.match_multiline(text, *self.tri_single)
    #     if not in_multiline:
    #         in_multiline = self.match_multiline(text, *self.tri_double)
    #
    # def match_multiline(self, text, delimiter, in_state, style):
    #     """Do highlighting of multi-line strings. ``delimiter`` should be a
    #     ``re.Pattern`` for triple-single-quotes or triple-double-quotes, and
    #     ``in_state`` should be a unique integer to represent the corresponding
    #     state changes when inside those strings. Returns True if we're still
    #     inside a multi-line string when this function is finished.
    #     """
    #     # If inside triple-single quotes, start at 0
    #     if self.previousBlockState() == in_state:
    #         start = 0
    #         add = 0
    #     # Otherwise, look for the delimiter on this line
    #     else:
    #         m = delimiter.search(text)
    #         if m:
    #             start = m.start()
    #             # Move past this match
    #             add = m.end() - m.start()
    #         else:
    #             start = -1
    #             add = -1
    #
    #     # As long as there's a delimiter match on this line...
    #     while start >= 0:
    #         # Look for the ending delimiter
    #         m = delimiter.search(text, start + add)
    #         # Ending delimiter on this line?
    #         if m and (m.start() >= add):
    #             # length = end - start + add + m.end() - m.start()
    #             length = add + m.end() - start
    #             self.setCurrentBlockState(0)
    #         # No; multi-line string
    #         else:
    #             self.setCurrentBlockState(in_state)
    #             length = len(text) - start + add
    #         # Apply formatting - convert to UTF-16 positions
    #         start_utf16 = self._to_utf16_offset(text, start)
    #         end_utf16 = self._to_utf16_offset(text, start + length)
    #         self.setFormat(start_utf16, end_utf16 - start_utf16, style)
    #         # Look for the next match
    #         m = delimiter.search(text, start + length)
    #         if m:
    #             start = m.start()
    #         else:
    #             break
    #
    #     # Return True if still inside a multi-line string, False otherwise
    #     return self.currentBlockState() == in_state
    #
    # def highlight_fstring_interpolations(self, text):
    #     """Highlight f-string interpolations (the {} parts)."""
    #     for m in self.fstring_pattern.finditer(text):
    #         string_content = m.group(2)
    #         ln = len(string_content)
    #         content_start = m.start(2)
    #
    #         i = 0
    #         while i < ln:
    #             if string_content[i] == "{":
    #                 # Skip escaped braces {{
    #                 if i + 1 < ln and string_content[i + 1] == "{":
    #                     i += 2
    #                     continue
    #
    #                 # Find matching closing brace
    #                 brace_count = 1
    #                 j = i + 1
    #                 while j < ln and brace_count > 0:
    #                     if string_content[j : j + 2] == "}}":
    #                         j += 2  # Skip escaped }}
    #                     elif string_content[j] == "{":
    #                         brace_count += 1
    #                         j += 1
    #                     elif string_content[j] == "}":
    #                         brace_count -= 1
    #                         j += 1
    #                     else:
    #                         j += 1
    #
    #                 if brace_count == 0:
    #                     start_utf16 = self._to_utf16_offset(text, content_start + i)
    #                     end_utf16 = self._to_utf16_offset(text, content_start + j)
    #                     self.setFormat(
    #                         start_utf16, end_utf16 - start_utf16, self.styles["fstring"]
    #                     )
    #                     i = j
    #                 else:
    #                     i += 1
    #             else:
    #                 i += 1
    #
    # def highlight_escape_sequences(self, text):
    #     """Highlight escape sequences in strings."""
    #     for m in self.string_pattern.finditer(text):
    #         content_start = m.start(2)
    #         for esc in self.escape_pattern.finditer(m.group(2)):
    #             start_utf16 = self._to_utf16_offset(text, content_start + esc.start())
    #             end_utf16 = self._to_utf16_offset(text, content_start + esc.end())
    #             self.setFormat(
    #                 start_utf16, end_utf16 - start_utf16, self.styles["escape"]
    #             )
