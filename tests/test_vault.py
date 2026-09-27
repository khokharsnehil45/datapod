import pytest
from pathlib import Path
from datapod.vault import PodVault
from datapod.models import PodEntry


def test_vault_add_and_pull(tmp_path):
    vault = PodVault(root_dir=tmp_path / "vault")
    sample_file = tmp_path / "test.txt"
    sample_file.write_text("Hello Datapod World!")

    entry = vault.add(
        sample_file,
        holder="alice",
        metadata={"project": "deep_space", "version": "1.0"},
        tags=["core", "raw"],
    )

    assert entry.id is not None
    assert len(entry.id) == 8
    assert entry.holder == "alice"
    assert entry.original_filename == "test.txt"
    assert entry.size_bytes == len("Hello Datapod World!")
    assert entry.metadata["project"] == "deep_space"
    assert "core" in entry.tags

    # Retrieve info
    retrieved = vault.get(entry.id)
    assert retrieved is not None
    assert retrieved.content_hash == entry.content_hash

    # Pull to a new location
    pull_dest = tmp_path / "restored.txt"
    _, dest = vault.pull(entry.id, output_path=pull_dest)
    assert dest.exists()
    assert dest.read_text() == "Hello Datapod World!"


def test_deduplication(tmp_path):
    vault = PodVault(root_dir=tmp_path / "vault")
    file1 = tmp_path / "f1.txt"
    file2 = tmp_path / "f2.txt"
    file1.write_text("Identical Content")
    file2.write_text("Identical Content")

    e1 = vault.add(file1, holder="user1")
    e2 = vault.add(file2, holder="user2")

    # IDs are unique, but content hash is shared
    assert e1.id != e2.id
    assert e1.content_hash == e2.content_hash

    # Only one blob should exist in blobs dir
    blobs = list((tmp_path / "vault" / "blobs").glob("*"))
    assert len(blobs) == 1


def test_vault_remove(tmp_path):
    vault = PodVault(root_dir=tmp_path / "vault")
    file1 = tmp_path / "secret.txt"
    file1.write_text("Top Secret")

    entry = vault.add(file1, holder="agent")
    assert vault.get(entry.id) is not None

    # Remove
    assert vault.remove(entry.id) is True
    assert vault.get(entry.id) is None
    assert vault.remove(entry.id) is False
