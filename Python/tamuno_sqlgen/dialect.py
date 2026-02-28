"""SQL dialect helpers for value escaping."""

from __future__ import annotations

import datetime
import decimal


class SQLDialect:
    """Standard SQL dialect (ANSI-style escaping)."""

    def escape_value(self, value) -> str:
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
    """MySQL-style escaping (backslash for special chars)."""

    def escape_value(self, value) -> str:
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
