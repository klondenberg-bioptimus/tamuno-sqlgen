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
    assert any(t.type == TokenType.TARGET_VAR and t.value == "user_id" and t.vartype == "int" for t in tokens)


def test_scan_escaped_var():
    tokens = scan("WHERE name=$user_name")
    assert any(t.type == TokenType.ESCAPED_VAR and t.value == "user_name" for t in tokens)


def test_scan_literal_var():
    tokens = scan("FROM #table_name")
    assert any(t.type == TokenType.LITERAL_VAR and t.value == "table_name" for t in tokens)


def test_scan_option_var():
    tokens = scan("?limit:int")
    assert any(t.type == TokenType.OPTION_VAR and t.value == "limit" and t.vartype == "int" for t in tokens)


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
    var_tokens = [t for t in tokens if t.type in (TokenType.ESCAPED_VAR, TokenType.LITERAL_VAR)]
    assert len(var_tokens) == 0


def test_scan_no_parse_inside_double_quotes():
    tokens = scan('WHERE status="$not_a_var"')
    var_tokens = [t for t in tokens if t.type in (TokenType.ESCAPED_VAR, TokenType.LITERAL_VAR)]
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
