"""SQL builder: evaluates an expression tree with given parameters to produce SQL."""

from __future__ import annotations

from .scanner import Token, TokenType
from .parser import Expression
from .dialect import SQLDialect


class SQLBuilder:
    """Builds a SQL string from a parsed template and a dict of parameter values."""

    def __init__(
        self,
        tokens: list[Token],
        expressions: list[Expression],
        input_vars: list[Token],
        dialect: SQLDialect | None = None,
    ) -> None:
        self.tokens = tokens
        self.expressions = expressions
        self.input_vars = input_vars
        self.dialect = dialect or SQLDialect()

    # ------------------------------------------------------------------
    def build(self, params: dict) -> str:
        """Build and return the SQL string for the given parameter dict."""
        available = self._calc_available(params)
        root = self.expressions[0]

        # Check that all required root-level vars are present
        if root.required_input_vars != 0:
            if (available & root.required_input_vars) != root.required_input_vars:
                missing = self._missing_var_names(available, root.required_input_vars)
                raise ValueError(f"Missing required arguments: {missing}")

        parts: list[str] = []
        combine = [False]
        self._build_expr(root, params, available, parts, combine, None, check_condition=False)
        return "".join(parts)

    # ------------------------------------------------------------------
    def _calc_available(self, params: dict) -> int:
        mask = 0
        for i, var in enumerate(self.input_vars):
            if params.get(var.value) is not None:
                mask |= 1 << i
        return mask

    def _missing_var_names(self, available: int, required: int) -> list[str]:
        missing = []
        for i, var in enumerate(self.input_vars):
            if (required & (1 << i)) and not (available & (1 << i)):
                missing.append(var.value)
        return missing

    # ------------------------------------------------------------------
    def _emit_tokens(
        self,
        start: int,
        stop: int,
        params: dict,
        parts: list[str],
    ) -> None:
        for idx in range(start, stop):
            tok = self.tokens[idx]
            tt = tok.type
            if tt == TokenType.LITERAL:
                if tok.value:
                    parts.append(tok.value)
            elif tt == TokenType.TARGET_VAR:
                if tok.value:
                    parts.append(tok.value)
            elif tt == TokenType.LITERAL_VAR:
                val = params.get(tok.value)
                parts.append("" if val is None else str(val))
            elif tt == TokenType.ESCAPED_VAR:
                val = params.get(tok.value)
                parts.append(self.dialect.escape_value(val))
            elif tt == TokenType.OPTION_VAR:
                pass  # no output

    # ------------------------------------------------------------------
    def _build_expr(
        self,
        expr: Expression,
        params: dict,
        available: int,
        parts: list[str],
        combine: list[bool],
        alt_flag: list[bool] | None,
        check_condition: bool,
    ) -> None:
        if expr.stop_combiner:
            combine[0] = False
            return

        if not expr.alternative and not expr.combiner:
            # Regular (possibly optional) expression
            should_include = True
            if check_condition and expr.optional:
                should_include = (
                    (available & expr.required_input_vars) == expr.required_input_vars
                )
            if should_include:
                if alt_flag is not None:
                    alt_flag[0] = True
                pos = expr.start_token_index
                for sub in expr.sub_expressions:
                    self._emit_tokens(pos, sub.start_token_index, params, parts)
                    self._build_expr(sub, params, available, parts, combine, alt_flag, True)
                    pos = sub.stop_token_index + 1
                self._emit_tokens(pos, expr.stop_token_index, params, parts)
                if not expr.combiner:
                    combine[0] = True

        elif expr.alternative:
            should_check = True
            if check_condition:
                should_check = (available & expr.required_input_vars) != 0
            if should_check:
                sub_parts: list[str] = []
                sub_alt = [False]
                sub_combine = [False]
                pos = expr.start_token_index
                for sub in expr.sub_expressions:
                    self._emit_tokens(pos, sub.start_token_index, params, sub_parts)
                    self._build_expr(sub, params, available, sub_parts, sub_combine, sub_alt, True)
                    pos = sub.stop_token_index + 1
                self._emit_tokens(pos, expr.stop_token_index, params, sub_parts)
                if sub_alt[0]:
                    if alt_flag is not None:
                        alt_flag[0] = True
                    parts.extend(sub_parts)
                    combine[0] = True

        elif expr.combiner:
            # Included only if the previous expression was included (combine flag)
            should_include = combine[0]
            if expr.required_input_vars != 0:
                should_include = should_include and (
                    (available & expr.required_input_vars) == expr.required_input_vars
                )
            if should_include:
                pos = expr.start_token_index
                for sub in expr.sub_expressions:
                    self._emit_tokens(pos, sub.start_token_index, params, parts)
                    self._build_expr(sub, params, available, parts, combine, alt_flag, True)
                    pos = sub.stop_token_index + 1
                self._emit_tokens(pos, expr.stop_token_index, params, parts)
                combine[0] = False
