from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1


def now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ItemState:
    item_key: str
    zotero_version: int
    state: str
    input_hash: str | None = None
    auto_tags: set[str] = None  # type: ignore[assignment]
    suppressed_tags: set[str] = None  # type: ignore[assignment]
    retry_count: int = 0

    def __post_init__(self) -> None:
        self.auto_tags = self.auto_tags or set()
        self.suppressed_tags = self.suppressed_tags or set()


class StateStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        self.db = sqlite3.connect(path)
        # The state DB may contain a remembered local API authorization.
        os.chmod(path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS items (
          item_key TEXT PRIMARY KEY, zotero_version INTEGER NOT NULL, state TEXT NOT NULL,
          discovered_at TEXT, ready_at TEXT, classified_at TEXT, taxonomy_version TEXT,
          classifier_version TEXT, input_hash TEXT, auto_tags_json TEXT NOT NULL DEFAULT '[]',
          suppressed_tags_json TEXT NOT NULL DEFAULT '[]', backup_snapshot TEXT, prewrite_path TEXT,
          last_error TEXT, retry_count INTEGER NOT NULL DEFAULT 0)""")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.db.execute("""CREATE TABLE IF NOT EXISTS taxonomy_audit_runs (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, taxonomy_version TEXT NOT NULL,
          taxonomy_digest TEXT NOT NULL, embedding_model TEXT NOT NULL, threshold REAL NOT NULL,
          findings_count INTEGER NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS taxonomy_audit_findings (
          audit_id INTEGER NOT NULL, first_tag TEXT NOT NULL, second_tag TEXT NOT NULL,
          similarity REAL NOT NULL, relationship_kind TEXT, resolution TEXT,
          review_status TEXT NOT NULL,
          PRIMARY KEY (audit_id, first_tag, second_tag),
          FOREIGN KEY (audit_id) REFERENCES taxonomy_audit_runs(id))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS profile_runs (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, server_id TEXT,
          library_version INTEGER, embedding_model TEXT NOT NULL, item_count INTEGER NOT NULL,
          tag_count INTEGER NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS profile_items (
          item_key TEXT PRIMARY KEY, item_version INTEGER NOT NULL, vector_json TEXT NOT NULL,
          tags_json TEXT NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS profile_vocabulary (
          raw_tag TEXT PRIMARY KEY, normalized_tag TEXT NOT NULL, item_count INTEGER NOT NULL,
          first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS profile_tag_mappings (
          raw_tag TEXT PRIMARY KEY, canonical_tag TEXT NOT NULL, mapping_type TEXT NOT NULL,
          approved_at TEXT NOT NULL)""")
        self.db.commit()
        if self._get_meta("schema_version") is None:
            self._set_meta("schema_version", str(SCHEMA_VERSION))

    def close(self) -> None:
        self.db.close()

    def get_library_version(self) -> int | None:
        row = self.db.execute("SELECT value FROM meta WHERE key='library_version'").fetchone()
        return int(row["value"]) if row else None

    def set_library_version(self, version: int) -> None:
        self.db.execute(
            "INSERT INTO meta(key,value) VALUES('library_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(version),),
        )
        self.db.commit()

    def get_baseline_at(self) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key='baseline_at'").fetchone()
        return row["value"] if row else None

    def establish_baseline(self, version: int, *, baseline_at: str | None = None) -> str:
        """Record a cursor without queueing the pre-existing library."""
        baseline_at = baseline_at or now()
        self.db.execute(
            "INSERT INTO meta(key,value) VALUES('library_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(version),),
        )
        self.db.execute(
            "INSERT INTO meta(key,value) VALUES('baseline_at',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (baseline_at,),
        )
        self.db.commit()
        return baseline_at

    def get_zotero_server_id(self) -> str | None:
        return self._get_meta("zotero_server_id")

    def set_zotero_server_id(self, server_id: str) -> None:
        self._set_meta("zotero_server_id", server_id)

    def get_local_api_key(self) -> str | None:
        return self._get_meta("zotero_local_api_key")

    def set_local_api_key(self, key: str) -> None:
        self._set_meta("zotero_local_api_key", key)

    def clear_local_api_key(self) -> None:
        self.db.execute("DELETE FROM meta WHERE key='zotero_local_api_key'")
        self.db.commit()

    def _get_meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.db.commit()

    def get(self, key: str) -> ItemState | None:
        row = self.db.execute("SELECT * FROM items WHERE item_key=?", (key,)).fetchone()
        return self._item(row) if row else None

    def _item(self, row: sqlite3.Row) -> ItemState:
        return ItemState(
            row["item_key"],
            row["zotero_version"],
            row["state"],
            row["input_hash"],
            set(json.loads(row["auto_tags_json"])),
            set(json.loads(row["suppressed_tags_json"])),
            row["retry_count"],
        )

    def upsert(self, item: ItemState, **extra: object) -> None:
        values = {
            "item_key": item.item_key,
            "zotero_version": item.zotero_version,
            "state": item.state,
            "input_hash": item.input_hash,
            "auto_tags_json": json.dumps(sorted(item.auto_tags)),
            "suppressed_tags_json": json.dumps(sorted(item.suppressed_tags)),
        }
        values.update(extra)
        cols = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        updates = ", ".join(f"{col}=excluded.{col}" for col in values if col != "item_key")
        self.db.execute(
            f"INSERT INTO items ({cols}) VALUES ({marks}) ON CONFLICT(item_key) DO UPDATE SET {updates}",
            tuple(values.values()),
        )
        self.db.commit()

    def discover(self, key: str, version: int) -> ItemState:
        prior = self.get(key)
        item = prior or ItemState(key, version, "discovered")
        item.zotero_version = version
        if not prior:
            self.upsert(item, discovered_at=now())
        else:
            self.upsert(item)
        return item

    def discovered_at(self, key: str) -> str | None:
        row = self.db.execute("SELECT discovered_at FROM items WHERE item_key=?", (key,)).fetchone()
        return row["discovered_at"] if row else None

    def record_error(self, item: ItemState, message: str) -> None:
        item.state = "failed"
        item.retry_count += 1
        self.upsert(item, last_error=message)

    def summary(self) -> dict[str, int]:
        rows = self.db.execute("SELECT state, count(*) AS n FROM items GROUP BY state").fetchall()
        return {row["state"]: row["n"] for row in rows}

    def pending_keys(self) -> list[str]:
        rows = self.db.execute(
            "SELECT item_key FROM items WHERE state NOT IN ('organised', 'needs_triage') ORDER BY discovered_at"
        ).fetchall()
        return [row["item_key"] for row in rows]

    def last_backup(self) -> str | None:
        row = self.db.execute(
            "SELECT backup_snapshot FROM items WHERE backup_snapshot IS NOT NULL ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        return row["backup_snapshot"] if row else None

    def record_taxonomy_audit(
        self,
        *,
        taxonomy_version: str,
        taxonomy_digest: str,
        embedding_model: str,
        threshold: float,
        findings: list[tuple[str, str, float, str | None, str | None, str]],
    ) -> int:
        """Persist one immutable audit run and its review candidates."""
        cursor = self.db.execute(
            """INSERT INTO taxonomy_audit_runs
               (created_at, taxonomy_version, taxonomy_digest, embedding_model, threshold, findings_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (now(), taxonomy_version, taxonomy_digest, embedding_model, threshold, len(findings)),
        )
        audit_id = int(cursor.lastrowid)
        self.db.executemany(
            """INSERT INTO taxonomy_audit_findings
               (audit_id, first_tag, second_tag, similarity, relationship_kind, resolution, review_status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (audit_id, first, second, similarity, kind, resolution, status)
                for first, second, similarity, kind, resolution, status in findings
            ],
        )
        self.db.commit()
        return audit_id

    def taxonomy_audit_history(self, *, limit: int = 10) -> list[sqlite3.Row]:
        return self.db.execute(
            """SELECT id, created_at, taxonomy_version, embedding_model, threshold, findings_count
               FROM taxonomy_audit_runs ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    def replace_profile(
        self,
        *,
        embedding_model: str,
        library_version: int | None,
        items: list[tuple[str, int, list[float], set[str]]],
    ) -> None:
        """Replace the local embedding profile from a complete library scan."""
        timestamp = now()
        vocabulary: dict[str, int] = {}
        for _key, _version, _vector, tags in items:
            for tag in tags:
                vocabulary[tag] = vocabulary.get(tag, 0) + 1
        with self.db:
            self.db.execute("DELETE FROM profile_items")
            self.db.execute("DELETE FROM profile_vocabulary")
            self.db.executemany(
                "INSERT INTO profile_items(item_key, item_version, vector_json, tags_json) VALUES (?, ?, ?, ?)",
                [
                    (
                        key,
                        version,
                        json.dumps(vector, separators=(",", ":")),
                        json.dumps(sorted(tags)),
                    )
                    for key, version, vector, tags in items
                ],
            )
            self.db.executemany(
                """INSERT INTO profile_vocabulary(raw_tag, normalized_tag, item_count, first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (tag, tag.strip().casefold(), count, timestamp, timestamp)
                    for tag, count in vocabulary.items()
                ],
            )
            self.db.execute(
                """INSERT INTO profile_runs(created_at, server_id, library_version, embedding_model, item_count, tag_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    timestamp,
                    self.get_zotero_server_id(),
                    library_version,
                    embedding_model,
                    len(items),
                    len(vocabulary),
                ),
            )

    def profile_status(self) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT created_at, embedding_model, item_count, tag_count FROM profile_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

    def profile_vocabulary(self, *, limit: int = 100) -> list[sqlite3.Row]:
        return self.db.execute(
            """SELECT vocabulary.raw_tag, vocabulary.item_count, mappings.canonical_tag
               FROM profile_vocabulary AS vocabulary
               LEFT JOIN profile_tag_mappings AS mappings ON mappings.raw_tag=vocabulary.raw_tag
               ORDER BY vocabulary.item_count DESC, vocabulary.raw_tag LIMIT ?""",
            (limit,),
        ).fetchall()

    def set_profile_mapping(
        self, raw_tag: str, canonical_tag: str, *, mapping_type: str = "alias"
    ) -> None:
        self.db.execute(
            """INSERT INTO profile_tag_mappings(raw_tag, canonical_tag, mapping_type, approved_at)
               VALUES (?, ?, ?, ?) ON CONFLICT(raw_tag) DO UPDATE SET
               canonical_tag=excluded.canonical_tag, mapping_type=excluded.mapping_type, approved_at=excluded.approved_at""",
            (raw_tag, canonical_tag, mapping_type, now()),
        )
        self.db.commit()

    def profile_mappings(self) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT raw_tag, canonical_tag, mapping_type FROM profile_tag_mappings ORDER BY raw_tag"
        ).fetchall()

    def profile_centroids(
        self, *, model: str, canonical_tags: set[str]
    ) -> dict[str, tuple[list[float], int]]:
        latest = self.profile_status()
        if latest is None or latest["embedding_model"] != model:
            return {}
        mappings = {row["raw_tag"]: row["canonical_tag"] for row in self.profile_mappings()}
        grouped: dict[str, list[list[float]]] = {}
        for row in self.db.execute("SELECT vector_json, tags_json FROM profile_items"):
            vector = json.loads(row["vector_json"])
            for raw_tag in json.loads(row["tags_json"]):
                canonical = raw_tag if raw_tag in canonical_tags else mappings.get(raw_tag)
                if canonical in canonical_tags:
                    grouped.setdefault(canonical, []).append(vector)
        return {
            tag: (
                [sum(values) / len(vectors) for values in zip(*vectors, strict=True)],
                len(vectors),
            )
            for tag, vectors in grouped.items()
        }
