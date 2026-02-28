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
    """Callable that returns a QueryParams instance for a single SQL statement."""

    def __init__(
        self,
        name: str,
        parser: Parser,
        dialect: SQLDialect,
    ) -> None:
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
            b = builder if dialect is None else SQLBuilder(
                tokens=builder.tokens,
                expressions=builder.expressions,
                input_vars=builder.input_vars,
                dialect=dialect,
            )
            return b.build(vars(self))

        def to_sql(self, dialect=None) -> str:
            return self.build_sql(dialect=dialect)

        def execute(self, conn) -> int:
            sql = self.build_sql()
            cursor = conn.cursor()
            cursor.execute(sql)
            return cursor.rowcount

        def query(self, conn) -> pd.DataFrame:
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
        return self._cls(**kwargs)

    @property
    def input_vars(self):
        return self._parser.input_vars

    @property
    def output_vars(self):
        return self._parser.output_vars


class SQLGenApi:
    """
    Main entry point for using SQL templates.

    Usage::

        api = SQLGenApi.from_file("queries.sqlg")
        params = api.select_user_login(user_name="alice", password="secret")
        df = params.query(conn)
    """

    def __init__(self, source: str, dialect: SQLDialect | None = None) -> None:
        self._dialect = dialect or SQLDialect()
        self._queries: dict[str, QueryFactory] = {}
        self._parse_source(source)

    @classmethod
    def from_file(cls, path: str, dialect: SQLDialect | None = None) -> "SQLGenApi":
        """Create an SQLGenApi from a .sqlg file."""
        with open(path, encoding="utf-8") as f:
            return cls(f.read(), dialect=dialect)

    def _parse_source(self, source: str) -> None:
        for name, body in Parser.extract_statements(source):
            p = Parser()
            p.parse(body)
            self._queries[name] = QueryFactory(name, p, self._dialect)

    def __getattr__(self, name: str) -> QueryFactory:
        # Try exact match first
        if name in self._queries:
            return self._queries[name]
        # Try snake_case → camelCase conversion
        camel = _snake_to_camel(name)
        if camel in self._queries:
            return self._queries[camel]
        raise AttributeError(f"No SQL statement named '{name}' (tried camelCase: '{camel}')")

    def __getitem__(self, name: str) -> QueryFactory:
        return self._queries[name]

    @property
    def statement_names(self) -> list[str]:
        return list(self._queries.keys())

    def build_sql(self, name: str, **params) -> str:
        """Build SQL for statement *name* with the given params."""
        factory = self._queries[name]
        qp = factory(**params)
        return qp.build_sql()
