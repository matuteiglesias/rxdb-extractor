from rxdb_extractor.source_identity import rxdb_source_family, rxdb_source_family_hash


def test_source_family_includes_matching_rxdb_and_rbfx(tmp_path):
    database = tmp_path / "cpv2022.rxdb"
    database.write_bytes(b"db")
    (tmp_path / "cpv2022-000.rbfx").write_bytes(b"a")
    (tmp_path / "cpv2022-001.rbfx").write_bytes(b"b")
    (tmp_path / "other-000.rbfx").write_bytes(b"x")

    members = rxdb_source_family(database)
    assert [item.name for item in members] == [
        "cpv2022-000.rbfx",
        "cpv2022-001.rbfx",
        "cpv2022.rxdb",
    ]
    first = rxdb_source_family_hash(database)
    (tmp_path / "cpv2022-001.rbfx").write_bytes(b"changed")
    second = rxdb_source_family_hash(database)
    assert first != second
