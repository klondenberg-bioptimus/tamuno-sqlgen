"""Python code generator for tamuno-sqlgen templates."""

from __future__ import annotations

import textwrap
from pathlib import Path

from .parser import Parser
from .scanner import TokenType
from .types import TYPE_MAP, DEFAULT_TYPE


def _py_type_name(vartype: str) -> str:
    info = TYPE_MAP.get(vartype, TYPE_MAP[DEFAULT_TYPE])
    t = info["python_type"]
    if t is __import__("datetime").date:
        return "datetime.date"
    if t is __import__("datetime").time:
        return "datetime.time"
    if t is __import__("datetime").datetime:
        return "datetime.datetime"
    if t is __import__("decimal").Decimal:
        return "decimal.Decimal"
    return t.__name__ if hasattr(t, "__name__") else str(t)


def _optional_type_name(vartype: str) -> str:
    return f"{_py_type_name(vartype)} | None"


class PythonCodeGenerator:
    """Generates Python source files from ``.sqlg`` templates.

    The generated code contains ``@dataclass`` param and row classes with
    ``build_sql()``, ``execute()``, and ``query()`` methods, along with
    factory functions for each statement.
    """

    def generate(
        self,
        source: str,
        module_name: str,
        dialect_class: str = "SQLDialect",
    ) -> str:
        """Generate Python source code from a ``.sqlg`` template source.

        Args:
            source: Full contents of a ``.sqlg`` template file.
            module_name: Module name used in the file-level docstring.
            dialect_class: Name of the dialect class to import and use.

        Returns:
            The generated Python source code as a string.
        """
        lines: list[str] = []

        lines.append(f'"""Auto-generated SQL query helpers for {module_name}."""')
        lines.append("")
        lines.append("import datetime")
        lines.append("import decimal")
        lines.append("from dataclasses import dataclass, field")
        lines.append("")
        lines.append("import pandas as pd")
        lines.append("")
        lines.append(f"from tamuno_sqlgen.dialect import {dialect_class}")
        lines.append("from tamuno_sqlgen.parser import Parser")
        lines.append("from tamuno_sqlgen.builder import SQLBuilder")
        lines.append("")
        lines.append(f"_dialect = {dialect_class}()")
        lines.append("")

        for name, body in Parser.extract_statements(source):
            p = Parser()
            p.parse(body)
            lines.extend(self._gen_statement(name, body, p))
            lines.append("")

        return "\n".join(lines)

    def generate_file(
        self,
        source_path: str,
        target_path: str,
        module_name: str,
        dialect_class: str = "SQLDialect",
    ) -> None:
        """Generate a Python file from a ``.sqlg`` template file.

        Args:
            source_path: Path to the ``.sqlg`` template file.
            target_path: Path to the Python file to write.
            module_name: Module name used in the file-level docstring.
            dialect_class: Name of the dialect class to import and use.
        """
        source = Path(source_path).read_text(encoding="utf-8")
        code = self.generate(source, module_name, dialect_class)
        Path(target_path).write_text(code, encoding="utf-8")

    # ------------------------------------------------------------------
    def _gen_statement(self, name: str, body: str, p: Parser) -> list[str]:
        cap = name[0].upper() + name[1:]
        lines: list[str] = []

        # --- Row (result) dataclass ---
        if p.output_vars:
            lines.append(f"@dataclass(kw_only=True)")
            lines.append(f"class {cap}Row:")
            lines.append(f'    """Result row for {name}."""')
            for var in p.output_vars:
                pytype = _py_type_name(var.vartype)
                lines.append(f"    {var.value}: {pytype} | None = None")
            lines.append("")

        # --- Params dataclass ---
        escaped_body = body.replace('"""', r'\"\"\"')
        # Store the template at module level to avoid slots/annotation issues
        tpl_var = f"_SQL_TEMPLATE_{name.upper()}"
        lines.append(f'{tpl_var} = """{escaped_body}"""')
        lines.append("")
        lines.append(f"@dataclass(kw_only=True)")
        lines.append(f"class {cap}Params:")
        lines.append(f'    """Parameters for {name}."""')
        lines.append("")

        for var in p.input_vars:
            opt_type = _optional_type_name(var.vartype)
            lines.append(f"    {var.value}: {opt_type} = None")

        lines.append("")
        lines.append("    def _get_parser(self) -> Parser:")
        lines.append(f"        p = Parser()")
        lines.append(f"        p.parse({tpl_var})")
        lines.append(f"        return p")
        lines.append("")
        lines.append("    def build_sql(self, dialect=None) -> str:")
        lines.append('        """Build the SQL string from the current parameter values.')
        lines.append("")
        lines.append("        Args:")
        lines.append("            dialect: Optional SQL dialect override for value escaping.")
        lines.append("")
        lines.append("        Returns:")
        lines.append("            The fully constructed SQL string.")
        lines.append('        """')
        lines.append("        p = self._get_parser()")
        lines.append("        d = dialect or _dialect")
        lines.append(
            "        builder = SQLBuilder(p.tokens, p.expressions, p.input_vars, d)"
        )
        lines.append("        params = {")
        for var in p.input_vars:
            lines.append(f"            '{var.value}': self.{var.value},")
        lines.append("        }")
        lines.append("        return builder.build(params)")
        lines.append("")
        lines.append("    def to_sql(self, dialect=None) -> str:")
        lines.append('        """Alias for :meth:`build_sql`.')
        lines.append("")
        lines.append("        Args:")
        lines.append("            dialect: Optional SQL dialect override for value escaping.")
        lines.append("")
        lines.append("        Returns:")
        lines.append("            The fully constructed SQL string.")
        lines.append('        """')
        lines.append("        return self.build_sql(dialect=dialect)")
        lines.append("")
        lines.append("    def execute(self, conn) -> int:")
        lines.append('        """Execute the SQL statement (INSERT, UPDATE, DELETE).')
        lines.append("")
        lines.append("        Args:")
        lines.append("            conn: A DB-API 2.0 database connection.")
        lines.append("")
        lines.append("        Returns:")
        lines.append("            The number of affected rows.")
        lines.append('        """')
        lines.append("        sql = self.build_sql()")
        lines.append("        cursor = conn.cursor()")
        lines.append("        cursor.execute(sql)")
        lines.append("        return cursor.rowcount")
        lines.append("")

        if p.output_vars:
            col_names = [v.value for v in p.output_vars]
            col_names_repr = repr(col_names)
            lines.append(f"    def query(self, conn) -> pd.DataFrame:")
            lines.append('        """Execute the SQL query and return results as a DataFrame.')
            lines.append("")
            lines.append("        Args:")
            lines.append("            conn: A DB-API 2.0 database connection.")
            lines.append("")
            lines.append("        Returns:")
            lines.append("            A pandas DataFrame with columns named after the output")
            lines.append("            variables defined in the template.")
            lines.append('        """')
            lines.append("        sql = self.build_sql()")
            lines.append("        df = pd.read_sql_query(sql, conn)")
            lines.append(f"        col_names = {col_names_repr}")
            lines.append("        if len(df.columns) == len(col_names):")
            lines.append("            df.columns = col_names")
            lines.append("        return df")
        else:
            lines.append("    def query(self, conn) -> pd.DataFrame:")
            lines.append('        """Execute the SQL query and return results as a DataFrame.')
            lines.append("")
            lines.append("        Args:")
            lines.append("            conn: A DB-API 2.0 database connection.")
            lines.append("")
            lines.append("        Returns:")
            lines.append("            A pandas DataFrame with the query results.")
            lines.append('        """')
            lines.append("        sql = self.build_sql()")
            lines.append("        return pd.read_sql_query(sql, conn)")

        lines.append("")

        # Factory function
        params_sig = ", ".join(
            f"{v.value}: {_optional_type_name(v.vartype)} = None"
            for v in p.input_vars
        )
        params_call = ", ".join(f"{v.value}={v.value}" for v in p.input_vars)
        lines.append(f"def {name}({params_sig}) -> {cap}Params:")
        lines.append(f'    """Create a {cap}Params instance.')
        lines.append("")
        lines.append("    Args:")
        for v in p.input_vars:
            lines.append(f"        {v.value}: Value for the {v.value} parameter.")
        lines.append("")
        lines.append("    Returns:")
        lines.append(f"        A new {cap}Params instance.")
        lines.append('    """')
        if params_call:
            lines.append(f"    return {cap}Params({params_call})")
        else:
            lines.append(f"    return {cap}Params()")

        return lines
