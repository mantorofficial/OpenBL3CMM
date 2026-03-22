"""
Datapack generator for OpenBL3CMM Object Explorer.

This script can create a datapack from:
  1. apocalyptech's bl3refs.sqlite3 (object references database)
  2. Extracted BL3 JSON data (from unpacked PAK files)
  3. A list of object paths (minimal, just for browsing/search)

Usage:
  python generate_datapack.py --from-refs bl3refs.sqlite3 --output bl3data.sqlite3
  python generate_datapack.py --from-json /path/to/extracted/ --output bl3data.sqlite3
  python generate_datapack.py --from-paths paths.txt --output bl3data.sqlite3
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path


def create_empty_db(path: str) -> sqlite3.Connection:
    """Create a new datapack database with the correct schema."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS objects (
            path TEXT PRIMARY KEY,
            class_name TEXT,
            data TEXT
        );

        CREATE TABLE IF NOT EXISTS refs (
            source TEXT NOT NULL,
            target TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS classes (
            name TEXT PRIMARY KEY,
            parent TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_refs_source ON refs(source);
        CREATE INDEX IF NOT EXISTS idx_refs_target ON refs(target);
        CREATE INDEX IF NOT EXISTS idx_objects_class ON objects(class_name);
    """)
    conn.commit()
    return conn


def import_from_refs_db(refs_path: str, output_path: str):
    """
    Import from apocalyptech's bl3refs.sqlite3.
    This gives us object paths and their references, but no property data.
    """
    print(f"Loading refs database: {refs_path}")
    refs_conn = sqlite3.connect(refs_path)
    refs_conn.row_factory = sqlite3.Row

    out_conn = create_empty_db(output_path)

    # Check what tables exist in the refs DB
    cursor = refs_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor}
    print(f"  Tables found: {tables}")

    # Import references
    if "refs" in tables:
        print("  Importing references...")
        cursor = refs_conn.execute("SELECT * FROM refs")
        batch = []
        count = 0
        for row in cursor:
            # The refs table might have different column names
            cols = row.keys()
            if "source" in cols and "target" in cols:
                batch.append((row["source"], row["target"]))
            elif len(cols) >= 2:
                batch.append((row[cols[0]], row[cols[1]]))

            if len(batch) >= 10000:
                out_conn.executemany("INSERT OR IGNORE INTO refs (source, target) VALUES (?, ?)", batch)
                count += len(batch)
                batch = []

        if batch:
            out_conn.executemany("INSERT OR IGNORE INTO refs (source, target) VALUES (?, ?)", batch)
            count += len(batch)

        out_conn.commit()
        print(f"  Imported {count:,} references")

    # Extract unique object paths from refs
    print("  Extracting object paths from references...")
    out_conn.execute("""
        INSERT OR IGNORE INTO objects (path, class_name, data)
        SELECT DISTINCT source, NULL, NULL FROM refs
    """)
    out_conn.execute("""
        INSERT OR IGNORE INTO objects (path, class_name, data)
        SELECT DISTINCT target, NULL, NULL FROM refs
    """)
    out_conn.commit()

    cursor = out_conn.execute("SELECT COUNT(*) as c FROM objects")
    obj_count = cursor.fetchone()[0]
    print(f"  Total unique objects: {obj_count:,}")

    refs_conn.close()
    out_conn.close()
    print(f"Datapack saved: {output_path}")


def import_from_json(json_dir: str, output_path: str, refs_db: str = ""):
    """
    Import from extracted BL3 JSON files (from unpacked PAK files).
    Each .json file contains one object's data.
    Optionally merge with a bl3refs.sqlite3 for reference data.
    """
    json_path = Path(json_dir)
    if not json_path.is_dir():
        print(f"Error: {json_dir} is not a directory")
        return

    out_conn = create_empty_db(output_path)

    # Enable WAL mode for faster writes
    out_conn.execute("PRAGMA journal_mode=WAL")
    out_conn.execute("PRAGMA synchronous=OFF")

    print(f"Scanning JSON files in: {json_dir}")
    count = 0
    batch = []

    for json_file in json_path.rglob("*.json"):
        try:
            relative = json_file.relative_to(json_path)
            obj_path = "/" + str(relative.with_suffix("")).replace("\\", "/")

            with open(json_file, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()

            # Try to extract class name
            class_name = ""
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list) and parsed:
                    first = parsed[0]
                    if isinstance(first, dict):
                        class_name = first.get("export_type", "")
                elif isinstance(parsed, dict):
                    class_name = parsed.get("export_type", "")
            except json.JSONDecodeError:
                pass

            # Compress JSON data with zlib to save space
            import zlib
            compressed = zlib.compress(data.encode("utf-8"), 6)

            batch.append((obj_path, class_name, compressed))
            count += 1

            if len(batch) >= 1000:
                out_conn.executemany(
                    "INSERT OR REPLACE INTO objects (path, class_name, data) VALUES (?, ?, ?)",
                    batch
                )
                out_conn.commit()
                batch = []
                print(f"  Processed {count:,} files...", end="\r")

        except Exception as e:
            print(f"  Warning: Failed to process {json_file}: {e}")

    if batch:
        out_conn.executemany(
            "INSERT OR REPLACE INTO objects (path, class_name, data) VALUES (?, ?, ?)",
            batch
        )
        out_conn.commit()

    print(f"\n  Total objects imported: {count:,}")

    # Merge refs if provided
    if refs_db and Path(refs_db).is_file():
        print(f"  Merging references from: {refs_db}")
        _merge_refs(out_conn, refs_db)

    # Optimize
    print("  Optimizing database...")
    out_conn.execute("PRAGMA journal_mode=DELETE")
    out_conn.execute("VACUUM")
    out_conn.close()

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Datapack saved: {output_path} ({size_mb:.1f} MB)")


def import_from_7z(archive_path: str, output_path: str, refs_db: str = ""):
    """
    Import from a 7z archive of JSON files (like Grimm's serialized data).
    Extracts to a temp directory then processes.
    Requires: pip install py7zr
    """
    try:
        import py7zr
    except ImportError:
        print("Error: py7zr is required. Install with: pip install py7zr")
        return

    import tempfile
    import shutil
    import zlib

    print(f"Opening archive: {archive_path}")

    with py7zr.SevenZipFile(archive_path, "r") as archive:
        names = [n for n in archive.getnames() if n.endswith(".json")]
        print(f"  Found {len(names):,} JSON files in archive")

        # Extract to temp directory
        tmp_dir = tempfile.mkdtemp(prefix="bl3data_")
        print(f"  Extracting to temp directory: {tmp_dir}")
        print(f"  This may take a while for large archives...")

        try:
            archive.extractall(path=tmp_dir)
            print(f"  Extraction complete. Processing JSON files...")

            # Now process as a regular directory
            import_from_json(tmp_dir, output_path, refs_db=refs_db)

        finally:
            # Clean up temp dir
            print(f"  Cleaning up temp directory...")
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _merge_refs(out_conn: sqlite3.Connection, refs_path: str):
    """Merge references AND object paths from a bl3refs.sqlite3 into the output database."""
    refs_conn = sqlite3.connect(refs_path)
    refs_conn.row_factory = sqlite3.Row

    cursor = refs_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor}

    if "bl3refs" in tables and "bl3object" in tables:
        # Import all object paths (so we get Engine, GbxAI, etc.)
        print("  Importing object paths from refs database...")
        cursor = refs_conn.execute("SELECT name FROM bl3object ORDER BY name")
        batch = []
        path_count = 0
        for row in cursor:
            batch.append((row["name"], None, None))
            if len(batch) >= 10000:
                out_conn.executemany(
                    "INSERT OR IGNORE INTO objects (path, class_name, data) VALUES (?, ?, ?)",
                    batch
                )
                path_count += len(batch)
                batch = []
        if batch:
            out_conn.executemany(
                "INSERT OR IGNORE INTO objects (path, class_name, data) VALUES (?, ?, ?)",
                batch
            )
            path_count += len(batch)
        out_conn.commit()
        print(f"  Merged {path_count:,} object paths")

        # Import references
        print("  Importing references...")
        cursor = refs_conn.execute("""
            SELECT a.name as source, b.name as target
            FROM bl3refs r
            JOIN bl3object a ON r.from_obj = a.id
            JOIN bl3object b ON r.to_obj = b.id
        """)
        batch = []
        count = 0
        for row in cursor:
            batch.append((row["source"], row["target"]))
            if len(batch) >= 10000:
                out_conn.executemany("INSERT OR IGNORE INTO refs (source, target) VALUES (?, ?)", batch)
                count += len(batch)
                batch = []
        if batch:
            out_conn.executemany("INSERT OR IGNORE INTO refs (source, target) VALUES (?, ?)", batch)
            count += len(batch)
        out_conn.commit()
        print(f"  Merged {count:,} references")

    refs_conn.close()


def import_from_paths(paths_file: str, output_path: str):
    """Import from a text file with one object path per line."""
    out_conn = create_empty_db(output_path)

    print(f"Loading paths from: {paths_file}")
    count = 0
    batch = []

    with open(paths_file, "r") as f:
        for line in f:
            path = line.strip()
            if not path or path.startswith("#"):
                continue

            # Try to extract class name from path
            class_name = ""
            parts = path.rsplit(".", 1)
            if len(parts) > 1:
                class_name = parts[-1]

            batch.append((path, class_name, None))
            count += 1

            if len(batch) >= 10000:
                out_conn.executemany(
                    "INSERT OR IGNORE INTO objects (path, class_name, data) VALUES (?, ?, ?)",
                    batch
                )
                batch = []

    if batch:
        out_conn.executemany(
            "INSERT OR IGNORE INTO objects (path, class_name, data) VALUES (?, ?, ?)",
            batch
        )

    out_conn.commit()
    out_conn.close()
    print(f"  Imported {count:,} paths")
    print(f"Datapack saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate OpenBL3CMM Object Explorer datapack")
    parser.add_argument("--from-refs", help="Path to bl3refs.sqlite3")
    parser.add_argument("--from-json", help="Path to extracted JSON directory")
    parser.add_argument("--from-7z", help="Path to 7z archive of JSON files (e.g. Grimm's data)")
    parser.add_argument("--from-paths", help="Path to text file with object paths")
    parser.add_argument("--merge-refs", help="Also merge references from bl3refs.sqlite3", default="")
    parser.add_argument("--output", "-o", default="bl3data.sqlite3", help="Output datapack path")

    args = parser.parse_args()

    if args.from_refs:
        import_from_refs_db(args.from_refs, args.output)
    elif args.from_json:
        import_from_json(args.from_json, args.output, refs_db=args.merge_refs)
    elif args.from_7z:
        import_from_7z(args.from_7z, args.output, refs_db=args.merge_refs)
    elif args.from_paths:
        import_from_paths(args.from_paths, args.output)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  # Refs only (small, fast):")
        print("  python generate_datapack.py --from-refs bl3refs.sqlite3 -o bl3data.sqlite3")
        print("")
        print("  # Full data from Grimm's 7z + refs (best, single file):")
        print("  python generate_datapack.py --from-7z Serialized.7z --merge-refs bl3refs.sqlite3 -o bl3data.sqlite3")
        print("")
        print("  # Full data from extracted JSON folder + refs:")
        print("  python generate_datapack.py --from-json ./extracted/ --merge-refs bl3refs.sqlite3 -o bl3data.sqlite3")


if __name__ == "__main__":
    main()
