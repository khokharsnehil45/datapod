"""Terminal rendering and card formatters for datapod."""

import json
from typing import List, Union
from datapod.models import PodEntry


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable B, KB, MB, GB."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def render_entry_card(entry: PodEntry, title: str = "DATAPOD ENTRY") -> str:
    """Renders a single pod entry as an elegant box card."""
    lines = [
        f"  ID        :  {entry.id}",
        f"  File      :  {entry.original_filename}",
        f"  Holder    :  {entry.holder}",
        f"  Size      :  {format_bytes(entry.size_bytes)} ({entry.size_bytes:,} bytes)",
        f"  Timestamp :  {entry.created_at}",
        f"  SHA-256   :  {entry.content_hash[:16]}...",
    ]

    if entry.tags:
        lines.append(f"  Tags      :  {', '.join(entry.tags)}")

    meta_lines = []
    if entry.metadata:
        for k, v in entry.metadata.items():
            meta_lines.append(f"    • {k}: {v}")

    all_content_lines = lines + meta_lines
    max_len = max(len(l) for l in all_content_lines) if all_content_lines else 30
    box_width = max(max_len + 6, 44)

    border = "─" * (box_width - 2)
    sep = "─" * (box_width - 2)

    out = []
    out.append(f"╭{border}╮")
    title_text = f"\033[1;36m{title}\033[0m"
    out.append(f"│  {title_text}{' ' * (box_width - len(title) - 4)}│")
    out.append(f"├{sep}┤")

    for line in lines:
        k, v = line.split(":", 1)
        k_clean = k.strip()
        v_clean = v.strip()
        colored_line = f"│ \033[90m{k_clean:<9}:\033[0m \033[1m{v_clean}\033[0m"
        pad = box_width - len(k_clean) - len(v_clean) - 5
        out.append(f"{colored_line}{' ' * max(pad, 1)}│")

    if entry.metadata:
        out.append(f"├{sep}┤")
        out.append(f"│ \033[1;33mMetadata:\033[0m{' ' * (box_width - 12)}│")
        for k, v in entry.metadata.items():
            val_str = str(v)
            meta_str = f"  \033[90m•\033[0m {k}: \033[37m{val_str}\033[0m"
            pad = box_width - len(k) - len(val_str) - 8
            out.append(f"│{meta_str}{' ' * max(pad, 1)}│")

    out.append(f"╰{border}╯")
    return "\n".join(out)


def render_table(entries: List[PodEntry]) -> str:
    """Renders a collection of entries in a clean CLI table."""
    if not entries:
        return "\033[90m(No pods stored in vault. Use `datapod -add <file>` to store data)\033[0m"

    out = []
    header = f"{'ID':<10} {'HOLDER':<14} {'FILE':<22} {'SIZE':<10} {'TIMESTAMP':<20}"
    border = "─" * len(header)
    out.append(f"\033[1m{header}\033[0m")
    out.append(f"\033[90m{border}\033[0m")

    for e in entries:
        dt = e.created_at.split("T")[0] + " " + e.created_at.split("T")[1][:5]
        row = (
            f"\033[1;36m{e.id:<10}\033[0m "
            f"\033[33m{e.holder:<14}\033[0m "
            f"\033[1m{e.original_filename[:20]:<22}\033[0m "
            f"\033[90m{format_bytes(e.size_bytes):<10}\033[0m "
            f"\033[90m{dt:<20}\033[0m"
        )
        out.append(row)

    return "\n".join(out)
