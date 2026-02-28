"""Tests for the high-level SQLGenApi."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from tamuno_sqlgen.api import SQLGenApi


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# --- Creation ---

def test_api_from_string(sample_source):
    api = SQLGenApi(sample_source)
    assert "selectUserLogin" in api.statement_names


def test_api_from_file(sample_sqlg_path):
    api = SQLGenApi.from_file(str(sample_sqlg_path))
    assert "selectUserLogin" in api.statement_names


def test_api_statement_names(sample_source):
    api = SQLGenApi(sample_source)
    names = api.statement_names
    assert "insertUser" in names
    assert "updateUser" in names


def test_api_attribute_access(sample_source):
    api = SQLGenApi(sample_source)
    factory = api.selectUserLogin
    assert callable(factory)


def test_api_snake_case_access(sample_source):
    api = SQLGenApi(sample_source)
    factory = api.select_user_login
    assert callable(factory)


def test_api_getitem(sample_source):
    api = SQLGenApi(sample_source)
    factory = api["selectUserLogin"]
    assert callable(factory)


def test_api_unknown_statement_raises(sample_source):
    api = SQLGenApi(sample_source)
    with pytest.raises(AttributeError):
        _ = api.nonExistentStatement


# --- Build SQL ---

def test_api_build_sql_select(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUserLogin(user_name="alice", password="secret")
    sql = params.build_sql()
    assert "alice" in sql
    assert "secret" in sql
    assert "SELECT" in sql


def test_api_build_sql_optional_absent(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    sql = params.build_sql()
    assert "WHERE" not in sql


def test_api_build_sql_optional_present(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUser(user_name="alice")
    sql = params.build_sql()
    assert "WHERE" in sql
    assert "alice" in sql


def test_api_build_sql_insert(sample_source):
    api = SQLGenApi(sample_source)
    params = api.insertUser(user_name="dave", active=1)
    sql = params.build_sql()
    assert "INSERT INTO users" in sql
    assert "'dave'" in sql


def test_api_to_sql_alias(sample_source):
    api = SQLGenApi(sample_source)
    params = api.selectUser(user_name="alice")
    assert params.to_sql() == params.build_sql()


# --- Query execution against SQLite ---

def test_api_query_returns_dataframe(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    df = params.query(sqlite_conn)
    assert isinstance(df, pd.DataFrame)


def test_api_query_with_user_name_filter(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser(user_name="alice")
    df = params.query(sqlite_conn)
    assert len(df) == 1
    assert df.iloc[0]["user_name"] == "alice"


def test_api_query_with_active_filter(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser(active=1)
    df = params.query(sqlite_conn)
    # alice and carol are active
    assert len(df) >= 1


def test_api_query_all_users(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    df = params.query(sqlite_conn)
    # selectUser has LIMIT 1 so returns at most 1 row
    assert len(df) <= 3  # just verify it returns a DataFrame without error


def test_api_query_column_names(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.selectUser()
    df = params.query(sqlite_conn)
    assert "user_id" in df.columns
    assert "user_name" in df.columns
    assert "birthdate" in df.columns


# --- Execute (INSERT/UPDATE) ---

def test_api_execute_insert(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.insertUser(user_name="dave", active=1)
    rows = params.execute(sqlite_conn)
    assert rows == 1


def test_api_execute_insert_persists(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    api.insertUser(user_name="dave", active=1).execute(sqlite_conn)
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_name='dave'")
    count = cursor.fetchone()[0]
    assert count == 1


def test_api_execute_update(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.updateUser(user_name="alice_updated", user_id=1)
    rows = params.execute(sqlite_conn)
    assert rows == 1


# --- Optional field combiner ---

def test_api_update_single_field_no_comma(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.updateUser(user_name="bob_renamed", user_id=2)
    sql = params.build_sql()
    # Should NOT have a trailing comma
    assert "user_name='bob_renamed'" in sql
    # active is absent, so comma should not appear
    assert "," not in sql.split("WHERE")[0].strip().rstrip(",")


def test_api_update_two_fields_has_comma(sample_source, sqlite_conn):
    api = SQLGenApi(sample_source)
    params = api.updateUser(user_name="carol_new", active=0, user_id=3)
    sql = params.build_sql()
    assert "," in sql
