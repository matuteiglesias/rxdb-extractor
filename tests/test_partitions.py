import json

import pytest

from rxdb_extractor.partitions import load_partition_requests


def test_text_partition_inventory(tmp_path):
    path = tmp_path / "radios.txt"
    path.write_text("# radios\n061120902\n\n061471101\n", encoding="utf-8")
    requests = load_partition_requests(path)
    assert [item.selection_code for item in requests] == ["061120902", "061471101"]
    assert all(item.expected_counts is None for item in requests)


def test_json_partition_inventory_can_carry_expected_counts(tmp_path):
    path = tmp_path / "radios.json"
    path.write_text(
        json.dumps(
            {
                "partitions": [
                    "061120902",
                    {
                        "selection_code": "061471101",
                        "expected_counts": {
                            "vivienda": 73,
                            "hogar": 56,
                            "persona": 137,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    requests = load_partition_requests(path)
    assert requests[1].expected_counts == {
        "VIVIENDA": 73,
        "HOGAR": 56,
        "PERSONA": 137,
    }


def test_csv_partition_inventory(tmp_path):
    path = tmp_path / "radios.csv"
    path.write_text(
        "selection_code,vivienda_count,hogar_count,persona_count\n"
        "061471101,73,56,137\n",
        encoding="utf-8",
    )
    requests = load_partition_requests(path)
    assert requests[0].selection_code == "061471101"
    assert requests[0].expected_counts == {
        "VIVIENDA": 73,
        "HOGAR": 56,
        "PERSONA": 137,
    }


def test_duplicate_partition_is_rejected(tmp_path):
    path = tmp_path / "radios.txt"
    path.write_text("061471101\n061471101\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_partition_requests(path)
