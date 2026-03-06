# tamuno-sqlgen Python

A Python port of the [tamuno-sqlgen](../Java/sqlgen/) Java SQL template engine. It parses a custom SQL template DSL and provides a Pythonic API for type-safe SQL generation, execution, and code generation.

## Overview

tamuno-sqlgen lets you write SQL templates with typed variables and optional sections. It handles:

- **Typed output columns** (`@name:type`) → named DataFrame columns
- **Escaped input variables** (`$name:type`) → SQL-escaped values (e.g. `'value'`)
- **Literal input variables** (`#name:type`) → raw SQL injection (table names, etc.)
- **Option variables** (`?name:type`) → metadata only, no SQL emitted
- **Optional sections** (`[...]`) → included only if all required input vars are provided
- **Alternative sections** → optional sections containing only other optional sections (included if at least one inner section is included)
- **Combiner sections** (`[AND]`, `[,]`) → included only if the previous expression was included

## Installation

```bash
pip install -r requirements.txt
```

Or install the package directly:

```bash
pip install -e .
```

## Getting Started

### Define your SQL templates in a `.sqlg` file

```sql
-- queries.sqlg

selectUser:=
    SELECT @user_id:int, @user_name:String, @birthdate:Date
        FROM users
            [ WHERE
                [user_name=$user_name] [AND] [active=$active:int]
            ]
        LIMIT 10;

insertUser:=
    INSERT INTO users (user_name, active) VALUES ($user_name, $active:int);

updateUser:=
    UPDATE users SET
        [user_name=$user_name] [,] [active=$active:int]
    WHERE user_id=$user_id:int;
```

### Use the API directly (on-the-fly)

```python
import sqlite3
from tamuno_sqlgen import SQLGenApi

api = SQLGenApi.from_file("queries.sqlg")

conn = sqlite3.connect("mydb.sqlite")

# Build and run a SELECT query → returns a pandas DataFrame
df = api.select_user(user_name="alice").query(conn)
print(df)

# Query with multiple optional filters
df2 = api.select_user(user_name="alice", active=1).query(conn)

# Query with no filters (all optional sections omitted)
df_all = api.select_user().query(conn)

# INSERT
rows = api.insert_user(user_name="dave", active=1).execute(conn)
print(f"Inserted {rows} row(s)")

# UPDATE with optional fields
api.update_user(user_name="dave_new", user_id=4).execute(conn)

# Just build the SQL string
sql = api.select_user(user_name="alice").build_sql()
print(sql)
```

### Generate Python source files

```python
from tamuno_sqlgen import PythonCodeGenerator

gen = PythonCodeGenerator()
gen.generate_file("queries.sqlg", "generated_queries.py", "my_module")
```

The generated file contains dataclasses and factory functions:

```python
# generated_queries.py (auto-generated)

from generated_queries import selectUser, insertUser

# Use directly
params = selectUser(user_name="alice")
df = params.query(conn)
sql = params.build_sql()
```

## Template Syntax

### Statement definition

```
statementName:= SQL TEMPLATE;
```

A statement is terminated by `;` at the end of a line.

### Variables

| Syntax | Description |
|--------|-------------|
| `@name:type` | Output/result column |
| `$name:type` | Escaped input variable (SQL-escaped, e.g. `'value'`) |
| `#name:type` | Literal input variable (raw SQL, e.g. table names) |
| `?name:type` | Option variable (metadata only, no SQL emitted) |

### Type Mappings

| DSL Type | Python Type |
|----------|-------------|
| `String` | `str` |
| `int` | `int` |
| `long` | `int` |
| `double` | `float` |
| `float` | `float` |
| `short` | `int` |
| `boolean` | `bool` |
| `byte` | `int` |
| `bytes` | `bytes` |
| `decimal` | `decimal.Decimal` |
| `Date` | `datetime.date` |
| `Time` | `datetime.time` |
| `Timestamp` | `datetime.datetime` |

The default type (when `:type` is omitted) is `String`.

### Optional sections

```sql
[ WHERE x=$x ]
```

Included only if all required input variables inside are provided.

### Alternative sections

An optional section that contains only other optional sections - included if at least one inner section is included:

```sql
[ WHERE [x=$x] [AND] [y=$y:int] ]
```

### Combiner sections

An optional section with no variables and no sub-sections (e.g. `[AND]`, `[,]`) - included only if the **previous** expression was included:

```sql
[field1=$f1] [,] [field2=$f2]
```

### Stop-combiner

`{}` resets the "combine" flag:

```sql
[x=$x] [AND] {} [y=$y:int]
```

### Escaping special characters

The characters `[`, `]`, `{`, `}`, `$`, `#`, `@`, and `?` have special meaning in the template DSL. To include them as literal text in the generated SQL, prefix them with a backslash (`\`).

```sql
literalChars:=
    SELECT \$price, \#channel, \@mention, \?placeholder,
           \[array_access\], \{json_path\}
        FROM t;
```

The generated SQL contains the characters verbatim:

```
SELECT $price, #channel, @mention, ?placeholder,
       [array_access], {json_path}
    FROM t
```

This is useful when your target SQL dialect requires these characters as part of the query itself. For example:

- **PostgreSQL** uses `$1`, `$2` for prepared-statement positional parameters.
- **MySQL** uses `#` for comments and `@` for user-defined variables (`@rownum`).
- **SQL Server** uses `[schema].[table]` for quoted identifiers.
- **PostgreSQL JSONB** uses `@>`, `?`, `?|`, `?&` as operators.

#### Escaping the backslash itself

Since `\` is the escape character, you need to double it to produce a literal backslash in the output:

```sql
backslashExample:=
    SELECT * FROM t WHERE path LIKE 'C:\\\\Users\\\\%';
```

Note: inside quoted strings (`'...'` or `"..."`), the template engine does **not** interpret special characters, so `$`, `#`, `@`, `?`, `[`, `]`, `{`, `}` are passed through as-is. However, `\` is still processed inside quotes (and preserved together with the following character), so a `\\` inside a quoted string produces `\\` in the output - which is typically what you want for SQL string literals.

#### Combining escaped backslash with a variable

A double backslash produces a literal `\`. If a variable marker follows immediately after, it is still recognized as a variable:

```sql
pathQuery:=
    SELECT * FROM t WHERE path=\\$user_path;
```

```python
api.path_query(user_path="docs").build_sql()
# → SELECT * FROM t WHERE path=\'docs'
```

#### Summary

| Template | Output |
|----------|--------|
| `\$x` | `$x` (literal dollar, not a variable) |
| `\#x` | `#x` (literal hash) |
| `\@x` | `@x` (literal at-sign) |
| `\?x` | `?x` (literal question mark) |
| `\[` | `[` (literal bracket) |
| `\]` | `]` (literal bracket) |
| `\{` | `{` (literal brace) |
| `\}` | `}` (literal brace) |
| `\\` | `\` (literal backslash) |
| `\\$x` | `\` followed by the value of variable `$x` |

#### No parsing inside string literals

The template engine does not interpret special characters inside SQL string literals delimited by single quotes (`'...'`) or double quotes (`"..."`). This means you can safely write:

```sql
example:=
    SELECT * FROM t WHERE label='$not_a_var [not_a_bracket]';
```

The `$not_a_var` and `[not_a_bracket]` are **not** parsed - they appear verbatim in the output.

## Python API Reference

### `SQLGenApi`

```python
from tamuno_sqlgen import SQLGenApi

api = SQLGenApi(source_string, dialect=None)
api = SQLGenApi.from_file("path/to/queries.sqlg", dialect=None)

# Access statements by camelCase name or snake_case
factory = api.selectUser       # exact name
factory = api.select_user      # snake_case → camelCase

# Get all statement names
names = api.statement_names    # ['selectUser', 'insertUser', ...]

# Build SQL directly
sql = api.build_sql("selectUser", user_name="alice")
```

### `QueryFactory` (returned by `api.statementName`)

```python
factory = api.selectUser

# Create a params instance
params = factory(user_name="alice", active=1)

# Or use keyword arguments directly
params = api.selectUser(user_name="alice")
```

### `QueryParams` (returned by factory call)

```python
params = api.selectUser(user_name="alice")

# Build SQL string
sql = params.build_sql()          # str
sql = params.to_sql()             # alias for build_sql()

# Execute SELECT → DataFrame
df = params.query(conn)           # pd.DataFrame

# Execute INSERT/UPDATE/DELETE → affected row count
rows = params.execute(conn)       # int
```

### Dialects

```python
from tamuno_sqlgen import SQLDialect, MySQLDialect

# Default ANSI SQL (single quotes doubled: O'Brien → 'O''Brien')
dialect = SQLDialect()

# MySQL (backslash escaping: O'Brien → 'O\'Brien')
dialect = MySQLDialect()

api = SQLGenApi.from_file("queries.sqlg", dialect=dialect)
```

### `PythonCodeGenerator`

```python
from tamuno_sqlgen import PythonCodeGenerator

gen = PythonCodeGenerator()

# Generate code string
code = gen.generate(source_string, module_name="mymodule")

# Generate file
gen.generate_file("queries.sqlg", "generated.py", module_name="mymodule")

# With custom dialect
gen.generate_file("queries.sqlg", "generated.py", "mymodule", dialect_class="MySQLDialect")
```

## Manual Testing Guide

Here's how to test with a real SQLite database in a Python REPL:

```python
import sqlite3
from tamuno_sqlgen import SQLGenApi

# Create an in-memory database
conn = sqlite3.connect(":memory:")
conn.execute("""
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY,
        user_name TEXT,
        birthdate TEXT,
        active INTEGER DEFAULT 1,
        password_hash TEXT
    )
""")
conn.execute("INSERT INTO users VALUES (1, 'alice', '1990-01-15', 1, 'hash_alice')")
conn.execute("INSERT INTO users VALUES (2, 'bob', '1985-06-20', 0, 'hash_bob')")
conn.commit()

# Load templates
TEMPLATE = """
selectUser:=
    SELECT @user_id:int, @user_name:String, @birthdate:Date
        FROM users
            [ WHERE
                [user_name=$user_name] [AND] [active=$active:int]
            ]
        LIMIT 10;

insertUser:=
    INSERT INTO users (user_name, active) VALUES ($user_name, $active:int);
"""

api = SQLGenApi(TEMPLATE)

# Query all users (no WHERE clause)
print(api.selectUser().query(conn))

# Query with filter
print(api.selectUser(user_name="alice").query(conn))

# Query active users
print(api.selectUser(active=1).query(conn))

# Check the SQL being generated
print(api.selectUser(user_name="alice", active=1).build_sql())

# Insert a new user
api.insertUser(user_name="carol", active=1).execute(conn)
print(api.selectUser().query(conn))
```

## Advanced Examples

The examples below demonstrate real-world usage patterns with multi-table JOINs, dynamic SQL, aggregations, pagination, and more.

### Multi-table JOIN with dynamic filters

A common pattern is searching across joined tables with any combination of optional filters:

```sql
-- orders.sqlg

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
```

```python
from tamuno_sqlgen import SQLGenApi

api = SQLGenApi.from_file("orders.sqlg")

# All orders — no WHERE clause generated
df = api.search_orders().query(conn)

# Filter by customer only
df = api.search_orders(customer_name="Alice").query(conn)

# Combine multiple filters — AND combiners appear automatically
df = api.search_orders(
    customer_name="Alice",
    status="shipped",
    date_from=date(2024, 1, 1),
    date_to=date(2024, 12, 31),
).query(conn)

# Just inspect the SQL
print(api.search_orders(category="Electronics").build_sql())
# SELECT ... FROM orders o JOIN customers c ON ... JOIN ...
#   WHERE p.category='Electronics' ORDER BY o.order_date DESC
```

### Aggregation with GROUP BY and optional HAVING

Use optional sections in HAVING to create flexible reporting queries:

```sql
salesReport:=
    SELECT @category:String, @total_revenue:double,
           @order_count:int, @avg_price:double
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        JOIN orders o ON oi.order_id = o.order_id
            [ WHERE
                [o.order_date >= $date_from:Date]
                [AND]
                [o.order_date <= $date_to:Date]
                [AND]
                [o.status=$status]
            ]
        GROUP BY p.category
            [ HAVING
                [SUM(oi.quantity * oi.unit_price) >= $min_revenue:double]
                [AND]
                [COUNT(DISTINCT o.order_id) >= $min_orders:int]
            ]
        ORDER BY total_revenue DESC;
```

```python
# Full report — no WHERE, no HAVING
df = api.sales_report().query(conn)

# Only shipped orders with minimum revenue threshold
df = api.sales_report(
    status="shipped",
    min_revenue=1000.0,
).query(conn)

# Date range + minimum order count
df = api.sales_report(
    date_from=date(2024, 1, 1),
    date_to=date(2024, 6, 30),
    min_orders=5,
).query(conn)
```

### Pagination with literal variables

Literal variables (`#var`) inject raw values into SQL — useful for column names, sort directions, and pagination parameters that should not be quoted:

```sql
paginatedProducts:=
    SELECT @product_id:int, @product_name:String, @category:String,
           @price:double, @stock:int
        FROM products
            [ WHERE
                [category=$category]
                [AND]
                [price >= $min_price:double]
                [AND]
                [price <= $max_price:double]
                [AND]
                [stock > $min_stock:int]
            ]
        ORDER BY #sort_column #sort_direction
        LIMIT #page_size OFFSET #page_offset;
```

```python
# Page 1, 20 items, sorted by price descending
df = api.paginated_products(
    sort_column="price",
    sort_direction="DESC",
    page_size="20",
    page_offset="0",
).query(conn)

# Page 2 with category filter
df = api.paginated_products(
    category="Electronics",
    sort_column="product_name",
    sort_direction="ASC",
    page_size="20",
    page_offset="20",
).query(conn)
```

### Dynamic UPDATE with optional SET fields

When updating records, you often want to set only the fields that were provided. The `[,]` combiner handles comma placement automatically:

```sql
updateProduct:=
    UPDATE products SET
        [product_name=$product_name] [,]
        [category=$category] [,]
        [price=$price:double] [,]
        [stock=$stock:int] [,]
        [description=$description]
    WHERE product_id=$product_id:int;
```

```python
# Update only the price
api.update_product(product_id=42, price=29.99).execute(conn)
# → UPDATE products SET price=29.99 WHERE product_id=42

# Update name and stock — comma appears between them
api.update_product(
    product_id=42,
    product_name="Widget Pro",
    stock=100,
).execute(conn)
# → UPDATE products SET product_name='Widget Pro' , stock=100
#     WHERE product_id=42

# Update everything
api.update_product(
    product_id=42,
    product_name="Widget Pro",
    category="Gadgets",
    price=29.99,
    stock=100,
    description="The best widget",
).execute(conn)
```

### INSERT from SELECT with dynamic target table

Combine literal variables for table names with escaped variables for filters:

```sql
copyOrderItems:=
    INSERT INTO #target_table (order_id, product_id, quantity, unit_price)
        SELECT oi.order_id, oi.product_id, oi.quantity, oi.unit_price
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status=$status
                [AND o.order_date >= $date_from:Date]
                [AND o.order_date <= $date_to:Date];
```

```python
# Copy shipped order items to an archive table
api.copy_order_items(
    target_table="archived_items",
    status="shipped",
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
).execute(conn)
```

### Stop-combiners for independent filter groups

The `{}` stop-combiner resets the combiner state, allowing you to create independent groups of conditions where an `AND` only appears if the preceding condition *within the same group* was included:

```sql
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
```

```python
# Only price range — the "AND" before category is independent,
# so it appears even without name_pattern
api.advanced_search(min_price=10.0, max_price=50.0).build_sql()
# → SELECT ... FROM products WHERE AND price >= 10.0 AND price <= 50.0

# Only category
api.advanced_search(category="Books").build_sql()
# → SELECT ... FROM products WHERE AND category='Books'

# All filters
api.advanced_search(
    name_pattern="%widget%",
    category="Electronics",
    min_price=10.0,
    max_price=100.0,
).build_sql()
```

### Code generation for type-safe usage

Generate Python source code from your templates for IDE autocompletion and type checking:

```python
from tamuno_sqlgen import PythonCodeGenerator

gen = PythonCodeGenerator()
gen.generate_file("orders.sqlg", "generated_orders.py", "orders_module")
```

The generated file contains dataclasses with typed fields and factory functions:

```python
# generated_orders.py (auto-generated)
from dataclasses import dataclass
from typing import Optional

@dataclass
class SearchordersParams:
    customer_name: Optional[str] = None
    category: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    status: Optional[str] = None

    def build_sql(self) -> str: ...
    def to_sql(self) -> str: ...
    def query(self, conn) -> pd.DataFrame: ...
    def execute(self, conn) -> int: ...

def searchOrders(**kwargs) -> SearchordersParams: ...
```

### Factory introspection

Inspect the parsed metadata for a statement at runtime:

```python
api = SQLGenApi.from_file("orders.sqlg")
factory = api.search_orders

# Input variables (parameters the query accepts)
for var in factory.input_vars:
    print(f"  {var.value}: {var.vartype}")
# customer_name: String
# category: String
# date_from: Date
# date_to: Date
# status: String

# Output variables (columns returned)
for var in factory.output_vars:
    print(f"  {var.value}: {var.vartype}")
# order_id: int
# customer_name: String
# product_name: String
# quantity: int
# unit_price: double
# order_date: Date

# All available statements
print(api.statement_names)
```

## Using with SQLAlchemy

tamuno-sqlgen generates raw SQL strings, which makes it easy to use with SQLAlchemy's `text()` and connection/engine API. This lets you combine tamuno-sqlgen's dynamic SQL templating with SQLAlchemy's connection management, transactions, and ORM ecosystem.

### Setup

Install SQLAlchemy alongside tamuno-sqlgen:

```bash
pip install sqlalchemy
```

### Basic usage with SQLAlchemy engine

```python
from sqlalchemy import create_engine, text
from tamuno_sqlgen import SQLGenApi

engine = create_engine("sqlite:///mydb.sqlite")
api = SQLGenApi.from_file("orders.sqlg")

# Build the SQL with tamuno-sqlgen, execute with SQLAlchemy
sql = api.search_orders(customer_name="Alice", status="shipped").build_sql()

with engine.connect() as conn:
    result = conn.execute(text(sql))
    rows = result.fetchall()
    for row in rows:
        print(row)
```

### Using pandas with SQLAlchemy engine

Since `pandas.read_sql_query` accepts SQLAlchemy connections, you can use them directly with tamuno-sqlgen's `.query()` method:

```python
import pandas as pd
from sqlalchemy import create_engine
from tamuno_sqlgen import SQLGenApi

engine = create_engine("postgresql://user:pass@localhost/mydb")
api = SQLGenApi.from_file("orders.sqlg")

# Option 1: Use tamuno-sqlgen's built-in query() with a SQLAlchemy connection
with engine.connect() as conn:
    df = api.search_orders(status="shipped").query(conn)
    print(df)

# Option 2: Build SQL manually and use pd.read_sql_query
sql = api.search_orders(
    date_from=date(2024, 1, 1),
    date_to=date(2024, 6, 30),
).build_sql()

with engine.connect() as conn:
    df = pd.read_sql_query(sql, conn)
```

### Transactions

Use SQLAlchemy's transaction support for multi-statement operations:

```python
from sqlalchemy import create_engine, text
from tamuno_sqlgen import SQLGenApi

engine = create_engine("sqlite:///mydb.sqlite")
api = SQLGenApi.from_file("orders.sqlg")

# Atomic operation: archive old orders and delete originals
with engine.begin() as conn:
    # Copy shipped items to archive
    copy_sql = api.copy_order_items(
        target_table="archived_items",
        status="shipped",
        date_from=date(2023, 1, 1),
        date_to=date(2023, 12, 31),
    ).build_sql()
    conn.execute(text(copy_sql))

    # Delete the archived orders
    delete_sql = api.delete_orders(
        status="shipped",
        before_date=date(2024, 1, 1),
    ).build_sql()
    conn.execute(text(delete_sql))

    # Both statements commit together, or roll back on error
```

### Connection pooling and multiple databases

```python
from sqlalchemy import create_engine
from tamuno_sqlgen import SQLGenApi, MySQLDialect, SQLDialect

# PostgreSQL with ANSI dialect (default)
pg_engine = create_engine("postgresql://user:pass@pghost/mydb", pool_size=10)
pg_api = SQLGenApi.from_file("orders.sqlg")

# MySQL with MySQL dialect (backslash escaping)
mysql_engine = create_engine("mysql+pymysql://user:pass@myhost/mydb", pool_size=10)
mysql_api = SQLGenApi.from_file("orders.sqlg", dialect=MySQLDialect())

# Same template, different dialects
with pg_engine.connect() as conn:
    df_pg = pg_api.search_orders(customer_name="O'Brien").query(conn)
    # Uses: customer_name='O''Brien'  (ANSI doubling)

with mysql_engine.connect() as conn:
    df_mysql = mysql_api.search_orders(customer_name="O'Brien").query(conn)
    # Uses: customer_name='O\'Brien'  (MySQL backslash)
```

### Building a query service layer

Combine tamuno-sqlgen templates with a SQLAlchemy-backed service class for clean separation of concerns:

```python
from datetime import date
from sqlalchemy import create_engine, text
from tamuno_sqlgen import SQLGenApi


class OrderService:
    """Service layer using tamuno-sqlgen for SQL and SQLAlchemy for execution."""

    def __init__(self, engine, sqlg_path="orders.sqlg"):
        self.engine = engine
        self.api = SQLGenApi.from_file(sqlg_path)

    def search(self, **filters):
        """Search orders with any combination of filters."""
        with self.engine.connect() as conn:
            return self.api.search_orders(**filters).query(conn)

    def get_report(self, **filters):
        """Get sales report grouped by category."""
        with self.engine.connect() as conn:
            return self.api.sales_report(**filters).query(conn)

    def get_products_page(self, page=1, page_size=20,
                          sort_by="product_name", sort_dir="ASC", **filters):
        """Get a paginated page of products."""
        offset = (page - 1) * page_size
        with self.engine.connect() as conn:
            return self.api.paginated_products(
                sort_column=sort_by,
                sort_direction=sort_dir,
                page_size=str(page_size),
                page_offset=str(offset),
                **filters,
            ).query(conn)

    def update_product(self, product_id, **fields):
        """Update a product, setting only the provided fields."""
        with self.engine.begin() as conn:
            sql = self.api.update_product(product_id=product_id, **fields).build_sql()
            conn.execute(text(sql))

    def archive_orders(self, status, date_from, date_to):
        """Archive orders in a single transaction."""
        with self.engine.begin() as conn:
            copy_sql = self.api.copy_order_items(
                target_table="archived_items",
                status=status,
                date_from=date_from,
                date_to=date_to,
            ).build_sql()
            conn.execute(text(copy_sql))

            delete_sql = self.api.delete_orders(
                status=status,
                before_date=date_to,
            ).build_sql()
            conn.execute(text(delete_sql))


# Usage
engine = create_engine("sqlite:///shop.db")
svc = OrderService(engine)

# Search
df = svc.search(customer_name="Alice", status="shipped")

# Paginated product listing
page1 = svc.get_products_page(page=1, sort_by="price", sort_dir="DESC")
page2 = svc.get_products_page(page=2, sort_by="price", sort_dir="DESC",
                               category="Electronics")

# Partial update
svc.update_product(42, price=29.99, stock=100)

# Archive old shipped orders
svc.archive_orders("shipped", date(2023, 1, 1), date(2023, 12, 31))
```

### Using with SQLAlchemy ORM sessions

If your project uses SQLAlchemy ORM, you can still leverage tamuno-sqlgen for complex custom queries that are easier to express as templates:

```python
from sqlalchemy import text
from sqlalchemy.orm import Session

from tamuno_sqlgen import SQLGenApi

api = SQLGenApi.from_file("orders.sqlg")

# Within an ORM session
with Session(engine) as session:
    sql = api.sales_report(
        status="shipped",
        min_revenue=500.0,
    ).build_sql()

    # Execute raw SQL within the session
    result = session.execute(text(sql))
    for row in result:
        print(f"{row[0]}: ${row[1]:.2f} revenue, {row[2]} orders")

    # Modifications through tamuno-sqlgen
    update_sql = api.update_product(
        product_id=42,
        price=24.99,
    ).build_sql()
    session.execute(text(update_sql))
    session.commit()
```

## Running Tests

```bash
cd Python
pip install -r requirements.txt
pytest tests/ -v
```
