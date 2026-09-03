#!/usr/bin/env python3
"""
to_meta.py

Reads and writes the Tool dataclass "meta format" — a lossless, converter-
agnostic dump of every Tool field, independent of hsmlib or SolidWorks CSV
quirks. Two on-disk representations are supported:

- JSON: a list of objects, one per tool, keys = Tool field names.
- CSV:  one row per tool, header row = Tool field names (dataclasses.fields
        order), so the column names are never hand-typed and can't drift out
        of sync with the Tool dataclass.

Both formats can be used as:
  1. An additional *output* produced alongside a normal hsmlib/SW-CSV
     conversion (--dump-meta-json / --dump-meta-csv in toolconverter.py).
  2. A *source* format: convert_meta_to_hsmlib() / convert_meta_to_solidworks()
     read a meta file directly and re-use the existing write_hsmlib() /
     write_csv() pipelines, skipping parse_hsmlib()/parse_solidworks_csv()
     entirely since the meta file already holds fully-typed Tool objects.

Copyright (C) 2026 Codeblame

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import csv
import json
from dataclasses import fields, asdict
from pathlib import Path

from data import Tool
from to_swcam import tapered_mill_sw_type


# ─── Field introspection ──────────────────────────────────────────────────────

def tool_field_names():
    """Returns the Tool dataclass field names, in declaration order."""
    return [f.name for f in fields(Tool)]


def _cast_value(field, raw):
    """
    Casts a raw string/JSON value back to the type declared on the Tool
    dataclass field (str / float / int / bool). Falls back to the field
    default if casting fails or the field has no usable type annotation.
    """
    if raw is None:
        return field.default
    ftype = field.type
    # dataclasses.fields() may return the type as a string ("float") when
    # `from __future__ import annotations` is active; normalize both cases.
    ftype_name = ftype if isinstance(ftype, str) else getattr(ftype, "__name__", str(ftype))

    if ftype_name == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if ftype_name == "int":
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return field.default
    if ftype_name == "float":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return field.default
    # str and anything else: keep as-is (JSON already gives native str,
    # CSV gives str too via csv.DictReader).
    return "" if raw is None else str(raw)


def tool_from_row(row: dict) -> Tool:
    """
    Builds a Tool from a flat {field_name: raw_value} mapping (a CSV row or
    a parsed JSON object), casting each value to the type declared on the
    Tool dataclass. Unknown keys in `row` are ignored; missing keys fall
    back to the Tool dataclass defaults.
    """
    kwargs = {}
    for f in fields(Tool):
        if f.name in row and row[f.name] not in (None, ""):
            kwargs[f.name] = _cast_value(f, row[f.name])
    return Tool(**kwargs)


# ─── Format detection ──────────────────────────────────────────────────────────

def is_meta_csv(path) -> bool:
    """
    Distinguishes a meta CSV (header = Tool dataclass field names) from a
    SolidWorks-exported CSV (header = SW column names like "Tool ID",
    "Overall Length (L1)", etc.) by checking whether the first header row
    consists exclusively of known Tool field names. Used by toolconverter.py since
    both formats share the ".csv" extension.
    """
    try:
        with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
            first_line = f.readline().strip()
    except OSError:
        return False
    if not first_line:
        return False
    header_cols = [c.strip() for c in first_line.split(',')]
    known = set(tool_field_names())
    return len(header_cols) > 0 and all(c in known for c in header_cols)


def is_meta_json(path) -> bool:
    """
    Distinguishes a meta JSON file (list of Tool-field dicts) from any other
    JSON. Considered a meta file if it parses as a list/dict whose keys are
    a subset of known Tool field names (checked on the first element).
    """
    try:
        raw = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return False
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
        return False
    known = set(tool_field_names())
    return all(k in known for k in raw[0].keys())


# ─── Writers: Tool list -> meta JSON / meta CSV ───────────────────────────────

def write_meta_json(tools, output_path):
    """
    Writes `tools` (list[Tool]) as a JSON array of objects, one per tool,
    with the Tool dataclass field names as keys (dataclasses.asdict order).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(tool) for tool in tools]
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f" ✅ {output_path.name} ({len(tools)} Tools, meta JSON)")
    return output_path


def write_meta_csv(tools, output_path):
    """
    Writes `tools` (list[Tool]) as a CSV file, one row per tool. The header
    row uses the Tool dataclass member variable names as column names
    (dataclasses.fields order), so the columns can't drift out of sync with
    the dataclass definition.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = tool_field_names()
    with output_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for tool in tools:
            writer.writerow(asdict(tool))
    print(f" ✅ {output_path.name} ({len(tools)} Tools, meta CSV)")
    return output_path


def write_meta(tools, output_dir, base_name, as_json=True, as_csv=True):
    """
    Convenience wrapper: writes the requested meta format(s) for `tools`
    into output_dir, named "{base_name}_meta.json" / "{base_name}_meta.csv".
    Returns the list of written Paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    if as_json:
        written.append(write_meta_json(tools, output_dir / f"{base_name}.json"))
    if as_csv:
        written.append(write_meta_csv(tools, output_dir / f"{base_name}.csv"))
    return written


# ─── Readers: meta JSON / meta CSV -> Tool list ───────────────────────────────

def parse_meta_json(path) -> list:
    """Reads a meta JSON file (as written by write_meta_json) into list[Tool]."""
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(raw, dict):
        raw = [raw]
    return [tool_from_row(row) for row in raw]


def parse_meta_csv(path) -> list:
    """Reads a meta CSV file (as written by write_meta_csv) into list[Tool]."""
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return [tool_from_row(row) for row in reader]


def parse_meta_file(path) -> list:
    """Dispatches to parse_meta_json / parse_meta_csv based on file suffix."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == '.json':
        return parse_meta_json(path)
    if suffix == '.csv':
        return parse_meta_csv(path)
    raise ValueError(f"Unsupported meta file type: {suffix}")


# ─── Meta file as conversion source ───────────────────────────────────────────
# These mirror convert_hsmlib_to_solidworks() / convert_solidworks_to_hsmlib()
# but skip the format-specific parser, since the meta file already holds
# fully-typed Tool objects.

def convert_meta_to_solidworks(input_path, output_dir):
    """
    Converts a meta JSON/CSV file directly into one or more SolidWorks CAM
    CSV files, reusing the existing hsmlib->CSV row-building/dispatch logic
    in to_swcam.py (write_csv, ROW_BUILDERS, convert_hsm_to_sw).
    """
    from to_swcam import write_csv
    from data import HSMToolType, convert_hsm_to_sw, SWToolType

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = Path(input_path).stem
    tools = parse_meta_file(input_path)

    if not tools:
        print('⚠️ No tools found in meta file!')
        return []

    tools_by_type = {}
    skipped = 0
    for tool in tools:
        try:
            hsm_type = HSMToolType(tool.type)
        except ValueError:
            print(f"⚠️ Skipping unknown tool type: {tool.type!r} ({tool.description})")
            skipped += 1
            continue

        sw_type = convert_hsm_to_sw(hsm_type)
        if sw_type is SWToolType.THREAD_MULTI and tool.thread_nr_teeth == 0:
            sw_type = SWToolType.THREAD_SINGLE
        if sw_type in (SWToolType.TAPS_LH, SWToolType.TAPS_RH):
            sw_type = SWToolType.TAPS_RH
        if sw_type == SWToolType.TAPER_FLATEND:
            sw_type = tapered_mill_sw_type(tool)

        if not tool.name and tool.description:
            tool.name = tool.description

        tools_by_type.setdefault(sw_type, []).append(tool)

    written = write_csv(tools_by_type, output_dir, name)
    print(f"\n✅ Done — {len(tools) - skipped} tools exported into {len(written)} CSV file(s)"
          f"{f', {skipped} skipped' if skipped else ''}.")
    return written


def convert_meta_to_hsmlib(input_path, output_path):
    """
    Converts a meta JSON/CSV file directly into a .hsmlib file, reusing the
    existing Tool->hsmlib writer in to_hsmlib.py (write_hsmlib).
    """
    from to_hsmlib import write_hsmlib

    tools = parse_meta_file(input_path)
    if not tools:
        print('⚠️ No tools found in meta file!')
        return None

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = write_hsmlib(tools, output_path)
    print(f"\n✅ Done — {len(tools)} tools exported into {output_path.name}.")
    return written


def convert_meta(input_path, output_path, to_json=True):
    tools = parse_meta_file(input_path)
    if not tools:
        print('⚠️ No tools found in meta file!')
        return None

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = write_meta(tools, output_path, input_path.stem, to_json, not to_json)

    print(f"\n✅ Done — {len(tools)} tools exported into {output_path.name}.")
    return written
