"""Type system definitions for tamuno-sqlgen."""

from __future__ import annotations

import datetime
import decimal
from typing import Optional

# Maps DSL type name → {"python_type": T, "optional_type": Optional[T], "pandas_dtype": str}
TYPE_MAP: dict[str, dict] = {
    "String": {
        "python_type": str,
        "optional_type": Optional[str],
        "pandas_dtype": "object",
    },
    "int": {
        "python_type": int,
        "optional_type": Optional[int],
        "pandas_dtype": "Int64",
    },
    "long": {
        "python_type": int,
        "optional_type": Optional[int],
        "pandas_dtype": "Int64",
    },
    "double": {
        "python_type": float,
        "optional_type": Optional[float],
        "pandas_dtype": "float64",
    },
    "float": {
        "python_type": float,
        "optional_type": Optional[float],
        "pandas_dtype": "float64",
    },
    "short": {
        "python_type": int,
        "optional_type": Optional[int],
        "pandas_dtype": "Int64",
    },
    "boolean": {
        "python_type": bool,
        "optional_type": Optional[bool],
        "pandas_dtype": "boolean",
    },
    "byte": {
        "python_type": int,
        "optional_type": Optional[int],
        "pandas_dtype": "Int64",
    },
    "bytes": {
        "python_type": bytes,
        "optional_type": Optional[bytes],
        "pandas_dtype": "object",
    },
    "decimal": {
        "python_type": decimal.Decimal,
        "optional_type": Optional[decimal.Decimal],
        "pandas_dtype": "object",
    },
    "Date": {
        "python_type": datetime.date,
        "optional_type": Optional[datetime.date],
        "pandas_dtype": "object",
    },
    "Time": {
        "python_type": datetime.time,
        "optional_type": Optional[datetime.time],
        "pandas_dtype": "object",
    },
    "Timestamp": {
        "python_type": datetime.datetime,
        "optional_type": Optional[datetime.datetime],
        "pandas_dtype": "datetime64[ns]",
    },
}

DEFAULT_TYPE = "String"
