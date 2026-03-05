#!/usr/bin/env python3
"""
Sync source files into MorseTrainer/ for Arduino IDE compatibility.

On macOS/Linux, MorseTrainer/ uses symlinks back to src/, include/, and data/.
On Windows, git clones these symlinks as plain text files unless Developer Mode
is enabled. This script copies the real files into MorseTrainer/ so Arduino IDE
works regardless of OS or git symlink support.

Files that are already valid symlinks are skipped (no work needed).
Files are only overwritten if the source is newer than the destination,
unless --force is used to overwrite all files unconditionally.

After syncing, a verification pass warns about any remaining broken symlinks.

Usage: python sync_arduino.py [--force]
"""

import os
import shutil
import sys

PROJ_ROOT = os.path.dirname(os.path.abspath(__file__))
ARDUINO_DIR = os.path.join(PROJ_ROOT, "MorseTrainer")

# Files to skip entirely (never copied)
SKIP_ALWAYS = {
    "src": {"main.cpp"},
    "include": set(),
    "data": set(),
}

# Files to copy only if the destination doesn't exist yet.
# Once present, the user's local edits are preserved across syncs.
PRESERVE_IF_EXISTS = {
    "include": {"config.h"},
}

# (source_dir, dest_dir)
SYNC_RULES = [
    ("src",     ARDUINO_DIR),
    ("include", ARDUINO_DIR),
    ("data",    os.path.join(ARDUINO_DIR, "data")),
]


def is_broken_symlink_text(filepath):
    """Check if a file is a git-created text file standing in for a symlink.

    On Windows without Developer Mode, git writes a small text file
    containing the symlink target path (e.g. ../src/buzzer.cpp).
    """
    try:
        size = os.path.getsize(filepath)
    except OSError:
        return False
    if size >= 100:
        return False
    try:
        with open(filepath, "r", errors="ignore") as f:
            content = f.read().strip()
    except OSError:
        return False
    # Check both forward-slash (git default) and backslash (rare) paths
    return content.startswith("../") or content.startswith("..\\")


def needs_copy(src, dst, force=False):
    """Return True if dst is missing, older than src, or force is set."""
    if not os.path.exists(dst):
        return True
    # Don't copy a file onto itself (e.g. through a directory symlink)
    try:
        if os.path.samefile(src, dst):
            return False
    except OSError:
        pass
    if force:
        return True
    return os.path.getmtime(src) > os.path.getmtime(dst)


def sync(force=False):
    copied = 0
    skipped_symlink = 0
    up_to_date = 0
    preserved = 0

    for src_subdir, dest_dir in SYNC_RULES:
        src_dir = os.path.join(PROJ_ROOT, src_subdir)
        if not os.path.isdir(src_dir):
            print(f"  WARNING: {src_subdir}/ not found, skipping")
            continue

        # On Windows without Developer Mode, git clones symlinks as small
        # text files containing the target path. Replace these with real
        # directories so we can copy files into them.
        if os.path.exists(dest_dir) and not os.path.isdir(dest_dir):
            os.remove(dest_dir)
            print(f"  Replaced broken symlink: {os.path.relpath(dest_dir, PROJ_ROOT)}")

        os.makedirs(dest_dir, exist_ok=True)

        skip_files = SKIP_ALWAYS.get(src_subdir, set())
        preserve_files = PRESERVE_IF_EXISTS.get(src_subdir, set())

        for filename in sorted(os.listdir(src_dir)):
            if filename in skip_files:
                continue

            src_path = os.path.join(src_dir, filename)
            if not os.path.isfile(src_path):
                continue

            dst_path = os.path.join(dest_dir, filename)

            # Skip if destination is already a working symlink
            if os.path.islink(dst_path) and os.path.exists(dst_path):
                skipped_symlink += 1
                continue

            # Detect and remove broken symlink text files
            if os.path.isfile(dst_path) and is_broken_symlink_text(dst_path):
                os.remove(dst_path)
                print(f"  Replaced broken symlink: MorseTrainer/{os.path.relpath(dst_path, ARDUINO_DIR)}")

            # Preserve user-edited files (e.g. config.h with board selection)
            if filename in preserve_files and os.path.exists(dst_path):
                preserved += 1
                continue

            if needs_copy(src_path, dst_path, force):
                shutil.copy2(src_path, dst_path)
                print(f"  Copied: {src_subdir}/{filename} -> MorseTrainer/{os.path.relpath(dst_path, ARDUINO_DIR)}")
                copied += 1
            else:
                up_to_date += 1

    return copied, skipped_symlink, up_to_date, preserved


def verify():
    """Scan MorseTrainer/ for any remaining broken symlink text files."""
    problems = []
    for entry in sorted(os.listdir(ARDUINO_DIR)):
        path = os.path.join(ARDUINO_DIR, entry)
        if os.path.isfile(path) and entry != "MorseTrainer.ino":
            if is_broken_symlink_text(path):
                problems.append(entry)
    # Also check data/ subdirectory
    data_dir = os.path.join(ARDUINO_DIR, "data")
    if os.path.isdir(data_dir):
        for entry in sorted(os.listdir(data_dir)):
            path = os.path.join(data_dir, entry)
            if os.path.isfile(path) and is_broken_symlink_text(path):
                problems.append(f"data/{entry}")
    return problems


def main():
    force = "--force" in sys.argv

    print("Syncing Arduino IDE files (MorseTrainer/)...")
    if force:
        print("  (--force: overwriting all files)")
    print()

    if not os.path.isdir(ARDUINO_DIR):
        print(f"ERROR: MorseTrainer/ directory not found at {ARDUINO_DIR}")
        sys.exit(1)

    copied, skipped_symlink, up_to_date, preserved = sync(force)

    print()
    if copied == 0 and skipped_symlink > 0:
        print(f"All {skipped_symlink} files are symlinks — nothing to copy.")
    elif copied == 0:
        print("All files up to date.")
    else:
        print(f"Done: {copied} file(s) copied, {up_to_date} already up to date.")

    if preserved > 0:
        print(f"  ({preserved} user-edited file(s) preserved — delete to re-sync from source)")

    # Verify no broken symlinks remain
    problems = verify()
    if problems:
        print()
        print("WARNING: The following files still look like broken symlinks:")
        for p in problems:
            print(f"  MorseTrainer/{p}")
        print("Try running: python sync_arduino.py --force")
        sys.exit(1)


if __name__ == "__main__":
    main()
