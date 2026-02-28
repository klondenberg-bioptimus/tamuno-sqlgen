"""Tokenizer for the tamuno-sqlgen SQL template DSL."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
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
    type: TokenType
    value: str
    vartype: str = "String"


_STOP_CHARS = frozenset("[]{}$#@?\"'\\ ")
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
    def __init__(self, pos: int, message: str) -> None:
        super().__init__(f"Position {pos}: {message}")
        self.pos = pos


def scan(source: str) -> list[Token]:
    """Tokenize a SQL template string into a list of Tokens."""
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

        # Escape character
        if ch == "\\":
            if in_quote:
                buf.append("\\")
            if pos + 1 < length:
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
