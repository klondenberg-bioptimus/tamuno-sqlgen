"""Tests for the SQL builder module."""

from __future__ import annotations

import pytest

from tamuno_sqlgen.parser import Parser
from tamuno_sqlgen.builder import SQLBuilder
from tamuno_sqlgen.dialect import SQLDialect, MySQLDialect


def _make_builder(template: str, dialect=None) -> SQLBuilder:
    p = Parser()
    p.parse(template)
    return SQLBuilder(p.tokens, p.expressions, p.input_vars, dialect or SQLDialect())


def _build(template: str, params: dict, dialect=None) -> str:
    return _make_builder(template, dialect).build(params)


# --- Basic literal output ---

def test_build_plain_literal():
    sql = _build("SELECT * FROM users", {})
    assert sql == "SELECT * FROM users"


def test_build_target_var_emits_name():
    sql = _build("SELECT @user_id:int FROM t", {})
    assert "user_id" in sql


# --- Escaped vars ---

def test_build_escaped_string():
    sql = _build("WHERE name=$name", {"name": "alice"})
    assert sql == "WHERE name='alice'"


def test_build_escaped_int():
    sql = _build("WHERE id=$id:int", {"id": 42})
    assert "42" in sql
    assert "'" not in sql


def test_build_escaped_none_is_null():
    # Required (non-optional) vars with None raise ValueError (same as Java behavior)
    with pytest.raises(ValueError, match="Missing required"):
        _build("WHERE x=$x", {"x": None})


def test_build_escaped_none_in_optional_excluded():
    # Inside an optional section, None means the section is omitted
    sql = _build("[ WHERE x=$x ]", {"x": None})
    assert "WHERE" not in sql


def test_build_escaped_string_with_quotes():
    sql = _build("WHERE n=$n", {"n": "O'Brien"})
    assert "O''Brien" in sql


# --- Literal vars ---

def test_build_literal_var_raw():
    sql = _build("FROM #tbl_name", {"tbl_name": "my_table"})
    assert "my_table" in sql


# --- Optional sections ---

def test_build_optional_section_included():
    sql = _build("SELECT @id:int FROM t [ WHERE x=$x ]", {"x": "val"})
    assert "WHERE x='val'" in sql


def test_build_optional_section_excluded():
    sql = _build("SELECT @id:int FROM t [ WHERE x=$x ]", {})
    assert "WHERE" not in sql


def test_build_optional_section_excluded_when_none():
    sql = _build("SELECT @id:int FROM t [ WHERE x=$x ]", {"x": None})
    assert "WHERE" not in sql


# --- Combiner (AND) ---

def test_build_combiner_included_when_both():
    sql = _build(
        "SELECT @id:int FROM t [ WHERE [x=$x] [AND] [y=$y:int] ]",
        {"x": "a", "y": 1},
    )
    assert "AND" in sql


def test_build_combiner_excluded_when_only_first():
    sql = _build(
        "SELECT @id:int FROM t [ WHERE [x=$x] [AND] [y=$y:int] ]",
        {"x": "a"},
    )
    assert "AND" not in sql


def test_build_combiner_excluded_when_only_second():
    sql = _build(
        "SELECT @id:int FROM t [ WHERE [x=$x] [AND] [y=$y:int] ]",
        {"y": 1},
    )
    assert "AND" not in sql


def test_build_combiner_excluded_when_none():
    sql = _build(
        "SELECT @id:int FROM t [ WHERE [x=$x] [AND] [y=$y:int] ]",
        {},
    )
    assert "WHERE" not in sql
    assert "AND" not in sql


# --- Alternative section ---

def test_build_alternative_section_included_if_any():
    sql = _build("[ [x=$x] [OR] [y=$y:int] ]", {"x": "a"})
    assert "x='a'" in sql


def test_build_alternative_section_excluded_if_none():
    sql = _build("[ [x=$x] [OR] [y=$y:int] ]", {})
    assert "x" not in sql


# --- Required vars ---

def test_build_missing_required_var_raises():
    b = _make_builder("SELECT @id:int FROM t WHERE x=$x")
    with pytest.raises(ValueError, match="Missing required"):
        b.build({})


# --- MySQL dialect ---

def test_mysql_dialect_escapes_backslash():
    dialect = MySQLDialect()
    sql = _build("WHERE n=$n", {"n": "O'Brien"}, dialect=dialect)
    assert "\\'" in sql


# --- Update with optional SET ---

def test_build_update_with_comma_combiner():
    sql = _build(
        "UPDATE t SET [x=$x] [,] [y=$y:int] WHERE id=$id:int",
        {"x": "val", "y": 10, "id": 5},
    )
    assert "," in sql
    assert "x='val'" in sql
    assert "y=10" in sql


def test_build_update_no_comma_single_field():
    sql = _build(
        "UPDATE t SET [x=$x] [,] [y=$y:int] WHERE id=$id:int",
        {"x": "val", "id": 5},
    )
    assert "," not in sql
    assert "x='val'" in sql
