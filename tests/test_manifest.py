from rxdb_extractor.manifest import checkpoint_identity, semantic_hash


def test_semantic_hash_ignores_mapping_order():
    assert semantic_hash({"a": 1, "b": 2}) == semantic_hash({"b": 2, "a": 1})


def test_checkpoint_identity_changes_with_query():
    a = checkpoint_identity(source_hash="s", schema_hash="x", query_hash="q1", runtime_hash="r")
    b = checkpoint_identity(source_hash="s", schema_hash="x", query_hash="q2", runtime_hash="r")
    assert a != b
