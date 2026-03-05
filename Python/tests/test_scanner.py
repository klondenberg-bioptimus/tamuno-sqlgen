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
