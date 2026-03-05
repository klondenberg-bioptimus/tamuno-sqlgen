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


# ==================== Complex builder tests ====================


class TestBuildMultiTableJoin:
    """Building SQL with multi-table JOINs and many optional filters."""

    SEARCH_ORDERS = (
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
        "[o.status=$status] ] "
        "ORDER BY o.order_date DESC"
    )

    def test_build_join_all_filters(self):
        sql = _build(
            self.SEARCH_ORDERS,
            {
                "customer_name": "Acme Corp",
                "category": "Electronics",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
                "status": "shipped",
            },
        )
        assert "WHERE" in sql
        assert "c.customer_name='Acme Corp'" in sql
        assert "AND" in sql
        assert "p.category='Electronics'" in sql
        assert "'2024-01-01'" in sql
        assert "'2024-12-31'" in sql
        assert "o.status='shipped'" in sql
        assert "ORDER BY o.order_date DESC" in sql

    def test_build_join_no_filters(self):
        sql = _build(self.SEARCH_ORDERS, {})
        assert "WHERE" not in sql
        assert "JOIN customers c ON o.customer_id = c.customer_id" in sql
        assert "ORDER BY o.order_date DESC" in sql

    def test_build_join_single_filter(self):
        sql = _build(self.SEARCH_ORDERS, {"category": "Books"})
        assert "WHERE" in sql
        assert "p.category='Books'" in sql
        assert "AND" not in sql

    def test_build_join_two_nonadjacent_filters(self):
        """Only first and last filter: should still AND correctly."""
        sql = _build(
            self.SEARCH_ORDERS,
            {
                "customer_name": "Acme",
                "status": "pending",
            },
        )
        assert "WHERE" in sql
        assert "c.customer_name='Acme'" in sql
        assert "o.status='pending'" in sql
        assert sql.count("AND") == 1

    def test_build_join_three_filters(self):
        sql = _build(
            self.SEARCH_ORDERS,
            {
                "customer_name": "Acme",
                "date_from": "2024-06-01",
                "status": "shipped",
            },
        )
        assert sql.count("AND") == 2


class TestBuildGroupByHaving:
    """Building aggregation queries with optional HAVING."""

    SALES_REPORT = (
        "SELECT @category:String, @total_revenue:double, "
        "@order_count:int, @avg_price:double "
        "FROM products p "
        "JOIN order_items oi ON p.product_id = oi.product_id "
        "JOIN orders o ON oi.order_id = o.order_id "
        "[ WHERE "
        "[o.order_date >= $date_from:Date] [AND] "
        "[o.order_date <= $date_to:Date] [AND] "
        "[o.status=$status] ] "
        "GROUP BY p.category "
        "[ HAVING "
        "[SUM(oi.quantity * oi.unit_price) >= $min_revenue:double] [AND] "
        "[COUNT(DISTINCT o.order_id) >= $min_orders:int] ] "
        "ORDER BY total_revenue DESC"
    )

    def test_build_report_no_filters_no_having(self):
        sql = _build(self.SALES_REPORT, {})
        assert "WHERE" not in sql
        assert "HAVING" not in sql
        assert "GROUP BY p.category" in sql
        assert "ORDER BY total_revenue DESC" in sql

    def test_build_report_with_where_and_having(self):
        sql = _build(
            self.SALES_REPORT,
            {
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
                "min_revenue": 1000.0,
            },
        )
        assert "WHERE" in sql
        assert "'2024-01-01'" in sql
        assert "'2024-12-31'" in sql
        assert "HAVING" in sql
        assert "1000.0" in sql

    def test_build_report_having_only(self):
        sql = _build(self.SALES_REPORT, {"min_orders": 5})
        assert "WHERE" not in sql
        assert "HAVING" in sql
        assert "5" in sql

    def test_build_report_both_having_conditions(self):
        sql = _build(
            self.SALES_REPORT,
            {
                "min_revenue": 500.0,
                "min_orders": 10,
            },
        )
        assert "HAVING" in sql
        assert "AND" in sql
        assert "500.0" in sql
        assert "10" in sql


class TestBuildDynamicTableAndPagination:
    """Building queries with literal variables for dynamic SQL parts."""

    PAGINATED = (
        "SELECT @product_id:int, @product_name:String, @price:double "
        "FROM products "
        "[ WHERE [category=$category] [AND] [price >= $min_price:double] ] "
        "ORDER BY #sort_column #sort_direction "
        "LIMIT #page_size OFFSET #page_offset"
    )

    def test_build_pagination_with_all_params(self):
        sql = _build(
            self.PAGINATED,
            {
                "category": "Electronics",
                "min_price": 9.99,
                "sort_column": "price",
                "sort_direction": "DESC",
                "page_size": "20",
                "page_offset": "40",
            },
        )
        assert "category='Electronics'" in sql
        assert "9.99" in sql
        assert "ORDER BY price DESC" in sql
        assert "LIMIT 20 OFFSET 40" in sql

    def test_build_pagination_no_filters(self):
        sql = _build(
            self.PAGINATED,
            {
                "sort_column": "product_name",
                "sort_direction": "ASC",
                "page_size": "10",
                "page_offset": "0",
            },
        )
        assert "WHERE" not in sql
        assert "ORDER BY product_name ASC" in sql
        assert "LIMIT 10 OFFSET 0" in sql

    def test_build_dynamic_table_name(self):
        sql = _build(
            "SELECT @id:int, @name:String FROM #table_name WHERE active=$active:int",
            {"table_name": "products", "active": 1},
        )
        assert "FROM products" in sql
        assert "active=1" in sql


class TestBuildComplexUpdate:
    """Building UPDATE statements with many optional SET fields."""

    UPDATE_PRODUCT = (
        "UPDATE products SET "
        "[product_name=$product_name] [,] "
        "[category=$category] [,] "
        "[price=$price:double] [,] "
        "[stock=$stock:int] [,] "
        "[description=$description] "
        "WHERE product_id=$product_id:int"
    )

    def test_build_update_all_fields(self):
        sql = _build(
            self.UPDATE_PRODUCT,
            {
                "product_name": "Widget",
                "category": "Gadgets",
                "price": 19.99,
                "stock": 100,
                "description": "A nice widget",
                "product_id": 42,
            },
        )
        assert "product_name='Widget'" in sql
        assert "category='Gadgets'" in sql
        assert "price=19.99" in sql
        assert "stock=100" in sql
        assert "description='A nice widget'" in sql
        assert sql.count(",") == 4  # 4 commas between 5 fields

    def test_build_update_single_field(self):
        sql = _build(
            self.UPDATE_PRODUCT,
            {
                "price": 29.99,
                "product_id": 42,
            },
        )
        assert "price=29.99" in sql
        assert "," not in sql
        assert "product_name" not in sql

    def test_build_update_first_and_last_field(self):
        sql = _build(
            self.UPDATE_PRODUCT,
            {
                "product_name": "Gadget",
                "description": "Updated",
                "product_id": 1,
            },
        )
        assert "product_name='Gadget'" in sql
        assert "description='Updated'" in sql
        assert sql.count(",") == 1

    def test_build_update_middle_fields_only(self):
        sql = _build(
            self.UPDATE_PRODUCT,
            {
                "category": "New Cat",
                "price": 5.0,
                "stock": 50,
                "product_id": 7,
            },
        )
        assert "category='New Cat'" in sql
        assert "price=5.0" in sql
        assert "stock=50" in sql
        assert sql.count(",") == 2


class TestBuildStopCombiner:
    """Building with stop-combiners for independent filter groups."""

    ADVANCED_SEARCH = (
        "SELECT @id:int, @name:String FROM products "
        "[ WHERE "
        "[name LIKE $name_pattern] "
        "{} "
        "[AND category=$category] "
        "{} "
        "[AND price >= $min_price:double] [AND] [price <= $max_price:double] ]"
    )

    def test_build_stop_combiner_all_groups(self):
        sql = _build(
            self.ADVANCED_SEARCH,
            {
                "name_pattern": "%widget%",
                "category": "Gadgets",
                "min_price": 10.0,
                "max_price": 100.0,
            },
        )
        assert "WHERE" in sql
        assert "name LIKE '%widget%'" in sql
        assert "AND category='Gadgets'" in sql
        assert "AND price >= 10.0" in sql
        assert "AND" in sql
        assert "price <= 100.0" in sql

    def test_build_stop_combiner_only_last_group(self):
        """Price range only -- stop-combiner resets combine flag before AND category."""
        sql = _build(
            self.ADVANCED_SEARCH,
            {
                "min_price": 5.0,
                "max_price": 50.0,
            },
        )
        assert "WHERE" in sql
        assert "price >= 5.0" in sql
        assert "price <= 50.0" in sql
        # category should not appear
        assert "category" not in sql

    def test_build_stop_combiner_only_first_group(self):
        sql = _build(self.ADVANCED_SEARCH, {"name_pattern": "%test%"})
        assert "WHERE" in sql
        assert "name LIKE '%test%'" in sql
        assert "AND" not in sql

    def test_build_stop_combiner_nothing(self):
        sql = _build(self.ADVANCED_SEARCH, {})
        assert "WHERE" not in sql


class TestBuildInsertFromSelect:
    """Building INSERT ... SELECT with required and optional parts."""

    COPY_ITEMS = (
        "INSERT INTO #target_table (order_id, product_id, quantity, unit_price) "
        "SELECT oi.order_id, oi.product_id, oi.quantity, oi.unit_price "
        "FROM order_items oi "
        "JOIN orders o ON oi.order_id = o.order_id "
        "WHERE o.status=$status "
        "[AND o.order_date >= $date_from:Date] "
        "[AND o.order_date <= $date_to:Date]"
    )

    def test_build_copy_with_all_params(self):
        sql = _build(
            self.COPY_ITEMS,
            {
                "target_table": "archived_items",
                "status": "completed",
                "date_from": "2024-01-01",
                "date_to": "2024-06-30",
            },
        )
        assert "INSERT INTO archived_items" in sql
        assert "o.status='completed'" in sql
        assert "AND o.order_date >= '2024-01-01'" in sql
        assert "AND o.order_date <= '2024-06-30'" in sql

    def test_build_copy_required_only(self):
        sql = _build(
            self.COPY_ITEMS,
            {
                "target_table": "backup",
                "status": "shipped",
            },
        )
        assert "INSERT INTO backup" in sql
        assert "o.status='shipped'" in sql
        assert "o.order_date" not in sql

    def test_build_copy_missing_required_raises(self):
        with pytest.raises(ValueError, match="Missing required"):
            _build(self.COPY_ITEMS, {"target_table": "backup"})


class TestBuildDeleteWithOptionals:
    """Building DELETE statements with optional WHERE conditions."""

    DELETE_ORDERS = (
        "DELETE FROM orders "
        "[ WHERE "
        "[status=$status] [AND] "
        "[order_date < $before_date:Date] [AND] "
        "[customer_id=$customer_id:int] ]"
    )

    def test_build_delete_all_conditions(self):
        sql = _build(
            self.DELETE_ORDERS,
            {
                "status": "cancelled",
                "before_date": "2023-01-01",
                "customer_id": 99,
            },
        )
        assert "DELETE FROM orders" in sql
        assert "status='cancelled'" in sql
        assert "order_date < '2023-01-01'" in sql
        assert "customer_id=99" in sql
        assert sql.count("AND") == 2

    def test_build_delete_single_condition(self):
        sql = _build(self.DELETE_ORDERS, {"status": "cancelled"})
        assert "WHERE" in sql
        assert "status='cancelled'" in sql
        assert "AND" not in sql

    def test_build_delete_no_conditions(self):
        sql = _build(self.DELETE_ORDERS, {})
        assert "WHERE" not in sql
        assert sql.strip() == "DELETE FROM orders"


class TestBuildDialectVariations:
    """Building with different SQL dialects."""

    def test_ansi_escapes_single_quotes_by_doubling(self):
        sql = _build("WHERE x=$x", {"x": 'it\'s a "test"'})
        assert "it''s a \"test\"" in sql

    def test_mysql_escapes_single_quotes_with_backslash(self):
        sql = _build("WHERE x=$x", {"x": "it's a test"}, dialect=MySQLDialect())
        assert "it\\'s a test" in sql

    def test_mysql_escapes_backslash(self):
        sql = _build(
            "WHERE path=$path", {"path": "C:\\Users\\test"}, dialect=MySQLDialect()
        )
        assert "C:\\\\Users\\\\test" in sql

    def test_ansi_bool_true(self):
        sql = _build("WHERE active=$active:boolean", {"active": True})
        assert "active=1" in sql

    def test_ansi_bool_false(self):
        sql = _build("WHERE active=$active:boolean", {"active": False})
        assert "active=0" in sql

    def test_ansi_int(self):
        sql = _build("WHERE count=$count:int", {"count": 42})
        assert "count=42" in sql
        assert "'" not in sql

    def test_ansi_float(self):
        sql = _build("WHERE price=$price:double", {"price": 19.99})
        assert "price=19.99" in sql
        assert "'" not in sql

    def test_ansi_date(self):
        import datetime

        sql = _build("WHERE d=$d:Date", {"d": datetime.date(2024, 3, 15)})
        assert "d='2024-03-15'" in sql

    def test_ansi_null(self):
        sql = _build("[ WHERE x=$x ]", {"x": None})
        assert "WHERE" not in sql


class TestBuildComplexRealWorld:
    """Real-world complex SQL generation scenarios."""

    def test_build_search_with_like_and_range(self):
        sql = _build(
            "SELECT @id:int, @name:String, @price:double FROM products "
            "[ WHERE "
            "[name LIKE $search] [AND] "
            "[price >= $min:double] [AND] [price <= $max:double] [AND] "
            "[category=$cat] ] "
            "ORDER BY name",
            {"search": "%phone%", "min": 100.0, "max": 999.99},
        )
        assert "name LIKE '%phone%'" in sql
        assert "price >= 100.0" in sql
        assert "price <= 999.99" in sql
        assert "category" not in sql
        assert sql.count("AND") == 2

    def test_build_multi_table_insert_select(self):
        sql = _build(
            "INSERT INTO #dest (a, b) "
            "SELECT src.a, src.b FROM #source src "
            "WHERE src.status=$status [AND src.date >= $since:Date]",
            {
                "dest": "archive",
                "source": "live_data",
                "status": "processed",
                "since": "2024-01-01",
            },
        )
        assert "INSERT INTO archive" in sql
        assert "FROM live_data src" in sql
        assert "status='processed'" in sql
        assert "AND src.date >= '2024-01-01'" in sql

    def test_build_option_var_produces_no_sql(self):
        sql = _build(
            "INSERT INTO t (a) VALUES ($a) ?meta:String",
            {"a": "val", "meta": "tracking-123"},
        )
        assert "'val'" in sql
        assert "tracking-123" not in sql  # option vars produce no output

    def test_build_escaped_special_chars_in_values(self):
        sql = _build("WHERE x=$x", {"x": "O'Brien & Sons <test>"})
        assert "O''Brien & Sons <test>" in sql
