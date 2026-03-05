"""Tests for the high-level SQLGenApi."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from tamuno_sqlgen.api import SQLGenApi


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# --- Creation ---


def test_api_from_string(sample_source):
    api = SQLGenApi(sample_source)
    assert "selectUserLogin" in api.statement_names


def test_api_from_file(sample_sqlg_path):
    api = SQLGenApi.from_file(str(sample_sqlg_path))
    assert "selectUserLogin" in api.statement_names


def test_api_statement_names(sample_source):
    api = SQLGenApi(sample_source)
    names = api.statement_names
    assert "insertUser" in names
    assert "updateUser" in names


def test_api_attribute_access(sample_source):
    api = SQLGenApi(sample_source)
    factory = api.selectUserLogin
    assert callable(factory)


def test_api_snake_case_access(sample_source):
    api = SQLGenApi(sample_source)
    factory = api.select_user_login
    assert callable(factory)


def test_api_getitem(sample_source):
    api = SQLGenApi(sample_source)
    factory = api["selectUserLogin"]
    assert callable(factory)


def test_api_unknown_statement_raises(sample_source):
    api = SQLGenApi(sample_source)
    with pytest.raises(AttributeError):
        _ = api.nonExistentStatement


# --- Build SQL ---


def test_api_build_sql_select(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUserLogin(user_name="alice", password="secret")
    sql = params.build_sql()
    assert "alice" in sql
    assert "secret" in sql
    assert "SELECT" in sql


def test_api_build_sql_optional_absent(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    sql = params.build_sql()
    assert "WHERE" not in sql


def test_api_build_sql_optional_present(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUser(user_name="alice")
    sql = params.build_sql()
    assert "WHERE" in sql
    assert "alice" in sql


def test_api_build_sql_insert(sample_source):
    api = SQLGenApi(sample_source)
    params = api.insertUser(user_name="dave", active=1)
    sql = params.build_sql()
    assert "INSERT INTO users" in sql
    assert "'dave'" in sql


def test_api_to_sql_alias(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUser(user_name="alice")
    assert params.to_sql() == params.build_sql()


# --- Query execution against SQLite ---


def test_api_query_returns_dataframe(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    df = params.query(sqlite_conn)
    assert isinstance(df, pd.DataFrame)


def test_api_query_with_user_name_filter(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser(user_name="alice")
    df = params.query(sqlite_conn)
    assert len(df) == 1
    assert df.iloc[0]["user_name"] == "alice"


def test_api_query_with_active_filter(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser(active=1)
    df = params.query(sqlite_conn)
    # alice and carol are active
    assert len(df) >= 1


def test_api_query_all_users(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    df = params.query(sqlite_conn)
    # selectUser has LIMIT 1 so returns at most 1 row
    assert len(df) <= 1  # selectUser has LIMIT 1


def test_api_query_column_names(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    df = params.query(sqlite_conn)
    assert "user_id" in df.columns
    assert "user_name" in df.columns
    assert "birthdate" in df.columns


# --- Execute (INSERT/UPDATE) ---


def test_api_execute_insert(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.insertUser(user_name="dave", active=1)
    rows = params.execute(sqlite_conn)
    assert rows == 1


def test_api_execute_insert_persists(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    api.insertUser(user_name="dave", active=1).execute(sqlite_conn)
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_name='dave'")
    count = cursor.fetchone()[0]
    assert count == 1


def test_api_execute_update(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.updateUser(user_name="alice_updated", user_id=1)
    rows = params.execute(sqlite_conn)
    assert rows == 1


# --- Optional field combiner ---


def test_api_update_single_field_no_comma(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.updateUser(user_name="bob_renamed", user_id=2)
    sql = params.build_sql()
    # Should NOT have a trailing comma
    assert "user_name='bob_renamed'" in sql
    # active is absent, so comma should not appear
    assert "," not in sql.split("WHERE")[0].strip().rstrip(",")


def test_api_update_two_fields_has_comma(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.updateUser(user_name="carol_new", active=0, user_id=3)
    sql = params.build_sql()
    assert "," in sql


# ==================== Complex API tests ====================


# --- Complex schema fixture ---

COMPLEX_TEMPLATE = """\
searchOrders:=
    SELECT o.order_id as @order_id:int, c.customer_name as @customer_name:String,
           p.product_name as @product_name:String,
           oi.quantity as @quantity:int, oi.unit_price as @unit_price:double,
           o.order_date as @order_date:String
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
            [ WHERE
                [c.customer_name=$customer_name]
                [AND]
                [p.category=$category]
                [AND]
                [o.order_date >= $date_from]
                [AND]
                [o.order_date <= $date_to]
                [AND]
                [o.status=$status]
            ]
        ORDER BY o.order_date DESC;

salesReport:=
    SELECT p.category as @category:String,
           SUM(oi.quantity * oi.unit_price) as @total_revenue:double,
           COUNT(DISTINCT o.order_id) as @order_count:int
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        JOIN orders o ON oi.order_id = o.order_id
            [ WHERE
                [o.status=$status]
                [AND]
                [p.category=$category]
            ]
        GROUP BY p.category
        ORDER BY total_revenue DESC;

paginatedProducts:=
    SELECT @product_id:int, @product_name:String, @category:String,
           @price:double
        FROM products
            [ WHERE
                [category=$category]
                [AND]
                [price >= $min_price:double]
                [AND]
                [price <= $max_price:double]
            ]
        ORDER BY #sort_column
        LIMIT #page_size OFFSET #page_offset;

updateProduct:=
    UPDATE products SET
        [product_name=$product_name] [,]
        [category=$category] [,]
        [price=$price:double]
    WHERE product_id=$product_id:int;

insertProduct:=
    INSERT INTO products (product_name, category, price)
        VALUES ($product_name, $category, $price:double);

deleteOrders:=
    DELETE FROM orders
        [ WHERE
            [status=$status]
            [AND]
            [order_date < $before_date]
            [AND]
            [customer_id=$customer_id:int]
        ];

selectFromDynamic:=
    SELECT @id:int, @name:String
        FROM #table_name
            [ WHERE [name=$name] ]
        ORDER BY id;

customerOrderSummary:=
    SELECT c.customer_name as @customer_name:String,
           COUNT(o.order_id) as @num_orders:int
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
            [ WHERE [o.status=$status] ]
        GROUP BY c.customer_name
        ORDER BY num_orders DESC;
"""


@pytest.fixture
def complex_conn():
    """In-memory SQLite database with a full e-commerce schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            email TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)
    cur.execute("""
        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # Seed data
    cur.executemany(
        "INSERT INTO customers (customer_id, customer_name, email) VALUES (?, ?, ?)",
        [
            (1, "Acme Corp", "acme@example.com"),
            (2, "Globex Inc", "globex@example.com"),
            (3, "Initech", "initech@example.com"),
        ],
    )
    cur.executemany(
        "INSERT INTO products (product_id, product_name, category, price) VALUES (?, ?, ?, ?)",
        [
            (1, "Widget A", "Gadgets", 19.99),
            (2, "Widget B", "Gadgets", 29.99),
            (3, "Gizmo X", "Electronics", 149.99),
            (4, "Gizmo Y", "Electronics", 249.99),
            (5, "Doohickey", "Misc", 9.99),
        ],
    )
    cur.executemany(
        "INSERT INTO orders (order_id, customer_id, order_date, status) VALUES (?, ?, ?, ?)",
        [
            (1, 1, "2024-01-15", "shipped"),
            (2, 1, "2024-03-20", "shipped"),
            (3, 2, "2024-02-10", "pending"),
            (4, 2, "2024-06-05", "shipped"),
            (5, 3, "2024-04-01", "cancelled"),
            (6, 3, "2024-07-12", "shipped"),
        ],
    )
    cur.executemany(
        "INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
        [
            (1, 1, 1, 5, 19.99),
            (2, 1, 3, 2, 149.99),
            (3, 2, 2, 10, 29.99),
            (4, 3, 4, 1, 249.99),
            (5, 4, 1, 3, 19.99),
            (6, 4, 5, 20, 9.99),
            (7, 5, 3, 1, 149.99),
            (8, 6, 2, 7, 29.99),
            (9, 6, 4, 3, 249.99),
        ],
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def complex_api():
    return SQLGenApi(COMPLEX_TEMPLATE)


# --- Multi-table JOIN query tests ---


class TestApiSearchOrders:
    """Test multi-table JOIN queries with optional filters."""

    def test_search_all_orders(self, complex_api, complex_conn):
        df = complex_api.searchOrders().query(complex_conn)
        assert isinstance(df, pd.DataFrame)
        # We inserted 9 order items across 6 orders
        assert len(df) == 9

    def test_search_by_customer(self, complex_api, complex_conn):
        df = complex_api.searchOrders(customer_name="Acme Corp").query(complex_conn)
        # Acme has orders 1 and 2 with items 1,2,3
        assert len(df) == 3
        assert all(df["customer_name"] == "Acme Corp")

    def test_search_by_category(self, complex_api, complex_conn):
        df = complex_api.searchOrders(category="Electronics").query(complex_conn)
        # Products 3 and 4 are Electronics: items 2, 4, 7, 9
        assert len(df) == 4

    def test_search_by_status(self, complex_api, complex_conn):
        df = complex_api.searchOrders(status="shipped").query(complex_conn)
        # Orders 1,2,4,6 are shipped
        shipped_items = [1, 2, 3, 5, 6, 8, 9]  # items belonging to those orders
        assert len(df) == len(shipped_items)

    def test_search_combined_filters(self, complex_api, complex_conn):
        df = complex_api.searchOrders(
            customer_name="Acme Corp",
            status="shipped",
        ).query(complex_conn)
        # Acme has orders 1 and 2 both shipped, with items 1,2,3
        assert len(df) == 3

    def test_search_date_range(self, complex_api, complex_conn):
        df = complex_api.searchOrders(
            date_from="2024-03-01",
            date_to="2024-06-30",
        ).query(complex_conn)
        # Orders 2 (Mar 20), 3 (Feb 10 excluded), 4 (Jun 5), 5 (Apr 1)
        # After filtering: order 2 (Mar 20), order 4 (Jun 5), order 5 (Apr 1)
        assert len(df) > 0
        for _, row in df.iterrows():
            assert row["order_date"] >= "2024-03-01"
            assert row["order_date"] <= "2024-06-30"

    def test_search_no_match(self, complex_api, complex_conn):
        df = complex_api.searchOrders(customer_name="Nonexistent").query(complex_conn)
        assert len(df) == 0

    def test_search_column_names(self, complex_api, complex_conn):
        df = complex_api.searchOrders().query(complex_conn)
        expected = [
            "order_id",
            "customer_name",
            "product_name",
            "quantity",
            "unit_price",
            "order_date",
        ]
        assert list(df.columns) == expected


# --- Aggregation query tests ---


class TestApiSalesReport:
    """Test aggregation queries with GROUP BY."""

    def test_report_all_categories(self, complex_api, complex_conn):
        df = complex_api.salesReport().query(complex_conn)
        assert len(df) > 0
        assert "category" in df.columns
        assert "total_revenue" in df.columns
        assert "order_count" in df.columns

    def test_report_shipped_only(self, complex_api, complex_conn):
        df = complex_api.salesReport(status="shipped").query(complex_conn)
        assert len(df) > 0
        # Cancelled order items should not appear

    def test_report_by_category_filter(self, complex_api, complex_conn):
        df = complex_api.salesReport(category="Electronics").query(complex_conn)
        assert len(df) == 1
        assert df.iloc[0]["category"] == "Electronics"

    def test_report_combined_filters(self, complex_api, complex_conn):
        df = complex_api.salesReport(
            status="shipped",
            category="Gadgets",
        ).query(complex_conn)
        assert len(df) == 1
        assert df.iloc[0]["category"] == "Gadgets"


# --- Pagination tests ---


class TestApiPaginatedProducts:
    """Test pagination with literal variables."""

    def test_paginated_first_page(self, complex_api, complex_conn):
        df = complex_api.paginatedProducts(
            sort_column="product_name",
            page_size="2",
            page_offset="0",
        ).query(complex_conn)
        assert len(df) == 2

    def test_paginated_second_page(self, complex_api, complex_conn):
        df = complex_api.paginatedProducts(
            sort_column="product_name",
            page_size="2",
            page_offset="2",
        ).query(complex_conn)
        assert len(df) == 2

    def test_paginated_last_page(self, complex_api, complex_conn):
        df = complex_api.paginatedProducts(
            sort_column="product_name",
            page_size="2",
            page_offset="4",
        ).query(complex_conn)
        assert len(df) == 1  # Only 5 products, offset 4 => 1 left

    def test_paginated_with_filter(self, complex_api, complex_conn):
        df = complex_api.paginatedProducts(
            category="Gadgets",
            sort_column="price",
            page_size="10",
            page_offset="0",
        ).query(complex_conn)
        assert len(df) == 2  # Widget A and Widget B
        assert all(df["category"] == "Gadgets")

    def test_paginated_with_price_range(self, complex_api, complex_conn):
        df = complex_api.paginatedProducts(
            min_price=20.0,
            max_price=200.0,
            sort_column="price",
            page_size="10",
            page_offset="0",
        ).query(complex_conn)
        # Widget B (29.99), Gizmo X (149.99) -- within [20, 200]
        for _, row in df.iterrows():
            assert row["price"] >= 20.0
            assert row["price"] <= 200.0

    def test_paginated_column_names(self, complex_api, complex_conn):
        df = complex_api.paginatedProducts(
            sort_column="product_id",
            page_size="10",
            page_offset="0",
        ).query(complex_conn)
        assert list(df.columns) == ["product_id", "product_name", "category", "price"]


# --- UPDATE tests ---


class TestApiUpdateProduct:
    """Test complex UPDATE with many optional SET fields."""

    def test_update_single_field(self, complex_api, complex_conn):
        rows = complex_api.updateProduct(
            product_name="Widget A+",
            product_id=1,
        ).execute(complex_conn)
        assert rows == 1
        cur = complex_conn.cursor()
        cur.execute("SELECT product_name FROM products WHERE product_id=1")
        assert cur.fetchone()[0] == "Widget A+"

    def test_update_all_fields(self, complex_api, complex_conn):
        rows = complex_api.updateProduct(
            product_name="Super Widget",
            category="Premium",
            price=99.99,
            product_id=1,
        ).execute(complex_conn)
        assert rows == 1
        cur = complex_conn.cursor()
        cur.execute(
            "SELECT product_name, category, price FROM products WHERE product_id=1"
        )
        row = cur.fetchone()
        assert row[0] == "Super Widget"
        assert row[1] == "Premium"
        assert row[2] == pytest.approx(99.99)

    def test_update_price_only(self, complex_api, complex_conn):
        complex_api.updateProduct(price=5.99, product_id=5).execute(complex_conn)
        cur = complex_conn.cursor()
        cur.execute("SELECT price FROM products WHERE product_id=5")
        assert cur.fetchone()[0] == pytest.approx(5.99)

    def test_update_no_match(self, complex_api, complex_conn):
        rows = complex_api.updateProduct(
            product_name="X",
            product_id=999,
        ).execute(complex_conn)
        assert rows == 0


# --- INSERT tests ---


class TestApiInsertProduct:
    """Test INSERT with complex schema."""

    def test_insert_new_product(self, complex_api, complex_conn):
        rows = complex_api.insertProduct(
            product_name="New Thing",
            category="Gadgets",
            price=39.99,
        ).execute(complex_conn)
        assert rows == 1
        cur = complex_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products WHERE product_name='New Thing'")
        assert cur.fetchone()[0] == 1

    def test_insert_and_query_back(self, complex_api, complex_conn):
        complex_api.insertProduct(
            product_name="Thingamajig",
            category="Misc",
            price=4.99,
        ).execute(complex_conn)
        df = complex_api.paginatedProducts(
            category="Misc",
            sort_column="product_name",
            page_size="10",
            page_offset="0",
        ).query(complex_conn)
        names = list(df["product_name"])
        assert "Thingamajig" in names


# --- DELETE tests ---


class TestApiDeleteOrders:
    """Test DELETE with optional WHERE conditions."""

    def test_delete_by_status(self, complex_api, complex_conn):
        rows = complex_api.deleteOrders(status="cancelled").execute(complex_conn)
        assert rows == 1  # Order 5 was cancelled
        cur = complex_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='cancelled'")
        assert cur.fetchone()[0] == 0

    def test_delete_combined_conditions(self, complex_api, complex_conn):
        rows = complex_api.deleteOrders(
            status="pending",
            customer_id=2,
        ).execute(complex_conn)
        assert rows == 1  # Order 3

    def test_delete_no_match(self, complex_api, complex_conn):
        rows = complex_api.deleteOrders(status="nonexistent").execute(complex_conn)
        assert rows == 0


# --- Dynamic table name tests ---


class TestApiDynamicTable:
    """Test literal variable for table name."""

    def test_select_from_dynamic_table(self, complex_api, complex_conn):
        # Create a table that matches the template's id/name columns
        complex_conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        complex_conn.execute("INSERT INTO items (id, name) VALUES (1, 'alpha')")
        complex_conn.execute("INSERT INTO items (id, name) VALUES (2, 'beta')")
        complex_conn.commit()

        df = complex_api.selectFromDynamic(table_name="items").query(complex_conn)
        assert len(df) == 2

    def test_select_from_dynamic_table_with_filter(self, complex_api, complex_conn):
        # customer_name column is "name" in the template, so this works
        # with tables that have "name" column. Use customers which has customer_name.
        # Actually, let's just test it with the products table -- products has product_name not name.
        # Let's create a temp table that has 'name' column:
        complex_conn.execute(
            "CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT, active INTEGER)"
        )
        complex_conn.execute(
            "INSERT INTO tags (id, name, active) VALUES (1, 'alpha', 1)"
        )
        complex_conn.execute(
            "INSERT INTO tags (id, name, active) VALUES (2, 'beta', 0)"
        )
        complex_conn.commit()

        df = complex_api.selectFromDynamic(
            table_name="tags",
            name="alpha",
        ).query(complex_conn)
        assert len(df) == 1
        assert df.iloc[0]["name"] == "alpha"


# --- Customer order summary tests ---


class TestApiCustomerOrderSummary:
    """Test LEFT JOIN aggregation query."""

    def test_summary_all_customers(self, complex_api, complex_conn):
        df = complex_api.customerOrderSummary().query(complex_conn)
        assert len(df) == 3  # 3 customers
        assert "customer_name" in df.columns
        assert "num_orders" in df.columns

    def test_summary_shipped_only(self, complex_api, complex_conn):
        df = complex_api.customerOrderSummary(status="shipped").query(complex_conn)
        # Acme: 2 shipped, Globex: 1 shipped, Initech: 1 shipped
        # Only customers with shipped orders will appear (LEFT JOIN + WHERE on o.status)
        assert len(df) > 0

    def test_summary_ordered_by_count_desc(self, complex_api, complex_conn):
        df = complex_api.customerOrderSummary().query(complex_conn)
        counts = list(df["num_orders"])
        assert counts == sorted(counts, reverse=True)


# --- SQL build verification tests ---


class TestApiBuildSqlComplex:
    """Test that build_sql produces correct SQL strings for complex templates."""

    def test_build_sql_join_all_filters(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        sql = api.searchOrders(
            customer_name="Test",
            category="Cat",
            status="active",
        ).build_sql()
        assert "JOIN customers c" in sql
        assert "JOIN order_items oi" in sql
        assert "JOIN products p" in sql
        assert "WHERE" in sql
        assert "c.customer_name='Test'" in sql
        assert "p.category='Cat'" in sql
        assert "o.status='active'" in sql
        assert sql.count("AND") == 2

    def test_build_sql_join_no_filters(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        sql = api.searchOrders().build_sql()
        assert "WHERE" not in sql
        assert "JOIN" in sql

    def test_build_sql_pagination(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        sql = api.paginatedProducts(
            sort_column="price",
            page_size="25",
            page_offset="50",
        ).build_sql()
        assert "ORDER BY price" in sql
        assert "LIMIT 25 OFFSET 50" in sql
        assert "WHERE" not in sql

    def test_build_sql_update_two_of_three(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        sql = api.updateProduct(
            product_name="X",
            price=10.0,
            product_id=1,
        ).build_sql()
        assert "product_name='X'" in sql
        assert "price=10.0" in sql
        assert sql.count(",") == 1
        # category should not be in the SET clause
        assert "category=" not in sql

    def test_to_sql_and_build_sql_match(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        params = api.searchOrders(customer_name="Test")
        assert params.to_sql() == params.build_sql()


# --- Factory and introspection tests ---


class TestApiFactoryIntrospection:
    """Test factory properties and introspection."""

    def test_factory_input_vars(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        factory = api.searchOrders
        names = [v.value for v in factory.input_vars]
        assert "customer_name" in names
        assert "category" in names
        assert "date_from" in names
        assert "status" in names

    def test_factory_output_vars(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        factory = api.searchOrders
        names = [v.value for v in factory.output_vars]
        assert "order_id" in names
        assert "customer_name" in names
        assert "product_name" in names

    def test_statement_names_include_complex(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        names = api.statement_names
        assert "searchOrders" in names
        assert "salesReport" in names
        assert "paginatedProducts" in names
        assert "updateProduct" in names
        assert "deleteOrders" in names

    def test_snake_case_access_complex(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        factory = api.search_orders
        assert callable(factory)
        factory2 = api.sales_report
        assert callable(factory2)

    def test_getitem_access_complex(self):
        api = SQLGenApi(COMPLEX_TEMPLATE)
        factory = api["searchOrders"]
        assert callable(factory)
