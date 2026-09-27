"""Vault storage engine for managing files, blobs, and metadata."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from datapod.models import PodEntry


class PodVault:
    """Manages the datapod storage repository."""

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is not None:
            self.root_dir = Path(root_dir)
        else:
            # Check for local workspace vault first, then fallback to global ~/.datapod
            local_vault = self._find_local_vault(Path.cwd())
            if local_vault:
                self.root_dir = local_vault
            else:
                self.root_dir = Path.home() / ".datapod"

        self.blobs_dir = self.root_dir / "blobs"
        self.meta_dir = self.root_dir / "meta"
        self._ensure_dirs()

    @staticmethod
    def _find_local_vault(start_path: Path) -> Optional[Path]:
        current = start_path.resolve()
        while True:
            candidate = current / ".datapod"
            if candidate.is_dir():
                return candidate
            if current.parent == current:
                break
            current = current.parent
        return None

    def _ensure_dirs(self) -> None:
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _meta_file(self, pod_id: str) -> Path:
        return self.meta_dir / f"{pod_id}.json"

    def _blob_file(self, content_hash: str) -> Path:
        return self.blobs_dir / content_hash

    def add(
        self,
        file_path: Path,
        holder: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
    ) -> PodEntry:
        """Store a file and its metadata into the vault."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'")
        if not file_path.is_file():
            raise ValueError(f"Target must be a regular file: '{file_path}'")

        data = file_path.read_bytes()
        entry = PodEntry.create(
            filename=file_path.name,
            data=data,
            holder=holder,
            metadata=metadata,
            tags=tags,
        )

        # Store content blob (content-addressable by hash)
        blob_path = self._blob_file(entry.content_hash)
        if not blob_path.exists():
            # Atomic write
            with tempfile.NamedTemporaryFile(dir=self.blobs_dir, delete=False) as tf:
                tf.write(data)
                temp_name = tf.name
            os.replace(temp_name, blob_path)

        # Store metadata JSON (atomic write)
        meta_path = self._meta_file(entry.id)
        with tempfile.NamedTemporaryFile("w", dir=self.meta_dir, delete=False, encoding="utf-8") as tf:
            json.dump(entry.to_dict(), tf, indent=2)
            temp_name = tf.name
        os.replace(temp_name, meta_path)

        return entry

    def add_content(
        self,
        filename: str,
        data: bytes,
        holder: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
    ) -> PodEntry:
        """Store raw bytes content directly."""
        entry = PodEntry.create(
            filename=filename,
            data=data,
            holder=holder,
            metadata=metadata,
            tags=tags,
        )

        blob_path = self._blob_file(entry.content_hash)
        if not blob_path.exists():
            with tempfile.NamedTemporaryFile(dir=self.blobs_dir, delete=False) as tf:
                tf.write(data)
                temp_name = tf.name
            os.replace(temp_name, blob_path)

        meta_path = self._meta_file(entry.id)
        with tempfile.NamedTemporaryFile("w", dir=self.meta_dir, delete=False, encoding="utf-8") as tf:
            json.dump(entry.to_dict(), tf, indent=2)
            temp_name = tf.name
        os.replace(temp_name, meta_path)

        return entry

    def get(self, pod_id: str) -> Optional[PodEntry]:
        """Fetch metadata for a pod ID."""
        meta_path = self._meta_file(pod_id)
        if not meta_path.exists():
            # Check for partial prefix match
            matches = list(self.meta_dir.glob(f"{pod_id}*.json"))
            if len(matches) == 1:
                meta_path = matches[0]
            else:
                return None

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return PodEntry.from_dict(data)
        except Exception:
            return None

    def pull(self, pod_id: str, output_path: Optional[Path] = None) -> Tuple[PodEntry, Path]:
        """Extract the stored file for a given pod ID."""
        entry = self.get(pod_id)
        if not entry:
            raise KeyError(f"Pod ID '{pod_id}' not found in vault")

        blob_path = self._blob_file(entry.content_hash)
        if not blob_path.exists():
            raise FileNotFoundError(f"Content blob missing for pod {pod_id} (hash {entry.content_hash})")

        if output_path is None:
            # Save into current working directory with original filename
            dest = Path.cwd() / entry.original_filename
        else:
            dest = Path(output_path)
            if dest.is_dir():
                dest = dest / entry.original_filename

        shutil.copy2(blob_path, dest)
        return entry, dest

    def read_bytes(self, pod_id: str) -> Tuple[PodEntry, bytes]:
        """Read pod file content into memory."""
        entry = self.get(pod_id)
        if not entry:
            raise KeyError(f"Pod ID '{pod_id}' not found in vault")
        blob_path = self._blob_file(entry.content_hash)
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob data missing for pod {pod_id}")
        return entry, blob_path.read_bytes()

    def list_all(self, holder: Optional[str] = None) -> List[PodEntry]:
        """List all entries in the vault, optionally filtered by holder."""
        entries = []
        for meta_file in sorted(self.meta_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                entry = PodEntry.from_dict(data)
                if holder is None or entry.holder.lower() == holder.lower():
                    entries.append(entry)
            except Exception:
                continue
        return entries

    def remove(self, pod_id: str) -> bool:
        """Remove a pod entry by ID."""
        entry = self.get(pod_id)
        if not entry:
            return False

        meta_path = self._meta_file(entry.id)
        if meta_path.exists():
            meta_path.unlink()

        # Check if any other pod references the same content hash
        hash_still_referenced = False
        for mf in self.meta_dir.glob("*.json"):
            try:
                d = json.loads(mf.read_text(encoding="utf-8"))
                if d.get("content_hash") == entry.content_hash:
                    hash_still_referenced = True
                    break
            except Exception:
                pass

        if not hash_still_referenced:
            blob = self._blob_file(entry.content_hash)
            if blob.exists():
                blob.unlink()

        return True
