"""Parser: converts tokens into an expression tree."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .scanner import Token, TokenType, scan
from .types import TYPE_MAP, DEFAULT_TYPE


class ParseError(Exception):
    """Error raised when parsing a SQL template fails."""

    pass


@dataclass(slots=True)
class Expression:
    """Node in the expression tree built from a parsed SQL template.

    Attributes:
        start_token_index: Index of the first token belonging to this expression.
        stop_token_index: Index one past the last token belonging to this expression.
        optional: Whether this expression is inside optional brackets ``[...]``.
        alternative: Whether this is an alternative section (optional with
            sub-expressions but no direct required variables).
        combiner: Whether this is a combiner section (e.g. ``[AND]``).
        stop_combiner: Whether this expression resets the combiner flag.
        sub_expressions: Child expressions nested inside this one.
        required_input_vars: Bitmask of input variable indices required by
            this expression (up to 64 bits).
    """

    start_token_index: int
    stop_token_index: int
    optional: bool = False
    alternative: bool = False
    combiner: bool = False
    stop_combiner: bool = False
    sub_expressions: list = field(default_factory=list)
    required_input_vars: int = 0  # bitmask, up to 64 bits

    def set_required_input_var(self, idx: int) -> None:
        """Set the bit for input variable *idx* in the required bitmask.

        Args:
            idx: Zero-based index of the input variable.
        """
        self.required_input_vars |= 1 << idx

    def close_expression(self, stop_token_index: int, tokens: list[Token]) -> None:
        """Finalize this expression after all its tokens have been consumed.

        Determines whether this expression is alternative, combiner, or
        stop-combiner based on its structure, and propagates required
        input variable bitmasks to sub-expressions.

        Args:
            stop_token_index: Token index of the closing bracket (or end
                of token list for the root expression).
            tokens: The full list of tokens from the scanner.
        """
        self.stop_token_index = stop_token_index
        if self.optional:
            if self.required_input_vars == 0 and len(self.sub_expressions) > 0:
                self.alternative = True
            elif self.required_input_vars == 0 and len(self.sub_expressions) == 0:
                # Check if this is a stop-combiner: [<empty_literal>]
                if self.start_token_index + 2 >= self.stop_token_index:
                    prev = stop_token_index - 1
                    if 0 <= prev < len(tokens):
                        t = tokens[prev]
                        if t.type == TokenType.LITERAL and t.value == "":
                            self.stop_combiner = True
                self.combiner = True
                return

        # Propagate required_input_vars for alternative expressions; assign combiner deps
        for i, sub in enumerate(self.sub_expressions):
            if sub.required_input_vars != 0:
                if self.alternative:
                    self.required_input_vars |= sub.required_input_vars
                continue
            if sub.combiner and i < len(self.sub_expressions) - 1:
                sub.required_input_vars |= self.sub_expressions[i + 1].required_input_vars


_STATEMENT_RE = re.compile(
    r"^([0-9a-zA-Z_]+):=(.*?);[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


class Parser:
    """Parses a SQL template string into tokens and an expression tree.

    After calling :meth:`parse`, the following attributes are populated:

    Attributes:
        tokens: List of scanned tokens.
        expressions: All expression nodes (root at index 0).
        input_vars: Ordered list of unique input variable tokens.
        output_vars: List of output (``@``) variable tokens.
    """

    def __init__(self) -> None:
        """Initialize the parser with empty state."""
        self.tokens: list[Token] = []
        self.expressions: list[Expression] = []
        self.input_vars: list[Token] = []  # ordered, unique by name
        self._input_var_indices: dict[str, int] = {}
        self.output_vars: list[Token] = []

    # ------------------------------------------------------------------
    def parse(self, stmt_str: str) -> None:
        """Parse a single statement body into tokens and an expression tree.

        The statement body is the text between ``:=`` and ``;`` in the
        template source file.

        Args:
            stmt_str: The SQL template body to parse.

        Raises:
            ParseError: If the template contains type mismatches, unknown
                output types, or more than 64 distinct input variables.
        """
        self.tokens = scan(stmt_str)
        self.expressions = []
        self.input_vars = []
        self._input_var_indices = {}
        self.output_vars = []

        root = Expression(start_token_index=0, stop_token_index=0, optional=False)
        stack: list[Expression] = [root]
        self.expressions.append(root)

        for i, tok in enumerate(self.tokens):
            tt = tok.type
            if tt == TokenType.LITERAL:
                continue

            elif tt in (TokenType.ESCAPED_VAR, TokenType.LITERAL_VAR, TokenType.OPTION_VAR):
                idx = self._input_var_indices.get(tok.value)
                if idx is None:
                    idx = len(self.input_vars)
                    self._input_var_indices[tok.value] = idx
                    self.input_vars.append(tok)
                else:
                    existing = self.input_vars[idx]
                    if existing.vartype != tok.vartype:
                        raise ParseError(
                            f"Input variable '{tok.value}' used with differing types: "
                            f"'{existing.vartype}' vs '{tok.vartype}'"
                        )
                self._require_input_var(stack, idx)

            elif tt == TokenType.TARGET_VAR:
                if tok.vartype not in TYPE_MAP:
                    raise ParseError(
                        f"Output variable '{tok.value}' has unknown type '{tok.vartype}'"
                    )
                self.output_vars.append(tok)

            elif tt == TokenType.OPEN_BRACKET:
                exp = Expression(start_token_index=i, stop_token_index=i, optional=True)
                stack[-1].sub_expressions.append(exp)
                stack.append(exp)
                self.expressions.append(exp)

            elif tt == TokenType.CLOSE_BRACKET:
                closed = stack.pop()
                closed.close_expression(i, self.tokens)

            elif tt == TokenType.REQUIRED_OPEN_BRACKET:
                pass  # ignored

            elif tt == TokenType.REQUIRED_CLOSE_BRACKET:
                exp = Expression(
                    start_token_index=i,
                    stop_token_index=i,
                    optional=False,
                    stop_combiner=True,
                )
                stack[-1].sub_expressions.append(exp)
                # Note: NOT pushed onto stack

        # Close root expression
        root.close_expression(len(self.tokens), self.tokens)

        if len(self.input_vars) > 64:
            raise ParseError("More than 64 distinct input variables are not allowed.")

    # ------------------------------------------------------------------
    @staticmethod
    def _require_input_var(stack: list[Expression], idx: int) -> None:
        """Walk up the stack and set bit for idx, stopping at first optional."""
        for e in reversed(stack):
            e.set_required_input_var(idx)
            if e.optional:
                return

    # ------------------------------------------------------------------
    @staticmethod
    def extract_statements(source: str) -> list[tuple[str, str]]:
        """Extract named statements from a full ``.sqlg`` source file.

        Args:
            source: The entire contents of a ``.sqlg`` file.

        Returns:
            A list of ``(name, body)`` tuples for each statement found.
        """
        return [
            (m.group(1), m.group(2).strip())
            for m in _STATEMENT_RE.finditer(source)
        ]
