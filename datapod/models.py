"""PodEntry data model with serialization and integrity checking."""

import hashlib
import json
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def generate_pod_id(length: int = 8) -> str:
    """Generate a clean, unambiguous hexadecimal / alphanumeric ID."""
    return secrets.token_hex(length // 2)


def calculate_sha256(data: bytes) -> str:
    """Compute sha256 checksum of data."""
    return hashlib.sha256(data).hexdigest()


@dataclass
class PodEntry:
    id: str
    original_filename: str
    holder: str
    content_hash: str
    size_bytes: int
    created_at: str  # ISO-8601 string
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: list = field(default_factory=list)

    @classmethod
    def create(
        cls,
        filename: str,
        data: bytes,
        holder: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
        custom_id: Optional[str] = None,
    ) -> "PodEntry":
        pod_id = custom_id if custom_id else generate_pod_id(8)
        content_hash = calculate_sha256(data)
        created_at = datetime.now().astimezone().isoformat()
        
        meta = metadata.copy() if metadata else {}
        
        return cls(
            id=pod_id,
            original_filename=Path(filename).name,
            holder=holder,
            content_hash=content_hash,
            size_bytes=len(data),
            created_at=created_at,
            metadata=meta,
            tags=tags or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PodEntry":
        return cls(
            id=data["id"],
            original_filename=data["original_filename"],
            holder=data.get("holder", "default"),
            content_hash=data["content_hash"],
            size_bytes=data["size_bytes"],
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )
