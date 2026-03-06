# Tamuno SQL Generator

Tamuno-sqlgen is a SQL template engine that turns a concise DSL into type-safe, ready-to-execute SQL code. You write your queries once in `.sqlg` template files using a simple syntax for typed variables, optional clauses, and combiners, and the generator produces language-specific classes (Java) or dataclasses (Python) that build the final SQL strings at runtime.

## Why?

Most applications need dynamic SQL: queries where filters, SET clauses, or entire JOIN branches appear or disappear depending on user input. The common solutions each come with trade-offs:

- **String concatenation** is fragile, error-prone, and hard to read.
- **ORM query builders** abstract SQL away behind a language-specific API, but that abstraction has a cost.

Tamuno-sqlgen occupies the middle ground: you write **real SQL** enriched with a lightweight template syntax, and the tooling generates type-safe code around it.

## Template Syntax at a Glance

```sql
-- queries.sqlg

selectUser:=
    SELECT @user_id:int, @user_name:String, @birthdate:Date
        FROM users
            [ WHERE
                [user_name=$user_name] [AND] [active=$active:int]
            ]
        LIMIT 10;

updateUser:=
    UPDATE users SET
        [user_name=$user_name] [,] [active=$active:int]
    WHERE user_id=$user_id:int;
```

| Syntax | Meaning |
|--------|---------|
| `@name:type` | Output column (result set) |
| `$name:type` | Escaped input variable |
| `#name:type` | Literal (unescaped) input variable |
| `?name:type` | Option variable (metadata only) |
| `[...]` | Optional section - included only if its variables are provided |
| `[AND]`, `[,]` | Combiner - included only if the preceding section was included |
| `{}` | Stop-combiner - resets combiner state |
| `\` | Escape symbol - to use $?#[]{} in your SQL |


Optional sections can nest, and the engine handles the combiners (`AND`, `,`, `OR`, etc.) automatically so you never end up with a dangling `WHERE AND` or a trailing comma.

## Why not an ORM?

If you are happy with your ORM, keep using it. ORMs are a fine choice for many applications, especially those that are mostly CRUD on single tables. Tamuno-sqlgen is for developers who want to write their own SQL but would still like a type-safe, generated API around it - without resorting to fragile string concatenation.

Once queries grow beyond the basics, ORMs tend to get in the way:

- **Lowest-common-denominator SQL.** ORMs generate portable SQL, which means you lose access to vendor-specific features: window functions, CTEs, lateral joins, partial indexes, `RETURNING` clauses, and database-specific hints.
- **Opaque query generation.** When an ORM produces a slow query, debugging means reverse-engineering the generated SQL and fighting the API to make it emit something better. With tamuno-sqlgen the SQL is right there in the template - what you write is what gets executed.
- **Object-mapping overhead.** ORMs hydrate full entity graphs by default, pulling columns you don't need. For reporting queries, bulk exports, or dashboards, this is wasteful. Tamuno-sqlgen builds a flat SQL string; you decide how to consume the results.
- **Difficult partial updates.** Updating only the fields that changed is awkward in most ORMs. In tamuno-sqlgen, you write `UPDATE ... SET [col=$col] [,] [col2=$col2]` and only the provided fields appear in the final SQL.
- **N+1 and eager-loading traps.** ORMs shift the responsibility for efficient data fetching onto the developer through lazy/eager loading configuration. With explicit SQL templates you fetch exactly the data you need in a single round-trip.

## SQL is already an abstraction layer

SQL is a declarative, set-oriented language with decades of optimization behind it. It abstracts away storage layout, access paths, join algorithms, and parallelism - and modern query planners are remarkably good at it. Rewriting SQL in an ORM's bespoke API is not a step up in abstraction; it is a lateral move into a narrower language that is specific to one library and one programming language. The SQL itself would work unchanged across all of them.

ORMs justify this trade by offering type safety and IDE integration: autocompletion, compile-time checks, refactoring support. These are real benefits. But tamuno-sqlgen delivers them without the ORM baggage. The `.sqlg` template is plain SQL - portable, readable by any DBA, and able to use every feature your database offers. The code generator wraps it in typed, language-specific APIs so you get autocompletion and type checking without surrendering control over the query.

## Implementations

### [Java](Java/)

The original implementation (2007). Includes:

- **[sqlgen](Java/sqlgen/)** - Core library: DSL parser, code generator, and a JDBC-based runtime (`BaseSQLExecutor`, `RowIterator`, dialect utilities).
- **[sqlgen-maven-plugin](Java/sqlgen-maven-plugin/)** - Maven plugin to run code generation as part of your build.
- An Ant task (`TamunoSQLCodeGeneratorTask`) for Ant-based builds.

### [Python](Python/)

A full Python port with a Pythonic API. Includes:

- On-the-fly template parsing and query execution via `SQLGenApi`.
- Code generation that emits dataclasses with typed fields (`PythonCodeGenerator`).
- Pandas DataFrame integration for SELECT queries.
- SQLAlchemy compatibility (use `build_sql()` with `text()`).
- Dialect support (ANSI SQL, MySQL).

See the [Python README](Python/README.md) for detailed API documentation and examples.

## License

Apache License 2.0

## Author

Kai Londenberg - Kai.Londenberg@googlemail.com
