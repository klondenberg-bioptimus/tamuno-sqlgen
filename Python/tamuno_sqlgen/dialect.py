"""SQL dialect helpers for value escaping."""

from __future__ import annotations

import datetime
import decimal


class SQLDialect:
    """Standard SQL dialect (ANSI-style escaping).

    Escapes values for safe inclusion in SQL strings. Strings are quoted
    with single quotes and internal quotes are doubled (``''``).
    """

    def escape_value(self, value) -> str:
        """Escape a Python value for safe inclusion in a SQL string.

        Args:
            value: The value to escape. Supports ``None``, ``bool``,
                ``int``, ``float``, ``str``, ``bytes``,
                ``decimal.Decimal``, ``datetime.date``,
                ``datetime.time``, and ``datetime.datetime``.

        Returns:
            A SQL-safe string representation of the value.
        """
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, decimal.Decimal):
            return str(value)
        if isinstance(value, datetime.datetime):
            return "'" + str(value) + "'"
        if isinstance(value, datetime.date):
            return "'" + str(value) + "'"
        if isinstance(value, datetime.time):
            return "'" + str(value) + "'"
        if isinstance(value, bytes):
            return "X'" + value.hex() + "'"
        # Default: treat as string
        s = str(value)
        return "'" + s.replace("'", "''") + "'"


class MySQLDialect(SQLDialect):
    """MySQL-style escaping (backslash for special chars).

    Uses backslash escaping for single quotes (``\\'``) and backslashes
    (``\\\\``) instead of the ANSI doubling convention.
    """

    def escape_value(self, value) -> str:
        """Escape a Python value for safe inclusion in a MySQL SQL string.

        Args:
            value: The value to escape. Supports the same types as
                :meth:`SQLDialect.escape_value`.

        Returns:
            A MySQL-safe string representation of the value.
        """
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, decimal.Decimal):
            return str(value)
        if isinstance(value, datetime.datetime):
            return "'" + str(value) + "'"
        if isinstance(value, datetime.date):
            return "'" + str(value) + "'"
        if isinstance(value, datetime.time):
            return "'" + str(value) + "'"
        if isinstance(value, bytes):
            return "X'" + value.hex() + "'"
        s = str(value)
        s = s.replace("\\", "\\\\").replace("'", "\\'")
        return "'" + s + "'"
