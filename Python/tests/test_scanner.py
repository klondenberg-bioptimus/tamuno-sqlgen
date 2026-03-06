"""Tests for the scanner module."""

from __future__ import annotations

import pytest

from tamuno_sqlgen.scanner import scan, ScannerError, Token, TokenType


def test_scan_simple_literal():
    tokens = scan("SELECT * FROM users")
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.LITERAL
    assert tokens[0].value == "SELECT * FROM users"


def test_scan_target_var():
    tokens = scan("SELECT @user_id:int")
    assert any(
        t.type == TokenType.TARGET_VAR and t.value == "user_id" and t.vartype == "int"
        for t in tokens
    )


def test_scan_escaped_var():
    tokens = scan("WHERE name=$user_name")
    assert any(
        t.type == TokenType.ESCAPED_VAR and t.value == "user_name" for t in tokens
    )


def test_scan_literal_var():
    tokens = scan("FROM #table_name")
    assert any(
        t.type == TokenType.LITERAL_VAR and t.value == "table_name" for t in tokens
    )


def test_scan_option_var():
    tokens = scan("?limit:int")
    assert any(
        t.type == TokenType.OPTION_VAR and t.value == "limit" and t.vartype == "int"
        for t in tokens
    )


def test_scan_optional_section():
    tokens = scan("[WHERE x=$x]")
    types = [t.type for t in tokens]
    assert TokenType.OPEN_BRACKET in types
    assert TokenType.CLOSE_BRACKET in types
    assert TokenType.ESCAPED_VAR in types


def test_scan_required_bracket():
    tokens = scan("{reset}")
    types = [t.type for t in tokens]
    assert TokenType.REQUIRED_OPEN_BRACKET in types
    assert TokenType.REQUIRED_CLOSE_BRACKET in types


def test_scan_default_vartype_is_string():
    tokens = scan("$user_name")
    var_tokens = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
    assert var_tokens[0].vartype == "String"


def test_scan_no_parse_inside_single_quotes():
    tokens = scan("WHERE status='$not_a_var'")
    var_tokens = [
        t for t in tokens if t.type in (TokenType.ESCAPED_VAR, TokenType.LITERAL_VAR)
    ]
    assert len(var_tokens) == 0


def test_scan_no_parse_inside_double_quotes():
    tokens = scan('WHERE status="$not_a_var"')
    var_tokens = [
        t for t in tokens if t.type in (TokenType.ESCAPED_VAR, TokenType.LITERAL_VAR)
    ]
    assert len(var_tokens) == 0


def test_scan_escape_char():
    tokens = scan(r"SELECT \$not_a_var")
    assert all(t.type == TokenType.LITERAL for t in tokens)
    assert any("$not_a_var" in t.value for t in tokens)


def test_scan_mismatched_close_bracket():
    with pytest.raises(ScannerError):
        scan("SELECT * FROM users]")


def test_scan_unclosed_bracket():
    with pytest.raises(ScannerError):
        scan("[WHERE x=$x")


def test_scan_mismatched_curly_close():
    with pytest.raises(ScannerError):
        scan("SELECT * FROM users}")


def test_scan_multiple_vars():
    tokens = scan("$a:int AND $b:String AND @c:Date")
    types = [t.type for t in tokens]
    assert types.count(TokenType.ESCAPED_VAR) == 2
    assert types.count(TokenType.TARGET_VAR) == 1


def test_scan_missing_identifier_raises():
    with pytest.raises(ScannerError):
        scan("WHERE $")


def test_scan_complex_template():
    source = (
        "SELECT @user_id:int, @user_name:String FROM users"
        " [ WHERE [user_name=$user_name] [AND] [active=$active:int] ] LIMIT 1"
    )
    tokens = scan(source)
    target_vars = [t for t in tokens if t.type == TokenType.TARGET_VAR]
    escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
    open_brackets = [t for t in tokens if t.type == TokenType.OPEN_BRACKET]
    assert len(target_vars) == 2
    assert len(escaped_vars) == 2
    # outer WHERE bracket + user_name + AND + active = 4
    assert len(open_brackets) == 4


# ==================== Complex scanning tests ====================


class TestScanMultiTableJoin:
    """Scanning templates with JOIN syntax and many variables."""

    def test_scan_join_with_multiple_target_and_escaped_vars(self):
        source = (
            "SELECT @order_id:int, @customer_name:String, @product_name:String, "
            "@quantity:int, @unit_price:double, @order_date:Date "
            "FROM orders o "
            "JOIN customers c ON o.customer_id = c.customer_id "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "JOIN products p ON oi.product_id = p.product_id "
            "[ WHERE "
            "[c.customer_name=$customer_name] [AND] "
            "[p.category=$category] [AND] "
            "[o.order_date >= $date_from:Date] [AND] "
            "[o.order_date <= $date_to:Date] [AND] "
            "[o.status=$status] ]"
        )
        tokens = scan(source)
        target_vars = [t for t in tokens if t.type == TokenType.TARGET_VAR]
        escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        assert len(target_vars) == 6
        assert len(escaped_vars) == 5

    def test_scan_join_preserves_on_clauses_as_literals(self):
        source = "SELECT @id:int FROM t1 JOIN t2 ON t1.id = t2.fk_id WHERE t1.x=$x"
        tokens = scan(source)
        literals = [t for t in tokens if t.type == TokenType.LITERAL]
        combined = "".join(t.value for t in literals)
        assert "JOIN t2 ON t1.id = t2.fk_id" in combined

    def test_scan_many_different_var_types(self):
        source = (
            "SELECT @a:int, @b:String, @c:Date, @d:double, @e:Timestamp, @f:boolean "
            "FROM t WHERE x=$x:int AND y=$y:double AND z=$z:Date"
        )
        tokens = scan(source)
        target_vars = [t for t in tokens if t.type == TokenType.TARGET_VAR]
        escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        assert len(target_vars) == 6
        assert {v.vartype for v in target_vars} == {
            "int",
            "String",
            "Date",
            "double",
            "Timestamp",
            "boolean",
        }
        assert len(escaped_vars) == 3
        assert {v.vartype for v in escaped_vars} == {"int", "double", "Date"}


class TestScanDeeplyNested:
    """Scanning deeply nested optional bracket structures."""

    def test_scan_three_levels_nested(self):
        source = "[ [ [x=$x] ] ]"
        tokens = scan(source)
        opens = [t for t in tokens if t.type == TokenType.OPEN_BRACKET]
        closes = [t for t in tokens if t.type == TokenType.CLOSE_BRACKET]
        assert len(opens) == 3
        assert len(closes) == 3

    def test_scan_five_optional_sections_in_sequence(self):
        source = "[a=$a] [AND] [b=$b] [AND] [c=$c] [AND] [d=$d] [AND] [e=$e]"
        tokens = scan(source)
        opens = [t for t in tokens if t.type == TokenType.OPEN_BRACKET]
        escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        assert len(opens) == 9  # 5 value sections + 4 AND sections
        assert len(escaped_vars) == 5

    def test_scan_nested_alternative_with_combiners(self):
        source = (
            "[ WHERE [a=$a] [AND] [b=$b:int] [AND] [c=$c:double] [AND] [d=$d:Date] ]"
        )
        tokens = scan(source)
        escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        names = [v.value for v in escaped_vars]
        assert names == ["a", "b", "c", "d"]
        types_list = [v.vartype for v in escaped_vars]
        assert types_list == ["String", "int", "double", "Date"]


class TestScanLiteralVariables:
    """Scanning literal variables (# prefix) for dynamic SQL parts."""

    def test_scan_literal_var_for_table_name(self):
        source = "SELECT @id:int FROM #table_name WHERE id=$id:int"
        tokens = scan(source)
        literal_vars = [t for t in tokens if t.type == TokenType.LITERAL_VAR]
        assert len(literal_vars) == 1
        assert literal_vars[0].value == "table_name"

    def test_scan_multiple_literal_vars(self):
        source = (
            "ORDER BY #sort_column #sort_direction LIMIT #page_size OFFSET #page_offset"
        )
        tokens = scan(source)
        literal_vars = [t for t in tokens if t.type == TokenType.LITERAL_VAR]
        assert len(literal_vars) == 4
        names = [v.value for v in literal_vars]
        assert names == ["sort_column", "sort_direction", "page_size", "page_offset"]

    def test_scan_literal_and_escaped_mixed(self):
        source = "INSERT INTO #target (col) SELECT col FROM src WHERE status=$status"
        tokens = scan(source)
        literal_vars = [t for t in tokens if t.type == TokenType.LITERAL_VAR]
        escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        assert len(literal_vars) == 1
        assert literal_vars[0].value == "target"
        assert len(escaped_vars) == 1
        assert escaped_vars[0].value == "status"


class TestScanOptionVariables:
    """Scanning option (?) variables."""

    def test_scan_option_var_at_end(self):
        source = "INSERT INTO t (a) VALUES ($a) ?batch_id:String"
        tokens = scan(source)
        option_vars = [t for t in tokens if t.type == TokenType.OPTION_VAR]
        assert len(option_vars) == 1
        assert option_vars[0].value == "batch_id"
        assert option_vars[0].vartype == "String"

    def test_scan_option_var_does_not_interfere_with_other_vars(self):
        source = "SELECT @id:int FROM t WHERE x=$x ?meta:int"
        tokens = scan(source)
        target_vars = [t for t in tokens if t.type == TokenType.TARGET_VAR]
        escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        option_vars = [t for t in tokens if t.type == TokenType.OPTION_VAR]
        assert len(target_vars) == 1
        assert len(escaped_vars) == 1
        assert len(option_vars) == 1


class TestScanStopCombiner:
    """Scanning stop-combiner ({}) syntax."""

    def test_scan_stop_combiner_tokens(self):
        source = "[x=$x] [AND] {} [y=$y:int]"
        tokens = scan(source)
        required_opens = [
            t for t in tokens if t.type == TokenType.REQUIRED_OPEN_BRACKET
        ]
        required_closes = [
            t for t in tokens if t.type == TokenType.REQUIRED_CLOSE_BRACKET
        ]
        assert len(required_opens) == 1
        assert len(required_closes) == 1

    def test_scan_multiple_stop_combiners(self):
        source = "[a=$a] {} [AND b=$b] {} [AND c=$c]"
        tokens = scan(source)
        required_opens = [
            t for t in tokens if t.type == TokenType.REQUIRED_OPEN_BRACKET
        ]
        assert len(required_opens) == 2


class TestScanEdgeCases:
    """Edge cases in scanning."""

    def test_scan_escaped_bracket_in_literal(self):
        tokens = scan(r"SELECT '\[not a bracket\]' FROM t")
        # The escaped brackets should become part of a literal token
        assert all(t.type == TokenType.LITERAL for t in tokens)

    def test_scan_empty_string(self):
        tokens = scan("")
        # Scanner returns a single empty literal token for empty input
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LITERAL
        assert tokens[0].value == ""

    def test_scan_only_whitespace(self):
        tokens = scan("   \n\t  ")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LITERAL

    def test_scan_var_immediately_after_var(self):
        """Two vars with no whitespace between them (unusual but valid)."""
        tokens = scan("$a$b")
        escaped = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        assert len(escaped) == 2
        assert escaped[0].value == "a"
        assert escaped[1].value == "b"

    def test_scan_quoted_string_with_nested_quotes(self):
        """Quoted strings should not be parsed even with special chars inside."""
        tokens = scan("WHERE x='$not_var [not_bracket] @not_target #not_literal'")
        escaped = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        literal_vars = [t for t in tokens if t.type == TokenType.LITERAL_VAR]
        target_vars = [t for t in tokens if t.type == TokenType.TARGET_VAR]
        assert len(escaped) == 0
        assert len(literal_vars) == 0
        assert len(target_vars) == 0

    def test_scan_subquery_in_from_clause(self):
        """Subquery text should scan without error -- parentheses are just literals."""
        source = (
            "SELECT @id:int FROM (SELECT id FROM t WHERE active=1) sub "
            "WHERE sub.id=$id:int"
        )
        tokens = scan(source)
        escaped = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        target = [t for t in tokens if t.type == TokenType.TARGET_VAR]
        assert len(escaped) == 1
        assert len(target) == 1

    def test_scan_aggregate_functions_in_literals(self):
        """Aggregate functions like COUNT(*), SUM(), AVG() are just literal text."""
        source = (
            "SELECT @cat:String, COUNT(*) as @cnt:int, SUM(price) as @total:double "
            "FROM products GROUP BY category"
        )
        tokens = scan(source)
        target_vars = [t for t in tokens if t.type == TokenType.TARGET_VAR]
        assert len(target_vars) == 3
        names = [v.value for v in target_vars]
        assert "cat" in names
        assert "cnt" in names
        assert "total" in names


# ==================== Escape character tests ====================


class TestScanEscapeCharacter:
    """Comprehensive tests for the backslash escape character."""

    # --- Escaping each special character individually ---

    def test_escape_dollar(self):
        """\\$ produces literal $ instead of starting a variable."""
        tokens = scan("SELECT \\$price FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "$price" in combined

    def test_escape_hash(self):
        """\\# produces literal # instead of starting a literal variable."""
        tokens = scan("SELECT \\#channel FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "#channel" in combined

    def test_escape_at(self):
        """\\@ produces literal @ instead of starting a target variable."""
        tokens = scan("SELECT \\@mention FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "@mention" in combined

    def test_escape_question_mark(self):
        """\\? produces literal ? instead of starting an option variable."""
        tokens = scan("SELECT \\?placeholder FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "?placeholder" in combined

    def test_escape_open_bracket(self):
        """\\[ produces literal [ instead of opening an optional section."""
        tokens = scan("SELECT \\[col\\] FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "[col]" in combined

    def test_escape_close_bracket(self):
        """\\] produces literal ] without requiring a matching open bracket."""
        tokens = scan("SELECT x\\] FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "x]" in combined

    def test_escape_open_brace(self):
        """\\{ produces literal { instead of opening a required bracket."""
        tokens = scan("SELECT \\{json\\} FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "{json}" in combined

    def test_escape_close_brace(self):
        """\\} produces literal } without requiring a matching open brace."""
        tokens = scan("SELECT x\\} FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "x}" in combined

    # --- Escaping the backslash itself ---

    def test_escape_backslash(self):
        """Double backslash produces a single literal backslash."""
        tokens = scan("a\\\\b")
        combined = "".join(t.value for t in tokens)
        assert combined == "a\\b"

    def test_double_backslash_followed_by_variable(self):
        """\\\\$var: first \\\\ produces literal \\, then $var is a variable."""
        tokens = scan("\\\\$var")
        literals = [t for t in tokens if t.type == TokenType.LITERAL]
        variables = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        assert any("\\" in t.value for t in literals)
        assert len(variables) == 1
        assert variables[0].value == "var"

    def test_triple_backslash_before_dollar(self):
        """\\\\\\$ = escaped backslash (\\\\) + escaped dollar (\\$) -> literal \\$."""
        tokens = scan("\\\\\\$var")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert combined == "\\$var"

    # --- Escaping inside and outside quoted strings ---

    def test_backslash_inside_single_quotes_preserved(self):
        """Inside single quotes, backslash is preserved along with the next char."""
        tokens = scan("WHERE x='a\\'s'")
        combined = "".join(t.value for t in tokens)
        # The backslash and the quote are both in the output
        assert "a\\'" in combined

    def test_backslash_inside_double_quotes_preserved(self):
        """Inside double quotes, backslash is preserved along with the next char."""
        tokens = scan('WHERE x="a\\\\"')
        combined = "".join(t.value for t in tokens)
        assert "a\\\\" in combined

    def test_special_chars_inside_quotes_not_parsed(self):
        """$, #, @, ?, [, ], {, } inside quotes are not interpreted."""
        tokens = scan("WHERE x='$a #b @c ?d [e] {f}'")
        var_tokens = [t for t in tokens if t.type not in (TokenType.LITERAL,)]
        assert len(var_tokens) == 0
        combined = "".join(t.value for t in tokens)
        assert "$a #b @c ?d [e] {f}" in combined

    # --- Edge cases ---

    def test_trailing_backslash_ignored(self):
        """A backslash at end of input with nothing after it is silently ignored."""
        tokens = scan("test\\")
        combined = "".join(t.value for t in tokens)
        assert combined == "test"

    def test_escape_non_special_char(self):
        """Backslash before a non-special char consumes the backslash, keeps the char."""
        tokens = scan("a\\nb")
        combined = "".join(t.value for t in tokens)
        assert combined == "anb"

    def test_multiple_escapes_in_sequence(self):
        """Multiple escaped special chars in a row."""
        tokens = scan("\\$a \\#b \\@c \\?d")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert combined == "$a #b @c ?d"

    def test_escaped_chars_mixed_with_real_variables(self):
        """Escaped special chars alongside real variables."""
        tokens = scan("\\$literal $real \\#literal #real_lit")
        escaped_vars = [t for t in tokens if t.type == TokenType.ESCAPED_VAR]
        literal_vars = [t for t in tokens if t.type == TokenType.LITERAL_VAR]
        assert len(escaped_vars) == 1
        assert escaped_vars[0].value == "real"
        assert len(literal_vars) == 1
        assert literal_vars[0].value == "real_lit"
        literals_combined = "".join(
            t.value for t in tokens if t.type == TokenType.LITERAL
        )
        assert "$literal" in literals_combined
        assert "#literal" in literals_combined

    def test_escaped_brackets_do_not_affect_bracket_stack(self):
        """Escaped brackets are not counted in bracket matching."""
        # One real optional section, plus escaped brackets outside
        tokens = scan("\\[ [x=$x] \\]")
        opens = [t for t in tokens if t.type == TokenType.OPEN_BRACKET]
        closes = [t for t in tokens if t.type == TokenType.CLOSE_BRACKET]
        assert len(opens) == 1
        assert len(closes) == 1
        literals_combined = "".join(
            t.value for t in tokens if t.type == TokenType.LITERAL
        )
        assert "[" in literals_combined
        assert "]" in literals_combined

    def test_escaped_braces_do_not_affect_bracket_stack(self):
        """Escaped braces are not counted in bracket matching."""
        tokens = scan("\\{ {} \\}")
        req_opens = [t for t in tokens if t.type == TokenType.REQUIRED_OPEN_BRACKET]
        req_closes = [t for t in tokens if t.type == TokenType.REQUIRED_CLOSE_BRACKET]
        assert len(req_opens) == 1
        assert len(req_closes) == 1

    # --- SQL dialect use cases ---

    def test_postgresql_positional_param(self):
        """PostgreSQL \\$1 style positional parameters."""
        tokens = scan("SELECT * FROM t WHERE id = \\$1")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "$1" in combined

    def test_sqlserver_quoted_identifiers(self):
        """SQL Server [schema].[table] style quoted identifiers."""
        tokens = scan("SELECT * FROM \\[dbo\\].\\[users\\]")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "[dbo].[users]" in combined

    def test_postgresql_jsonb_operators(self):
        """PostgreSQL JSONB operators like @>, ?, ?|, ?&."""
        tokens = scan(
            "SELECT * FROM t WHERE data \\@> '{\"key\": 1}' AND data \\? 'key'"
        )
        combined = "".join(t.value for t in tokens)
        assert "@>" in combined
        assert "?" in combined

    def test_mysql_user_variable(self):
        """MySQL @rownum user variable."""
        tokens = scan("SELECT \\@rownum := \\@rownum + 1 FROM t")
        assert all(t.type == TokenType.LITERAL for t in tokens)
        combined = "".join(t.value for t in tokens)
        assert "@rownum := @rownum + 1" in combined


# ==================== End-to-end escape tests (scanner + builder) ====================


class TestEscapeEndToEnd:
    """End-to-end tests verifying escaped chars flow through to built SQL."""

    def test_escaped_dollar_in_output(self):
        from tamuno_sqlgen import SQLGenApi

        api = SQLGenApi("test:= SELECT \\$literal FROM t WHERE x=$x;")
        sql = api.test(x="hello").build_sql()
        assert "$literal" in sql
        assert "'hello'" in sql

    def test_escaped_brackets_in_output(self):
        from tamuno_sqlgen import SQLGenApi

        api = SQLGenApi("test:= SELECT \\[col\\] FROM t;")
        sql = api.test().build_sql()
        assert "[col]" in sql

    def test_escaped_hash_in_output(self):
        from tamuno_sqlgen import SQLGenApi

        api = SQLGenApi("test:= SELECT \\#comment FROM t;")
        sql = api.test().build_sql()
        assert "#comment" in sql

    def test_escaped_at_in_output(self):
        from tamuno_sqlgen import SQLGenApi

        api = SQLGenApi("test:= SELECT \\@var FROM t;")
        sql = api.test().build_sql()
        assert "@var" in sql

    def test_escaped_backslash_in_output(self):
        from tamuno_sqlgen import SQLGenApi

        api = SQLGenApi("test:= SELECT \\\\ FROM t;")
        sql = api.test().build_sql()
        assert "\\" in sql

    def test_escaped_backslash_before_variable_in_output(self):
        from tamuno_sqlgen import SQLGenApi

        api = SQLGenApi("test:= SELECT \\\\$x FROM t;")
        sql = api.test(x="val").build_sql()
        assert "\\'val'" in sql
