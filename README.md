# Tamuno SQL Generator

Tamuno-sqlgen is a SQL template engine that turns a concise DSL into type-safe, ready-to-execute SQL code. You write your queries once in `.sqlg` template files using a simple syntax for typed variables, optional clauses, and combiners, and the generator produces language-specific classes (Java) or dataclasses (Python) that build the final SQL strings at runtime.

## Why?

Most applications need dynamic SQL: queries where filters, SET clauses, or entire JOIN branches appear or disappear depending on user input. The common solutions each come with trade-offs:

- **String concatenation** is fragile, error-prone, and hard to read.
- **ORM query builders** abstract SQL away behind a language-specific API, but that abstraction has a cost.

Tamuno-sqlgen occupies the middle ground: you write **real SQL** enriched with a lightweight template syntax, and the tooling generates type-safe code around it.

## Why not an ORM?

ORMs are convenient for simple CRUD on single tables, but they become a liability when your queries grow beyond the basics:

- **Lowest-common-denominator SQL.** ORMs generate SQL that works across databases, which means you lose access to vendor-specific features: window functions, CTEs, lateral joins, partial indexes, `RETURNING` clauses, database-specific hints, and other advanced constructs that can make the difference between a query that takes seconds and one that takes milliseconds.
- **Opaque query generation.** When an ORM produces a slow query, debugging means reverse-engineering the generated SQL, understanding the ORM's internal decisions about join strategy and subquery placement, and then fighting the API to make it emit something better. With tamuno-sqlgen the SQL is right there in the template - what you write is what gets executed.
- **Object-mapping overhead.** ORMs hydrate full entity graphs by default, pulling columns you don't need and materializing object trees in memory. For reporting queries, bulk exports, or dashboards that return thousands of rows, this is wasteful. Tamuno-sqlgen builds a flat SQL string; you decide how to consume the results - as a DataFrame, a stream of rows, or a lightweight DTO - with no hidden allocations.
- **Difficult partial updates.** Updating only the fields that changed is awkward in most ORMs (dirty tracking, merge semantics, detached entities). In tamuno-sqlgen, you write `UPDATE ... SET [col=$col] [,] [col2=$col2]` and only the provided fields appear in the final SQL. No magic, no surprises.
- **N+1 and eager-loading traps.** ORMs shift the responsibility for efficient data fetching onto the developer through lazy/eager loading configuration, and getting it wrong means silent performance disasters. With explicit SQL templates you fetch exactly the data you need in a single round-trip.

In short, tamuno-sqlgen is for projects where you want **full control over the SQL** that hits your database, with the safety and convenience of generated, typed APIs around it.

## SQL is already an abstraction layer

It is worth stepping back and recognizing what SQL actually is: a declarative, set-oriented query language with decades of optimization behind it. It abstracts away storage layout, access paths, join algorithms, and parallelism. The database's query planner does the work of turning your declarative intent into an efficient execution plan - and modern planners are remarkably good at it. SQL is, arguably, a better abstraction layer than anything an ORM puts on top of it.

If you already know SQL - and most backend developers do - then rewriting your queries in an ORM's bespoke API is not a step up in abstraction. It is a lateral move into a different, narrower language that happens to be embedded in your programming language. You trade the universality of SQL for a wrapper that is, by definition, specific to one programming language and one library. The Hibernate query you wrote in Java is useless when you move to Python. The SQLAlchemy expression you crafted in Python does not transfer to C#. The SQL itself would work in all of them unchanged.

ORMs justify this trade by offering type safety and integration with the host language's tooling: autocompletion, compile-time checks, refactoring support. These are real benefits. Nobody wants to debug a misspelled column name at runtime. But the ORM bundles those benefits with an opinionated object-relational mapping model that you may not want and a query API that is strictly less expressive than SQL.

Tamuno-sqlgen separates the two concerns. The `.sqlg` template is plain SQL - portable, readable by any DBA, and able to use every feature your database offers. The code generator wraps it in typed, language-specific APIs with named parameters, so you get autocompletion and type checking without surrendering control over the query. Optional sections and combiners handle the dynamic parts that would otherwise require string concatenation, and they do so within the template syntax rather than in procedural code.

The result is the best of both worlds: **SQL as the query language** (universal, expressive, optimizable by the database engine) and **generated type-safe code as the calling convention** (safe, ergonomic, integrated with your IDE). You keep the abstraction layer that decades of database engineering have refined, and you add exactly the kind of type safety and convenience that makes application code robust - without the baggage of an object-relational mapping layer you never asked for.

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

Optional sections can nest, and the engine handles the combiners (`AND`, `,`, `OR`, etc.) automatically so you never end up with a dangling `WHERE AND` or a trailing comma.

## License

Apache License 2.0

## Author

Kai Londenberg - Kai.Londenberg@googlemail.com
