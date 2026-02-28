"""Tokenizer for the tamuno-sqlgen SQL template DSL."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Token types produced by the scanner.

    Attributes:
        LITERAL: Plain text.
        OPEN_BRACKET: Opening optional bracket ``[``.
        CLOSE_BRACKET: Closing optional bracket ``]``.
        REQUIRED_OPEN_BRACKET: Opening required bracket ``{``.
        REQUIRED_CLOSE_BRACKET: Closing required bracket ``}``.
        ESCAPED_VAR: Escaped input variable ``$name[:type]``.
        LITERAL_VAR: Literal input variable ``#name[:type]``.
        TARGET_VAR: Output/result variable ``@name[:type]``.
        OPTION_VAR: Option variable ``?name[:type]``.
    """

    LITERAL = auto()
    OPEN_BRACKET = auto()
    CLOSE_BRACKET = auto()
    REQUIRED_OPEN_BRACKET = auto()
    REQUIRED_CLOSE_BRACKET = auto()
    ESCAPED_VAR = auto()   # $name[:type]
    LITERAL_VAR = auto()   # #name[:type]
    TARGET_VAR = auto()    # @name[:type]
    OPTION_VAR = auto()    # ?name[:type]


@dataclass(slots=True)
class Token:
    """A single token produced by the scanner.

    Attributes:
        type: The token type.
        value: The token value (identifier name for variables, text for
            literals, bracket character for brackets).
        vartype: The DSL type name for variable tokens (default ``"String"``).
    """

    type: TokenType
    value: str
    vartype: str = "String"


_STOP_CHARS = frozenset("[]{}$#@?\"'\\")
_IDENT_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)

_VAR_PREFIX: dict[str, TokenType] = {
    "$": TokenType.ESCAPED_VAR,
    "#": TokenType.LITERAL_VAR,
    "@": TokenType.TARGET_VAR,
    "?": TokenType.OPTION_VAR,
}


class ScannerError(Exception):
    """Error raised when the scanner encounters invalid input."""

    def __init__(self, pos: int, message: str) -> None:
        """Initialize a ScannerError.

        Args:
            pos: Character position in the source where the error occurred.
            message: Human-readable description of the error.
        """
        super().__init__(f"Position {pos}: {message}")
        self.pos = pos


def scan(source: str) -> list[Token]:
    """Tokenize a SQL template string into a list of Tokens.

    Args:
        source: The SQL template string to tokenize.

    Returns:
        A list of Token objects representing the parsed template.

    Raises:
        ScannerError: If the source contains invalid syntax such as
            mismatched brackets or missing variable identifiers.
    """
    tokens: list[Token] = []
    bracket_stack: list[TokenType] = []
    pos = 0
    length = len(source)
    buf: list[str] = []
    in_quote = False
    quote_char = ""

    def flush_literal() -> None:
        tokens.append(Token(TokenType.LITERAL, "".join(buf)))
        buf.clear()

    while pos < length:
        ch = source[pos]

        # Escape character - advance by 2, appending the literal next char
        if ch == "\\":
            if pos + 1 < length:
                if in_quote:
                    buf.append("\\")
                buf.append(source[pos + 1])
            pos += 2
            continue

        # Inside a quoted string - pass through until closing quote
        if in_quote:
            if ch == quote_char:
                in_quote = False
            buf.append(ch)
            pos += 1
            continue

        # Start of a quoted string
        if ch in ("'", '"'):
            in_quote = True
            quote_char = ch
            buf.append(ch)
            pos += 1
            continue

        if ch not in _STOP_CHARS:
            buf.append(ch)
            pos += 1
            continue

        # Bracket or variable prefix found
        flush_literal()

        if ch == "[":
            tokens.append(Token(TokenType.OPEN_BRACKET, "["))
            bracket_stack.append(TokenType.OPEN_BRACKET)
            pos += 1
        elif ch == "]":
            tokens.append(Token(TokenType.CLOSE_BRACKET, "]"))
            if not bracket_stack or bracket_stack[-1] != TokenType.OPEN_BRACKET:
                raise ScannerError(pos, "Mismatched closing bracket ']'")
            bracket_stack.pop()
            pos += 1
        elif ch == "{":
            tokens.append(Token(TokenType.REQUIRED_OPEN_BRACKET, "{"))
            bracket_stack.append(TokenType.REQUIRED_OPEN_BRACKET)
            pos += 1
        elif ch == "}":
            tokens.append(Token(TokenType.REQUIRED_CLOSE_BRACKET, "}"))
            if not bracket_stack or bracket_stack[-1] != TokenType.REQUIRED_OPEN_BRACKET:
                raise ScannerError(pos, "Mismatched closing bracket '}'")
            bracket_stack.pop()
            pos += 1
        elif ch in _VAR_PREFIX:
            tok_type = _VAR_PREFIX[ch]
            pos += 1
            # consume identifier
            start = pos
            while pos < length and source[pos] in _IDENT_CHARS:
                pos += 1
            ident = source[start:pos]
            if not ident:
                raise ScannerError(pos - 1, f"Missing identifier after '{ch}'")
            # optional :type
            vartype = "String"
            if pos < length and source[pos] == ":":
                pos += 1
                tstart = pos
                while pos < length and source[pos] in _IDENT_CHARS:
                    pos += 1
                vartype = source[tstart:pos] or "String"
            tokens.append(Token(tok_type, ident, vartype))
        else:
            # Shouldn't happen, but advance
            buf.append(ch)
            pos += 1

    # Flush remaining literal
    flush_literal()

    if bracket_stack:
        raise ScannerError(length, f"{len(bracket_stack)} unclosed bracket(s)")

    return tokens
