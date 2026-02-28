"""High-level Pythonic API for tamuno-sqlgen."""

from __future__ import annotations

import re
from dataclasses import make_dataclass, field
from typing import Any

import pandas as pd

from .parser import Parser
from .builder import SQLBuilder
from .dialect import SQLDialect
from .types import TYPE_MAP, DEFAULT_TYPE


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    parts = name.split("_")
    if not parts:
        return name
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class QueryFactory:
    """Callable factory that creates query parameter instances for a SQL statement.

    Each instance wraps a single parsed SQL template and exposes methods
    for building SQL, executing queries, and returning typed results.

    Attributes:
        input_vars: Input variable tokens for this statement.
        output_vars: Output variable tokens for this statement.
    """

    def __init__(
        self,
        name: str,
        parser: Parser,
        dialect: SQLDialect,
    ) -> None:
        """Initialize the QueryFactory.

        Args:
            name: Name of the SQL statement.
            parser: A :class:`Parser` instance that has already parsed the
                statement body.
            dialect: SQL dialect to use for value escaping.
        """
        self._name = name
        self._parser = parser
        self._dialect = dialect
        self._builder = SQLBuilder(
            tokens=parser.tokens,
            expressions=parser.expressions,
            input_vars=parser.input_vars,
            dialect=dialect,
        )
        self._cls = self._make_class()

    def _make_class(self):
        input_vars = self._parser.input_vars
        output_vars = self._parser.output_vars
        builder = self._builder

        # Build fields list: [(name, type, field(default=None)), ...]
        fields = []
        for var in input_vars:
            info = TYPE_MAP.get(var.vartype, TYPE_MAP[DEFAULT_TYPE])
            fields.append((var.value, info["optional_type"], field(default=None)))

        # Methods to inject into the class namespace
        def build_sql(self, dialect=None) -> str:
            """Build the SQL string from the current parameter values.

            Args:
                dialect: Optional SQL dialect override for value escaping.

            Returns:
                The fully constructed SQL string.
            """
            b = builder if dialect is None else SQLBuilder(
                tokens=builder.tokens,
                expressions=builder.expressions,
                input_vars=builder.input_vars,
                dialect=dialect,
            )
            return b.build(vars(self))

        def to_sql(self, dialect=None) -> str:
            """Alias for :meth:`build_sql`.

            Args:
                dialect: Optional SQL dialect override for value escaping.

            Returns:
                The fully constructed SQL string.
            """
            return self.build_sql(dialect=dialect)

        def execute(self, conn) -> int:
            """Execute the SQL statement (INSERT, UPDATE, DELETE).

            Args:
                conn: A DB-API 2.0 database connection.

            Returns:
                The number of affected rows.
            """
            sql = self.build_sql()
            cursor = conn.cursor()
            cursor.execute(sql)
            return cursor.rowcount

        def query(self, conn) -> pd.DataFrame:
            """Execute the SQL query and return results as a DataFrame.

            Args:
                conn: A DB-API 2.0 database connection.

            Returns:
                A pandas DataFrame with columns named after the output
                variables defined in the template.
            """
            sql = self.build_sql()
            df = pd.read_sql_query(sql, conn)
            # Rename columns to match output var names if needed
            if output_vars:
                col_names = [v.value for v in output_vars]
                if len(df.columns) == len(col_names):
                    df.columns = col_names
            return df

        namespace = {
            "build_sql": build_sql,
            "to_sql": to_sql,
            "execute": execute,
            "query": query,
        }

        cls = make_dataclass(
            self._name.capitalize() + "Params",
            fields,
            namespace=namespace,
        )
        return cls

    def __call__(self, **kwargs) -> Any:
        """Create a new query parameter instance with the given values.

        Args:
            **kwargs: Parameter names and values for the SQL statement.

        Returns:
            A dynamically-created dataclass instance with ``build_sql()``,
            ``to_sql()``, ``execute()``, and ``query()`` methods.
        """
        return self._cls(**kwargs)

    @property
    def input_vars(self):
        """List of input variable tokens for this statement."""
        return self._parser.input_vars

    @property
    def output_vars(self):
        """List of output variable tokens for this statement."""
        return self._parser.output_vars


class SQLGenApi:
    """
    Main entry point for using SQL templates.

    Parses a ``.sqlg`` source and exposes each statement as a callable
    attribute.  Statement names can be accessed as camelCase (original)
    or snake_case.

    Example::

        api = SQLGenApi.from_file("queries.sqlg")
        params = api.select_user_login(user_name="alice", password="secret")
        df = params.query(conn)

    Attributes:
        statement_names: List of available statement names.
    """

    def __init__(self, source: str, dialect: SQLDialect | None = None) -> None:
        """Initialize the API by parsing the given source.

        Args:
            source: Full contents of a ``.sqlg`` template file.
            dialect: SQL dialect for value escaping. Defaults to
                :class:`SQLDialect` (ANSI standard).
        """
        self._dialect = dialect or SQLDialect()
        self._queries: dict[str, QueryFactory] = {}
        self._parse_source(source)

    @classmethod
    def from_file(cls, path: str, dialect: SQLDialect | None = None) -> "SQLGenApi":
        """Create an SQLGenApi from a ``.sqlg`` file.

        Args:
            path: Filesystem path to the ``.sqlg`` template file.
            dialect: SQL dialect for value escaping.

        Returns:
            A new :class:`SQLGenApi` instance.
        """
        with open(path, encoding="utf-8") as f:
            return cls(f.read(), dialect=dialect)

    def _parse_source(self, source: str) -> None:
        for name, body in Parser.extract_statements(source):
            p = Parser()
            p.parse(body)
            self._queries[name] = QueryFactory(name, p, self._dialect)

    def __getattr__(self, name: str) -> QueryFactory:
        """Look up a SQL statement by name.

        Supports both the original camelCase name and a snake_case
        variant (e.g. ``select_user_login`` resolves to ``selectUserLogin``).

        Args:
            name: Statement name to look up.

        Returns:
            The :class:`QueryFactory` for the requested statement.

        Raises:
            AttributeError: If no statement with the given name exists.
        """
        # Try exact match first
        if name in self._queries:
            return self._queries[name]
        # Try snake_case → camelCase conversion
        camel = _snake_to_camel(name)
        if camel in self._queries:
            return self._queries[camel]
        raise AttributeError(f"No SQL statement named '{name}' (tried camelCase: '{camel}')")

    def __getitem__(self, name: str) -> QueryFactory:
        """Look up a SQL statement by exact name using bracket notation.

        Args:
            name: Exact statement name as defined in the ``.sqlg`` file.

        Returns:
            The :class:`QueryFactory` for the requested statement.

        Raises:
            KeyError: If no statement with the given name exists.
        """
        return self._queries[name]

    @property
    def statement_names(self) -> list[str]:
        """List of all available SQL statement names."""
        return list(self._queries.keys())

    def build_sql(self, name: str, **params) -> str:
        """Build SQL for the named statement with the given parameters.

        Args:
            name: Exact statement name as defined in the ``.sqlg`` file.
            **params: Parameter names and values for the SQL statement.

        Returns:
            The fully constructed SQL string.
        """
        factory = self._queries[name]
        qp = factory(**params)
        return qp.build_sql()
