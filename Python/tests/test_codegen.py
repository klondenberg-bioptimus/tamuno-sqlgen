"""Tests for the Python code generator."""

from __future__ import annotations

import sys
import types
import importlib
from pathlib import Path

import pytest

from tamuno_sqlgen.codegen import PythonCodeGenerator


SAMPLE_SQLG = Path(__file__).parent / "fixtures" / "sample.sqlg"


@pytest.fixture
def generator() -> PythonCodeGenerator:
    return PythonCodeGenerator()


@pytest.fixture
def sample_source() -> str:
    return SAMPLE_SQLG.read_text(encoding="utf-8")


def test_generate_returns_string(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert isinstance(code, str)
    assert len(code) > 0


def test_generated_code_has_imports(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert "import pandas as pd" in code
    assert "from tamuno_sqlgen" in code
    assert "import datetime" in code


def test_generated_code_has_dataclasses(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert "@dataclass" in code
    assert "SelectUserLoginParams" in code
    assert "SelectUserRow" in code or "SelectUserLoginRow" in code


def test_generated_code_has_factory_functions(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert "def selectUserLogin(" in code
    assert "def insertUser(" in code


def test_generated_code_is_valid_python(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    # Should not raise a SyntaxError
    compile(code, "<generated>", "exec")


def test_generated_code_can_be_executed(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_exec")
    sys.modules["_test_generated_exec"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)
        # Should have the factory function
        assert hasattr(module, "selectUserLogin")
        assert hasattr(module, "insertUser")
    finally:
        del sys.modules["_test_generated_exec"]


def test_generated_params_build_sql(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_build")
    sys.modules["_test_generated_build"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)
        params = module.selectUserLogin(user_name="alice", password="secret")
        sql = params.build_sql()
        assert "SELECT" in sql
        assert "alice" in sql
    finally:
        del sys.modules["_test_generated_build"]


def test_generated_insert_sql(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_insert")
    sys.modules["_test_generated_insert"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)
        params = module.insertUser(user_name="dave", active=1)
        sql = params.build_sql()
        assert "INSERT INTO users" in sql
        assert "'dave'" in sql
    finally:
        del sys.modules["_test_generated_insert"]


def test_generate_file_creates_file(generator, sample_source, tmp_path):
    src_path = tmp_path / "test.sqlg"
    src_path.write_text(sample_source, encoding="utf-8")
    target_path = tmp_path / "generated.py"
    generator.generate_file(str(src_path), str(target_path), "generated")
    assert target_path.exists()
    content = target_path.read_text(encoding="utf-8")
    assert "SelectUserLoginParams" in content


def test_generated_optional_params(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_optional")
    sys.modules["_test_generated_optional"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)

        # selectUser with no args
        params = module.selectUser()
        sql = params.build_sql()
        assert "WHERE" not in sql

        # selectUser with user_name
        params2 = module.selectUser(user_name="alice")
        sql2 = params2.build_sql()
        assert "WHERE" in sql2
        assert "alice" in sql2
    finally:
        del sys.modules["_test_generated_optional"]


# ==================== Complex codegen tests ====================


COMPLEX_TEMPLATE = """\
searchOrders:=
    SELECT @order_id:int, @customer_name:String, @product_name:String,
           @quantity:int, @unit_price:double, @order_date:Date
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
            [ WHERE
                [c.customer_name=$customer_name]
                [AND]
                [p.category=$category]
                [AND]
                [o.order_date >= $date_from:Date]
                [AND]
                [o.order_date <= $date_to:Date]
                [AND]
                [o.status=$status]
            ]
        ORDER BY o.order_date DESC;

salesReport:=
    SELECT @category:String,
           SUM(oi.quantity * oi.unit_price) as @total_revenue:double,
           COUNT(DISTINCT o.order_id) as @order_count:int
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        JOIN orders o ON oi.order_id = o.order_id
            [ WHERE [o.status=$status] ]
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
            [customer_id=$customer_id:int]
        ];

selectFromDynamic:=
    SELECT @id:int, @name:String
        FROM #table_name
            [ WHERE [name=$name] ]
        ORDER BY id;

advancedSearch:=
    SELECT @id:int, @name:String, @category:String, @price:double
        FROM products
        [ WHERE
            [name LIKE $name_pattern]
            {}
            [AND category=$category]
            {}
            [AND price >= $min_price:double]
            [AND]
            [price <= $max_price:double]
        ];
"""


def _exec_complex_module():
    """Generate and execute complex template code, returning the module."""
    gen = PythonCodeGenerator()
    code = gen.generate(COMPLEX_TEMPLATE, "complex_test")
    module = types.ModuleType("_test_complex_codegen")
    sys.modules["_test_complex_codegen"] = module
    exec(compile(code, "<complex_generated>", "exec"), module.__dict__)
    return module


class TestCodegenComplexTemplates:
    """Test code generation for complex SQL templates."""

    def test_complex_code_compiles(self):
        gen = PythonCodeGenerator()
        code = gen.generate(COMPLEX_TEMPLATE, "complex_test")
        compile(code, "<complex_generated>", "exec")

    def test_complex_code_has_all_factory_functions(self):
        gen = PythonCodeGenerator()
        code = gen.generate(COMPLEX_TEMPLATE, "complex_test")
        assert "def searchOrders(" in code
        assert "def salesReport(" in code
        assert "def paginatedProducts(" in code
        assert "def updateProduct(" in code
        assert "def insertProduct(" in code
        assert "def deleteOrders(" in code
        assert "def selectFromDynamic(" in code
        assert "def advancedSearch(" in code

    def test_complex_code_has_all_dataclasses(self):
        gen = PythonCodeGenerator()
        code = gen.generate(COMPLEX_TEMPLATE, "complex_test")
        assert "SearchOrdersParams" in code
        assert "SalesReportParams" in code
        assert "PaginatedProductsParams" in code
        assert "UpdateProductParams" in code
        assert "SearchOrdersRow" in code

    def test_complex_code_executes_without_error(self):
        module = _exec_complex_module()
        try:
            assert hasattr(module, "searchOrders")
            assert hasattr(module, "salesReport")
            assert hasattr(module, "paginatedProducts")
        finally:
            del sys.modules["_test_complex_codegen"]


class TestCodegenComplexBuildSql:
    """Test that generated code produces correct SQL strings."""

    def test_generated_search_all_filters(self):
        module = _exec_complex_module()
        try:
            params = module.searchOrders(
                customer_name="Acme Corp",
                category="Electronics",
                status="shipped",
            )
            sql = params.build_sql()
            assert "JOIN customers c" in sql
            assert "JOIN order_items oi" in sql
            assert "JOIN products p" in sql
            assert "WHERE" in sql
            assert "c.customer_name='Acme Corp'" in sql
            assert "p.category='Electronics'" in sql
            assert "o.status='shipped'" in sql
            assert sql.count("AND") == 2
            assert "ORDER BY o.order_date DESC" in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_search_no_filters(self):
        module = _exec_complex_module()
        try:
            params = module.searchOrders()
            sql = params.build_sql()
            assert "WHERE" not in sql
            assert "JOIN" in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_search_single_filter(self):
        module = _exec_complex_module()
        try:
            params = module.searchOrders(category="Books")
            sql = params.build_sql()
            assert "WHERE" in sql
            assert "p.category='Books'" in sql
            assert "AND" not in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_pagination(self):
        module = _exec_complex_module()
        try:
            params = module.paginatedProducts(
                sort_column="price",
                page_size="25",
                page_offset="50",
            )
            sql = params.build_sql()
            assert "ORDER BY price" in sql
            assert "LIMIT 25 OFFSET 50" in sql
            assert "WHERE" not in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_pagination_with_filter(self):
        module = _exec_complex_module()
        try:
            params = module.paginatedProducts(
                category="Electronics",
                min_price=50.0,
                sort_column="product_name",
                page_size="10",
                page_offset="0",
            )
            sql = params.build_sql()
            assert "WHERE" in sql
            assert "category='Electronics'" in sql
            assert "50.0" in sql
            assert "ORDER BY product_name" in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_update_all_fields(self):
        module = _exec_complex_module()
        try:
            params = module.updateProduct(
                product_name="Widget",
                category="Gadgets",
                price=19.99,
                product_id=1,
            )
            sql = params.build_sql()
            assert "product_name='Widget'" in sql
            assert "category='Gadgets'" in sql
            assert "price=19.99" in sql
            assert sql.count(",") == 2
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_update_single_field(self):
        module = _exec_complex_module()
        try:
            params = module.updateProduct(
                price=29.99,
                product_id=1,
            )
            sql = params.build_sql()
            assert "price=29.99" in sql
            assert "," not in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_insert(self):
        module = _exec_complex_module()
        try:
            params = module.insertProduct(
                product_name="New Item",
                category="Misc",
                price=5.99,
            )
            sql = params.build_sql()
            assert "INSERT INTO products" in sql
            assert "'New Item'" in sql
            assert "'Misc'" in sql
            assert "5.99" in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_delete_with_filter(self):
        module = _exec_complex_module()
        try:
            params = module.deleteOrders(status="cancelled")
            sql = params.build_sql()
            assert "DELETE FROM orders" in sql
            assert "status='cancelled'" in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_delete_no_filter(self):
        module = _exec_complex_module()
        try:
            params = module.deleteOrders()
            sql = params.build_sql()
            assert "DELETE FROM orders" in sql
            assert "WHERE" not in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_dynamic_table(self):
        module = _exec_complex_module()
        try:
            params = module.selectFromDynamic(
                table_name="products",
                name="Widget",
            )
            sql = params.build_sql()
            assert "FROM products" in sql
            assert "name='Widget'" in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_to_sql_alias(self):
        module = _exec_complex_module()
        try:
            params = module.searchOrders(customer_name="Test")
            assert params.to_sql() == params.build_sql()
        finally:
            del sys.modules["_test_complex_codegen"]


class TestCodegenComplexStopCombiner:
    """Test generated code with stop-combiner templates."""

    def test_generated_stop_combiner_all_groups(self):
        module = _exec_complex_module()
        try:
            params = module.advancedSearch(
                name_pattern="%widget%",
                category="Gadgets",
                min_price=10.0,
                max_price=100.0,
            )
            sql = params.build_sql()
            assert "name LIKE '%widget%'" in sql
            assert "AND category='Gadgets'" in sql
            assert "AND price >= 10.0" in sql
            assert "price <= 100.0" in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_stop_combiner_partial(self):
        module = _exec_complex_module()
        try:
            params = module.advancedSearch(min_price=5.0, max_price=50.0)
            sql = params.build_sql()
            assert "price >= 5.0" in sql
            assert "price <= 50.0" in sql
            # category should not appear in WHERE clause filter
            assert "AND category=" not in sql
            assert "name LIKE" not in sql
        finally:
            del sys.modules["_test_complex_codegen"]

    def test_generated_stop_combiner_none(self):
        module = _exec_complex_module()
        try:
            params = module.advancedSearch()
            sql = params.build_sql()
            assert "WHERE" not in sql
        finally:
            del sys.modules["_test_complex_codegen"]


class TestCodegenFile:
    """Test code generation to file with complex templates."""

    def test_generate_complex_file(self, tmp_path):
        gen = PythonCodeGenerator()
        src_path = tmp_path / "complex.sqlg"
        src_path.write_text(COMPLEX_TEMPLATE, encoding="utf-8")
        target_path = tmp_path / "generated_complex.py"
        gen.generate_file(str(src_path), str(target_path), "generated_complex")
        assert target_path.exists()
        content = target_path.read_text(encoding="utf-8")
        assert "SearchOrdersParams" in content
        assert "def searchOrders(" in content
        assert "def paginatedProducts(" in content

    def test_generated_complex_file_is_valid_python(self, tmp_path):
        gen = PythonCodeGenerator()
        src_path = tmp_path / "complex.sqlg"
        src_path.write_text(COMPLEX_TEMPLATE, encoding="utf-8")
        target_path = tmp_path / "generated_complex.py"
        gen.generate_file(str(src_path), str(target_path), "generated_complex")
        content = target_path.read_text(encoding="utf-8")
        compile(content, str(target_path), "exec")
