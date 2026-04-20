"""Diff engine for JSON, XML, and plain-text payloads.

Produces a line-aligned side-by-side diff with per-line tags:
  'equal'    — unchanged
  'added'    — only on the right
  'removed'  — only on the left
  'changed'  — present on both sides but differ
  'blank'    — spacer for alignment
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any
from xml.dom import minidom
from xml.etree import ElementTree as ET

PLACEHOLDER = "<<IGNORED>>"


def normalize(raw: str, fmt: str, ignore: list[str]) -> str:
    """Return a canonical, pretty-printed form with ignored fields masked."""
    raw = raw or ""
    fmt = (fmt or "text").lower()

    if fmt == "json":
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e.msg} (line {e.lineno}, col {e.colno})")
        obj = _mask_json(obj, ignore)
        return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)

    if fmt == "xml":
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")
        _mask_xml(root, ignore)
        rough = ET.tostring(root, encoding="unicode")
        pretty = minidom.parseString(rough).toprettyxml(indent="  ")
        return "\n".join(line for line in pretty.splitlines() if line.strip())

    masked = raw
    for pat in ignore:
        if not pat:
            continue
        try:
            masked = re.sub(pat, PLACEHOLDER, masked)
        except re.error:
            masked = masked.replace(pat, PLACEHOLDER)
    return masked


def _mask_json(obj: Any, ignore: list[str]) -> Any:
    keys = {k.strip() for k in ignore if k.strip()}
    if isinstance(obj, dict):
        return {
            k: (PLACEHOLDER if k in keys else _mask_json(v, ignore))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_mask_json(x, ignore) for x in obj]
    return obj


def _mask_xml(elem: ET.Element, ignore: list[str]) -> None:
    tags = {t.strip() for t in ignore if t.strip()}
    for child in list(elem):
        local = child.tag.split("}", 1)[-1]
        if local in tags:
            child.text = PLACEHOLDER
            for sub in list(child):
                child.remove(sub)
        else:
            _mask_xml(child, ignore)
        for attr in list(child.attrib):
            if attr in tags:
                child.attrib[attr] = PLACEHOLDER


def diff_lines(left: str, right: str) -> list[dict]:
    """Align two strings line-by-line for side-by-side rendering."""
    a = left.splitlines() or [""]
    b = right.splitlines() or [""]
    rows: list[dict] = []
    sm = SequenceMatcher(a=a, b=b, autojunk=False)

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append({
                    "tag": "equal",
                    "left_no": i1 + k + 1,
                    "right_no": j1 + k + 1,
                    "left": a[i1 + k],
                    "right": b[j1 + k],
                })
        elif tag == "replace":
            left_block = a[i1:i2]
            right_block = b[j1:j2]
            rows.extend(_align_replace(left_block, right_block, i1, j1))
        elif tag == "delete":
            for k in range(i2 - i1):
                rows.append({
                    "tag": "removed",
                    "left_no": i1 + k + 1,
                    "right_no": None,
                    "left": a[i1 + k],
                    "right": "",
                })
        elif tag == "insert":
            for k in range(j2 - j1):
                rows.append({
                    "tag": "added",
                    "left_no": None,
                    "right_no": j1 + k + 1,
                    "left": "",
                    "right": b[j1 + k],
                })
    return rows


def _align_replace(left_block, right_block, i_base, j_base):
    """Pair up replaced lines; pad the shorter side with blanks."""
    out = []
    n = max(len(left_block), len(right_block))
    for k in range(n):
        l_present = k < len(left_block)
        r_present = k < len(right_block)
        if l_present and r_present:
            out.append({
                "tag": "changed",
                "left_no": i_base + k + 1,
                "right_no": j_base + k + 1,
                "left": left_block[k],
                "right": right_block[k],
            })
        elif l_present:
            out.append({
                "tag": "removed",
                "left_no": i_base + k + 1,
                "right_no": None,
                "left": left_block[k],
                "right": "",
            })
        else:
            out.append({
                "tag": "added",
                "left_no": None,
                "right_no": j_base + k + 1,
                "left": "",
                "right": right_block[k],
            })
    return out


def summarize(rows: list[dict]) -> dict:
    counts = {"equal": 0, "added": 0, "removed": 0, "changed": 0}
    for r in rows:
        counts[r["tag"]] = counts.get(r["tag"], 0) + 1
    counts["total"] = len(rows)
    counts["identical"] = counts["added"] == 0 and counts["removed"] == 0 and counts["changed"] == 0
    return counts
