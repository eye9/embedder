"""
Tests for load_tnved CLI product source replacement handling.
"""

import sys

import pandas as pd
import pytest

import load_tnved


class DummyLogger:
    """Logger stub for CLI tests."""

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def _create_excel_file(tmp_path):
    excel_file = tmp_path / "products.xlsx"
    pd.DataFrame({
        "Code": ["0901110000"],
        "TextEx": ["Coffee beans"],
    }).to_excel(excel_file, index=False)
    return excel_file


def _patch_cli_dependencies(monkeypatch, fake_loader_class):
    monkeypatch.setattr(load_tnved, "TextNormalizer", lambda: object())
    monkeypatch.setattr(load_tnved, "EmbeddingGenerator", lambda **kwargs: object())
    monkeypatch.setattr(load_tnved, "ProductLoader", fake_loader_class)
    monkeypatch.setattr(load_tnved, "setup_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(load_tnved, "get_logger", lambda name: DummyLogger())


def test_cli_existing_product_source_decline_cancels_without_loading(tmp_path, monkeypatch):
    """Test declining duplicate source prompt exits without loading data."""
    excel_file = _create_excel_file(tmp_path)
    load_calls = []

    class FakeProductLoader:
        def __init__(self, *args, **kwargs):
            pass

        def get_record_count(self):
            return 5

        def get_statistics_by_source_type(self):
            return {"reference": 0, "product": 5, "legacy": 0, "total": 5}

        def count_product_records_by_source(self, source_name):
            return 5

        def load_from_excel(self, *args, **kwargs):
            load_calls.append((args, kwargs))
            return 1

    _patch_cli_dependencies(monkeypatch, FakeProductLoader)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "load_tnved.py",
            str(excel_file),
            "--source-type",
            "product",
            "--source-name",
            "existing_source",
        ],
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    with pytest.raises(SystemExit) as exc_info:
        load_tnved.main()

    assert exc_info.value.code == 0
    assert load_calls == []


def test_cli_replace_source_flag_passes_replace_existing(tmp_path, monkeypatch):
    """Test --replace-source confirms replacement non-interactively."""
    excel_file = _create_excel_file(tmp_path)
    load_calls = []

    class FakeProductLoader:
        def __init__(self, *args, **kwargs):
            pass

        def get_record_count(self):
            return 5

        def get_statistics_by_source_type(self):
            return {"reference": 0, "product": 5, "legacy": 0, "total": 5}

        def count_product_records_by_source(self, source_name):
            return 5

        def load_from_excel(self, *args, **kwargs):
            load_calls.append((args, kwargs))
            return 1

    _patch_cli_dependencies(monkeypatch, FakeProductLoader)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "load_tnved.py",
            str(excel_file),
            "--source-type",
            "product",
            "--source-name",
            "existing_source",
            "--replace-source",
        ],
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: (_ for _ in ()).throw(AssertionError("prompt should not be used")),
    )

    with pytest.raises(SystemExit) as exc_info:
        load_tnved.main()

    assert exc_info.value.code == 0
    assert len(load_calls) == 1
    assert load_calls[0][0] == (str(excel_file), "existing_source")
    assert load_calls[0][1] == {"replace_existing": True}


def test_cli_quiet_existing_product_source_requires_replace_flag(tmp_path, monkeypatch):
    """Test quiet mode refuses duplicate source without --replace-source."""
    excel_file = _create_excel_file(tmp_path)
    load_calls = []

    class FakeProductLoader:
        def __init__(self, *args, **kwargs):
            pass

        def get_record_count(self):
            return 5

        def get_statistics_by_source_type(self):
            return {"reference": 0, "product": 5, "legacy": 0, "total": 5}

        def count_product_records_by_source(self, source_name):
            return 5

        def load_from_excel(self, *args, **kwargs):
            load_calls.append((args, kwargs))
            return 1

    _patch_cli_dependencies(monkeypatch, FakeProductLoader)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "load_tnved.py",
            str(excel_file),
            "--source-type",
            "product",
            "--source-name",
            "existing_source",
            "--quiet",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        load_tnved.main()

    assert exc_info.value.code == 1
    assert load_calls == []
