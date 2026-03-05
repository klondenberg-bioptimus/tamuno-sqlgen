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


# ==================== Complex parsing tests ====================


class TestParseMultiTableJoins:
    """Parsing templates with JOINs and many variables."""

    def test_parse_join_extracts_all_output_vars(self):
        p = Parser()
        p.parse(
            "SELECT @order_id:int, @customer_name:String, @product_name:String, "
            "@quantity:int, @unit_price:double, @order_date:Date "
            "FROM orders o "
            "JOIN customers c ON o.customer_id = c.customer_id"
        )
        assert len(p.output_vars) == 6
        names = [v.value for v in p.output_vars]
        assert names == [
            "order_id",
            "customer_name",
            "product_name",
            "quantity",
            "unit_price",
            "order_date",
        ]
        types = [v.vartype for v in p.output_vars]
        assert types == ["int", "String", "String", "int", "double", "Date"]

    def test_parse_join_with_five_optional_where_filters(self):
        p = Parser()
        p.parse(
            "SELECT @id:int FROM orders o "
            "JOIN customers c ON o.customer_id = c.customer_id "
            "[ WHERE "
            "[c.name=$name] [AND] [o.status=$status] [AND] "
            "[o.date >= $date_from:Date] [AND] [o.date <= $date_to:Date] "
            "[AND] [o.total >= $min_total:double] ]"
        )
        assert len(p.input_vars) == 5
        root = p.expressions[0]
        outer = root.sub_expressions[0]
        assert outer.alternative is True
        # 5 value sections + 4 AND combiners = 9 sub-expressions
        assert len(outer.sub_expressions) == 9

    def test_parse_join_input_var_types_preserved(self):
        p = Parser()
        p.parse(
            "SELECT @id:int FROM t "
            "[ WHERE "
            "[a=$a] [AND] [b=$b:int] [AND] [c=$c:double] [AND] [d=$d:Date] ]"
        )
        types = [v.vartype for v in p.input_vars]
        assert types == ["a" and "String", "int", "double", "Date"]
        # more precise:
        assert p.input_vars[0].vartype == "String"
        assert p.input_vars[1].vartype == "int"
        assert p.input_vars[2].vartype == "double"
        assert p.input_vars[3].vartype == "Date"


class TestParseDeeplyNested:
    """Parsing deeply nested optional sections."""

    def test_parse_three_level_nesting(self):
        p = Parser()
        p.parse("[ [ [x=$x] ] ]")
        root = p.expressions[0]
        # Level 1: one optional child
        assert len(root.sub_expressions) == 1
        level1 = root.sub_expressions[0]
        assert level1.optional is True
        # Level 2: one optional child inside
        assert len(level1.sub_expressions) == 1
        level2 = level1.sub_expressions[0]
        assert level2.optional is True
        # Level 3: innermost with var
        assert len(level2.sub_expressions) == 1
        level3 = level2.sub_expressions[0]
        assert level3.optional is True

    def test_parse_nested_vars_bitmask_does_not_propagate_past_optional(self):
        p = Parser()
        p.parse("SELECT @id:int FROM t [ WHERE [x=$x] [AND] [y=$y:int] ]")
        root = p.expressions[0]
        # Root should have no required vars (everything is inside optional)
        assert root.required_input_vars == 0
        # But the inner sections should have their bitmask set
        outer = root.sub_expressions[0]
        val_sections = [e for e in outer.sub_expressions if not e.combiner]
        assert val_sections[0].required_input_vars != 0
        assert val_sections[1].required_input_vars != 0


class TestParseMultipleCombinerTypes:
    """Parsing templates with different combiner types (AND, OR, comma)."""

    def test_parse_comma_combiner_in_update(self):
        p = Parser()
        p.parse(
            "UPDATE t SET [a=$a] [,] [b=$b:int] [,] [c=$c:double] [,] "
            "[d=$d] [,] [e=$e:int] WHERE id=$id:int"
        )
        root = p.expressions[0]
        # 5 SET sections + 4 comma combiners in the alternative wrapper? No,
        # these are direct children of root -- let's count
        # Actually they're direct children since there's no outer [...] wrapping them all
        combiners = [e for e in root.sub_expressions if e.combiner]
        assert len(combiners) == 4
        assert len(p.input_vars) == 6  # a, b, c, d, e, id

    def test_parse_combiner_gets_next_sibling_bitmask(self):
        """Combiner's required_input_vars should match the NEXT section's bitmask."""
        p = Parser()
        p.parse("[ [x=$x] [AND] [y=$y:int] ]")
        root = p.expressions[0]
        outer = root.sub_expressions[0]
        # Find the AND combiner
        combiner = [e for e in outer.sub_expressions if e.combiner][0]
        # Find y's section
        y_section = [
            e
            for e in outer.sub_expressions
            if not e.combiner and e.required_input_vars != 0
        ]
        # The combiner should have the bitmask of the y section
        # (so it's only included when y is available too)
        y_bitmask = y_section[-1].required_input_vars
        assert combiner.required_input_vars == y_bitmask


class TestParseStopCombiner:
    """Parsing stop-combiner ({}) usage."""

    def test_parse_multiple_stop_combiners(self):
        p = Parser()
        p.parse("SELECT @id:int FROM t [ WHERE [a=$a] {} [AND b=$b] {} [AND c=$c] ]")
        root = p.expressions[0]
        outer = root.sub_expressions[0]
        stop_combiners = [e for e in outer.sub_expressions if e.stop_combiner]
        assert len(stop_combiners) == 2

    def test_parse_stop_combiner_between_independent_groups(self):
        p = Parser()
        p.parse(
            "[ WHERE "
            "[name LIKE $pattern] "
            "{} "
            "[AND category=$cat] "
            "{} "
            "[AND price >= $min:double] [AND] [price <= $max:double] ]"
        )
        root = p.expressions[0]
        outer = root.sub_expressions[0]
        stop_combiners = [e for e in outer.sub_expressions if e.stop_combiner]
        assert len(stop_combiners) == 2
        assert len(p.input_vars) == 4  # pattern, cat, min, max


class TestParseComplexStatementExtraction:
    """Extracting multiple statements from complex .sqlg source."""

    def test_extract_many_statements(self):
        source = """\
selectAll:= SELECT @id:int FROM t;
insertOne:= INSERT INTO t (a) VALUES ($a);
updateOne:= UPDATE t SET [a=$a] WHERE id=$id:int;
deleteOne:= DELETE FROM t WHERE id=$id:int;
searchWithJoin:=
    SELECT @a:int, @b:String
        FROM t1
        JOIN t2 ON t1.id = t2.fk
        [ WHERE [t1.x=$x] [AND] [t2.y=$y:int] ];
"""
        stmts = Parser.extract_statements(source)
        names = [s[0] for s in stmts]
        assert len(stmts) == 5
        assert "selectAll" in names
        assert "searchWithJoin" in names

    def test_extract_preserves_multiline_body(self):
        source = """\
complexQuery:=
    SELECT @id:int, @name:String
        FROM products p
        JOIN categories c ON p.cat_id = c.id
        [ WHERE
            [p.name LIKE $pattern]
            [AND]
            [c.name=$category]
        ]
        ORDER BY p.name;
"""
        stmts = Parser.extract_statements(source)
        assert len(stmts) == 1
        name, body = stmts[0]
        assert name == "complexQuery"
        p = Parser()
        p.parse(body)
        assert len(p.output_vars) == 2
        assert len(p.input_vars) == 2


class TestParseLiteralAndOptionVars:
    """Parsing literal (#) and option (?) variables."""

    def test_parse_literal_vars_as_input(self):
        p = Parser()
        p.parse("SELECT @id:int FROM #table_name WHERE id=$id:int")
        # Literal vars count as input vars
        input_names = [v.value for v in p.input_vars]
        assert "table_name" in input_names
        assert "id" in input_names

    def test_parse_option_var_as_input(self):
        p = Parser()
        p.parse("INSERT INTO t (a) VALUES ($a) ?meta:String")
        input_names = [v.value for v in p.input_vars]
        assert "a" in input_names
        # Option vars are also tracked in input_vars
        assert "meta" in input_names

    def test_parse_pagination_literal_vars(self):
        p = Parser()
        p.parse(
            "SELECT @id:int FROM t "
            "ORDER BY #sort_col #sort_dir "
            "LIMIT #page_size OFFSET #page_offset"
        )
        literal_inputs = [v for v in p.input_vars if v.type == TokenType.LITERAL_VAR]
        assert len(literal_inputs) == 4
        names = [v.value for v in literal_inputs]
        assert names == ["sort_col", "sort_dir", "page_size", "page_offset"]


class TestParseGroupByHaving:
    """Parsing GROUP BY and optional HAVING clauses."""

    def test_parse_group_by_with_optional_having(self):
        p = Parser()
        p.parse(
            "SELECT @cat:String, @total:double "
            "FROM products "
            "GROUP BY category "
            "[ HAVING "
            "[SUM(price) >= $min_total:double] [AND] "
            "[COUNT(*) >= $min_count:int] ]"
        )
        assert len(p.output_vars) == 2
        input_names = [v.value for v in p.input_vars]
        assert "min_total" in input_names
        assert "min_count" in input_names
        root = p.expressions[0]
        having = root.sub_expressions[0]
        assert having.alternative is True

    def test_parse_aggregation_query_with_where_and_having(self):
        p = Parser()
        p.parse(
            "SELECT @cat:String, @revenue:double, @cnt:int "
            "FROM products p "
            "JOIN order_items oi ON p.id = oi.product_id "
            "[ WHERE "
            "[p.category=$category] [AND] "
            "[oi.order_date >= $date_from:Date] ] "
            "GROUP BY p.category "
            "[ HAVING [SUM(oi.price) >= $min_rev:double] ]"
        )
        assert len(p.output_vars) == 3
        assert len(p.input_vars) == 3  # category, date_from, min_rev
        root = p.expressions[0]
        # Should have two top-level optional/alternative sections: WHERE and HAVING
        optionals = [e for e in root.sub_expressions if e.optional or e.alternative]
        assert len(optionals) == 2
