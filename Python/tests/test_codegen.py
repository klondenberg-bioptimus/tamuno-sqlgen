"""Tests for the Python code generator."""

from __future__ import annotations

import sys
import types
import importlib
from pathlib import Path

import pytest

from tamuno_sqlgen.codegen import PythonCodeGenerator


SAMPLE_SQLG = Path(__file__).parent / "fixtures" / "sample.sqlg"


@pytest.fixture
def generator() -> PythonCodeGenerator:
    return PythonCodeGenerator()


@pytest.fixture
def sample_source() -> str:
    return SAMPLE_SQLG.read_text(encoding="utf-8")


def test_generate_returns_string(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert isinstance(code, str)
    assert len(code) > 0


def test_generated_code_has_imports(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert "import pandas as pd" in code
    assert "from tamuno_sqlgen" in code
    assert "import datetime" in code


def test_generated_code_has_dataclasses(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert "@dataclass" in code
    assert "SelectUserLoginParams" in code
    assert "SelectUserRow" in code or "SelectUserLoginRow" in code


def test_generated_code_has_factory_functions(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    assert "def selectUserLogin(" in code
    assert "def insertUser(" in code


def test_generated_code_is_valid_python(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    # Should not raise a SyntaxError
    compile(code, "<generated>", "exec")


def test_generated_code_can_be_executed(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_exec")
    sys.modules["_test_generated_exec"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)
        # Should have the factory function
        assert hasattr(module, "selectUserLogin")
        assert hasattr(module, "insertUser")
    finally:
        del sys.modules["_test_generated_exec"]


def test_generated_params_build_sql(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_build")
    sys.modules["_test_generated_build"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)
        params = module.selectUserLogin(user_name="alice", password="secret")
        sql = params.build_sql()
        assert "SELECT" in sql
        assert "alice" in sql
    finally:
        del sys.modules["_test_generated_build"]


def test_generated_insert_sql(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_insert")
    sys.modules["_test_generated_insert"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)
        params = module.insertUser(user_name="dave", active=1)
        sql = params.build_sql()
        assert "INSERT INTO users" in sql
        assert "'dave'" in sql
    finally:
        del sys.modules["_test_generated_insert"]


def test_generate_file_creates_file(generator, sample_source, tmp_path):
    src_path = tmp_path / "test.sqlg"
    src_path.write_text(sample_source, encoding="utf-8")
    target_path = tmp_path / "generated.py"
    generator.generate_file(str(src_path), str(target_path), "generated")
    assert target_path.exists()
    content = target_path.read_text(encoding="utf-8")
    assert "SelectUserLoginParams" in content


def test_generated_optional_params(generator, sample_source):
    code = generator.generate(sample_source, "test_module")
    module = types.ModuleType("_test_generated_optional")
    sys.modules["_test_generated_optional"] = module
    try:
        exec(compile(code, "<generated>", "exec"), module.__dict__)

        # selectUser with no args
        params = module.selectUser()
        sql = params.build_sql()
        assert "WHERE" not in sql

        # selectUser with user_name
        params2 = module.selectUser(user_name="alice")
        sql2 = params2.build_sql()
        assert "WHERE" in sql2
        assert "alice" in sql2
    finally:
        del sys.modules["_test_generated_optional"]
