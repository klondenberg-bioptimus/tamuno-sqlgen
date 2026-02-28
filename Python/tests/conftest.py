"""Shared pytest fixtures."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

SAMPLE_SQLG = FIXTURES_DIR / "sample.sqlg"

SIMPLE_TEMPLATE = """\
selectUserLogin:=
    SELECT @user_id:int, @user_name:String, @birthdate:Date
        FROM users
        WHERE user_name=$user_name AND password_hash=$password
        LIMIT 1;

selectUser:=
    SELECT @user_id:int, @user_name:String, @birthdate:Date
        FROM users
            [ WHERE
                [user_name=$user_name] [AND] [active=$active:int]
            ]
        LIMIT 1;

insertUser:=
    INSERT INTO users (user_name, active) VALUES ($user_name, $active:int);

updateUser:=
    UPDATE users SET
        [user_name=$user_name] [,] [active=$active:int]
    WHERE user_id=$user_id:int;
"""


@pytest.fixture
def sample_source() -> str:
    return SIMPLE_TEMPLATE


@pytest.fixture
def sample_sqlg_path() -> Path:
    return SAMPLE_SQLG


@pytest.fixture
def sqlite_conn():
    """In-memory SQLite database with a users table and sample data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT NOT NULL,
            birthdate TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            password_hash TEXT
        )
        """
    )
    cursor.executemany(
        "INSERT INTO users (user_id, user_name, birthdate, active, password_hash) VALUES (?, ?, ?, ?, ?)",
        [
            (1, "alice", "1990-01-15", 1, "hash_alice"),
            (2, "bob", "1985-06-20", 0, "hash_bob"),
            (3, "carol", "1995-03-10", 1, "hash_carol"),
        ],
    )
    conn.commit()
    yield conn
    conn.close()
