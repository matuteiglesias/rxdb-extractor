from __future__ import annotations

from pathlib import Path

from .artifacts import hash_file
from .manifest import semantic_hash


def rxdb_source_family(path: str | Path) -> tuple[Path, ...]:
    """Return the RXDB plus adjacent RBFX shards that belong to its stem."""
    database = Path(path).expanduser().resolve()
    if not database.is_file():
        raise ValueError(f"database does not exist: {database}")
    stem = database.stem
    siblings = [
        item
        for item in database.parent.iterdir()
        if item.is_file()
        and (
            item == database
            or (item.suffix.lower() == ".rbfx" and item.name.startswith(stem + "-"))
        )
    ]
    siblings.sort(key=lambda item: item.name)
    if database not in siblings:
        siblings.insert(0, database)
    return tuple(siblings)


def rxdb_source_family_hash(path: str | Path) -> str:
    members = rxdb_source_family(path)
    return semantic_hash(
        {
            "files": [
                {
                    "name": member.name,
                    "size_bytes": member.stat().st_size,
                    "sha256": hash_file(member),
                }
                for member in members
            ]
        }
    )
