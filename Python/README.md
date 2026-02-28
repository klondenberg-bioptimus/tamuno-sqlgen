# tamuno-sqlgen Python

A Python port of the [tamuno-sqlgen](../sqlgen/) Java SQL template engine. It parses a custom SQL template DSL and provides a Pythonic API for type-safe SQL generation, execution, and code generation.

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

### Escaping

Use `\` to escape special characters (`[`, `]`, `$`, `#`, `@`, `?`, `{`, `}`).

No parsing is done inside string literals `'...'` or `"..."`.

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

## Running Tests

```bash
cd Python
pip install -r requirements.txt
pytest tests/ -v
```
