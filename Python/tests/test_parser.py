"""Tests for the parser module."""

from __future__ import annotations

import pytest

from tamuno_sqlgen.parser import Parser, ParseError, Expression
from tamuno_sqlgen.scanner import TokenType


def test_parse_simple_select():
    p = Parser()
    p.parse("SELECT @user_id:int, @user_name:String FROM users WHERE name=$name")
    assert len(p.output_vars) == 2
    assert len(p.input_vars) == 1
    assert p.input_vars[0].value == "name"


def test_parse_extracts_output_vars():
    p = Parser()
    p.parse("SELECT @a:int, @b:String, @c:Date FROM tbl")
    names = [v.value for v in p.output_vars]
    assert names == ["a", "b", "c"]


def test_parse_extracts_input_vars_order():
    p = Parser()
    p.parse("WHERE x=$x AND y=$y:int AND z=$z:float")
    names = [v.value for v in p.input_vars]
    assert names == ["x", "y", "z"]


def test_parse_optional_section():
    p = Parser()
    p.parse("SELECT @id:int FROM t [ WHERE x=$x ]")
    # There should be a root + one optional child
    root = p.expressions[0]
    assert len(root.sub_expressions) == 1
    assert root.sub_expressions[0].optional is True


def test_parse_combiner_detection():
    p = Parser()
    p.parse("SELECT @id:int FROM t [WHERE [x=$x] [AND] [y=$y:int]]")
    root = p.expressions[0]
    # outer optional WHERE
    outer = root.sub_expressions[0]
    assert outer.alternative is True
    # [AND] should be a combiner
    combiner_exprs = [e for e in outer.sub_expressions if e.combiner]
    assert len(combiner_exprs) == 1


def test_parse_alternative_detection():
    p = Parser()
    p.parse("[ [x=$x] [AND] [y=$y:int] ]")
    root = p.expressions[0]
    outer = root.sub_expressions[0]
    assert outer.alternative is True


def test_parse_required_input_vars_bitmask():
    p = Parser()
    p.parse("WHERE x=$x AND y=$y:int")
    root = p.expressions[0]
    # Both x (bit 0) and y (bit 1) are required
    assert root.required_input_vars == 0b11


def test_parse_optional_does_not_propagate_to_root():
    p = Parser()
    p.parse("SELECT @id:int FROM t [ WHERE x=$x ]")
    root = p.expressions[0]
    # The root should NOT have x as required (it's inside optional)
    assert root.required_input_vars == 0


def test_parse_extract_statements():
    source = """\
foo:= SELECT @a:int FROM t WHERE x=$x;
bar:= INSERT INTO t VALUES ($v);
"""
    stmts = Parser.extract_statements(source)
    names = [s[0] for s in stmts]
    assert "foo" in names
    assert "bar" in names


def test_parse_multiline_statement():
    source = """\
selectUser:=
    SELECT @user_id:int, @user_name:String
        FROM users
        WHERE user_id=$user_id:int;
"""
    stmts = Parser.extract_statements(source)
    assert len(stmts) == 1
    name, body = stmts[0]
    assert name == "selectUser"
    p = Parser()
    p.parse(body)
    assert len(p.output_vars) == 2
    assert p.input_vars[0].value == "user_id"


def test_parse_stop_combiner():
    p = Parser()
    # {reset} or {} inside parser - REQUIRED_CLOSE_BRACKET creates stop_combiner
    p.parse("SELECT @id:int FROM t [WHERE [x=$x] {} [y=$y:int]]")
    root = p.expressions[0]
    outer = root.sub_expressions[0]
    stop_combiners = [e for e in outer.sub_expressions if e.stop_combiner]
    assert len(stop_combiners) >= 1


def test_parse_unknown_output_type_raises():
    p = Parser()
    with pytest.raises(ParseError):
        p.parse("SELECT @a:UnknownType FROM t")


def test_parse_differing_input_var_types_raises():
    p = Parser()
    with pytest.raises(ParseError):
        p.parse("WHERE x=$x:int AND x=$x:String")


def test_parse_empty_statement():
    p = Parser()
    p.parse("")
    assert p.input_vars == []
    assert p.output_vars == []
