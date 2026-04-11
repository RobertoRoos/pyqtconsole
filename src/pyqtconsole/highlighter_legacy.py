from warnings import warn

from pygments.style import Style
from pygments.token import Token
from qtpy.QtGui import QFont, QTextCharFormat

from pyqtconsole.prompt import TokenInPrompt, TokenOutPrompt


class OldPyqtconsoleStyle(Style):
    """The look of older pyqtconsole versions, but in the new Pygments datatype."""

    name = "old_pyqtconsole"

    styles = {
        Token.Keyword: "bold #0000ff",
        Token.Operator: "#ff0000",
        # Braces cannot be marked-up in pygments
        Token.Name: "bold #000000",
        Token.Literal.String: "#ff00ff",
        Token.Literal.String.Doc: "#8b008b",
        Token.Comment: "italic #006400",
        Token.Name.Builtin.Pseudo: "italic #000000",
        Token.Number: "#a52a2a",
        TokenInPrompt: "bold #00008b",
        TokenOutPrompt: "bold #8b0000",
        Token.Literal.String.Interpol: "bold #008b8b",
        Token.Literal.String.Escape: "bold #ff8c00",
        Token.Generic.Prompt: "bold",
    }


class FormatsStyleBase(Style):
    """Bridge for the legacy `formats` dict style.

    Use the static method to generate a new styles sub-class.
    """

    name = "formats_legacy"

    styles = {}

    @classmethod
    def create_from_formats(
        cls, formats: dict[str, QTextCharFormat], custom_name: str | None = None
    ) -> type[Style]:
        """Convert a formats dict into a Pygments style object."""

        this_styles = {
            ttype: qt_format_to_pygments(fmt)
            for token_name, fmt in formats.items()
            if (ttype := name_to_token(token_name)) is not None
        }

        # Programmatically create a sub-type:
        style_class = type(
            custom_name or "FormatsStyle", (cls,), {"styles": this_styles}
        )
        return style_class  # type: ignore


NAME_TO_TOKEN: dict[str, type[Token]] = {
    "keyword": Token.Keyword,
    "operator": Token.Operator,
    # "brace": ...,  # Braces cannot be marked-up in pygments
    "defclass": Token.Name,
    "string": Token.Literal.String,
    "string2": Token.Literal.String.Doc,
    "comment": Token.Comment,
    "self": Token.Name.Builtin.Pseudo,
    "numbers": Token.Number,
    "inprompt": TokenInPrompt,
    "outprompt": TokenOutPrompt,
    "fstring": Token.Literal.String.Interpol,
    "escape": Token.Literal.String.Escape,
    "shellcmd": Token.Generic.Prompt,
}  # Look-up from old custom pyqtconsole keywords to Pygments tokens


def name_to_token(name: str) -> type[Token]:
    """Take an old-style token name and turn it into a Pygments token."""
    try:
        return NAME_TO_TOKEN[name]
    except KeyError:
        msg = f"Cannot convert formats key `{name}` to something in Pygments"
        warn(msg, stacklevel=5)  # '5' points to the console constructor
        return None


def qt_format_to_pygments(fmt: QTextCharFormat) -> str | None:
    """Convert an old-style Qt format and turn into a Pygments rule."""
    result: list[str] = []

    if fmt.fontWeight() >= QFont.Bold:
        result.append("bold")

    if fmt.fontItalic():
        result.append("italic")

    result.append(fmt.foreground().color().name())

    return " ".join(result)
