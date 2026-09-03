#!/usr/bin/env python3
"""
dreanique_to_meta.py

Extracts tool geometry from the Dreanique PDF catalog and writes it out as
the converter-agnostic Tool "meta format" (CSV and/or JSON).

PDF -> raw dicts -> Tool objects -> write_meta() -> meta CSV/JSON

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

import sys
from pathlib import Path

def find_project_root(marker: str = "toolconverter.py") -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent
    raise RuntimeError(f"Project root with '{marker}' not found.")

sys.path.insert(0, str(find_project_root()))

import argparse
from collections import Counter
import pdfplumber

from dreanique_library_helper import *
from helper import *
from to_meta import write_meta

# ─── Series metadata: item-code prefix -> (hsm type, flutes, coating, material) ──
SERIES_META = {
    # ── Wood ──────────────────────────────────────────────────────────────────
    "WU2F": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, Laminate, MDF, HDF, Plywood"),
    "AWU2F": ("flat end mill", 2, "TAC", "Hardwood, Softwood, Laminate, MDF, HDF, Plywood"),
    "WD2F": ("flat end mill", 2, "Uncoated",
             "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "DWD2F": ("flat end mill", 2, "DLC", "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "AWD2F": ("flat end mill", 2, "TAC", "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "SP1FC": ("flat end mill", 1, "Uncoated",
              "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "SP2FC": ("flat end mill", 2, "Uncoated",
              "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "DSP2FC": ("flat end mill", 2, "DLC", "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "ASP2FC": ("flat end mill", 2, "TAC", "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "SP3FC": ("flat end mill", 3, "Uncoated",
              "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "ST2F": ("flat end mill", 2, "Uncoated",
             "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "DST2F": ("flat end mill", 2, "DLC", "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "ST3FK": ("flat end mill", 3, "Uncoated",
              "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "C2SF": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, Laminate, MDF, HDF"),
    "WU3C": ("flat end mill", 3, "Uncoated",
             "Hardwood, Softwood, Laminate, MDF, HDF, Veneered Plywood, Particle Board"),
    "W2B": ("ball end mill", 2, "Uncoated", "Hardwood, Softwood, Aluminum, Non-Ferrous, MDF, Plastic, Sign Foam"),
    "WTU2F": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, Laminate, Plywood"),
    "AWTU2F": ("flat end mill", 2, "TAC", "Hardwood, Softwood, Laminate, Plywood"),
    "WTD2F": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, Laminate, Plywood"),
    "AWTD2F": ("flat end mill", 2, "TAC", "Hardwood, Softwood, Laminate, Plywood"),
    "WTUD2F": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, Laminate, Plywood"),
    "AWTUD2F": ("flat end mill", 2, "TAC", "Hardwood, Softwood, Laminate, Plywood"),
    "DWTUD2F": ("flat end mill", 2, "DLC", "Hardwood, Softwood, Laminate, Plywood"),
    "PCB": ("flat end mill", 2, "Uncoated", "PCB Board, Carbon Fiber, Composites, Fiberglass"),
    # ── Acryl ─────────────────────────────────────────────────────────────────
    "SP1F": ("flat end mill", 1, "Uncoated", "Acrylic"),
    "DSP1F": ("flat end mill", 1, "DLC", "Acrylic"),
    "ZSP1F": ("flat end mill", 1, "ZrN", "Acrylic"),
    "ASP1F": ("flat end mill", 1, "TAC", "Acrylic"),
    "WD1F": ("flat end mill", 1, "Uncoated", "Acrylic"),
    # ── Aluminum ─────────────────────────────────────────────────────────────
    "AU2E": ("flat end mill", 2, "Uncoated", "Aluminum"),
    "AU2EL": ("flat end mill", 2, "Uncoated", "Aluminum"),
    "AU3E": ("flat end mill", 3, "Uncoated", "Aluminum"),
    "DAU3E": ("flat end mill", 3, "DLC", "Aluminum"),
    "AU3EL": ("flat end mill", 3, "Uncoated", "Aluminum"),
    "SA1F": ("flat end mill", 1, "Uncoated", "Aluminum"),
    "DSA1F": ("flat end mill", 1, "DLC", "Aluminum"),
    "DW1F": ("flat end mill", 1, "DLC", "Aluminum"),
    "M4E": ("flat end mill", 4, "TiAlN", "Aluminum"),
    # ── Steel ─────────────────────────────────────────────────────────────────
    "P4E": ("flat end mill", 4, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "P4EL": ("flat end mill", 4, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "P4C": ("flat end mill", 4, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "P4CL": ("flat end mill", 4, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "P4CFL": ("flat end mill", 4, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "T4E": ("flat end mill", 4, "TiAlXN",
            "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "T4EL": ("flat end mill", 4, "TiAlXN",
             "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "T2E": ("flat end mill", 2, "TiAlXN",
            "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "TX4E": ("flat end mill", 4, "TiAlN", "Stainless steel, Titanium alloy, Heat resistant alloy"),
    "TX4EL": ("flat end mill", 4, "TiAlN", "Stainless steel, Titanium alloy, Heat resistant alloy"),
    "ICT4F": ("radius mill", 4, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "IECP1F": ("flat end mill", 1, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "IFT2F": ("flat end mill", 2, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "BP2F": ("flat end mill", 2, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "IP2F": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, MDF, HDF, Plywood, Particle Board"),
    "IP3F": ("flat end mill", 3, "Uncoated", "Hardwood, Softwood, MDF, HDF, Plywood, Particle Board"),
    "IP4F": ("flat end mill", 4, "Uncoated", "Hardwood, Softwood, MDF, HDF, Plywood, Particle Board"),
    "IP4FC": ("flat end mill", 4, "Uncoated", "Hardwood, Softwood, MDF, HDF, Plywood, Particle Board"),
    "IPA": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, MDF, HDF, Plywood, Particle Board"),
    "IPB": ("flat end mill", 2, "Uncoated", "Hardwood, Softwood, MDF, HDF, Plywood, Particle Board"),
    "DCM": ("dovetail mill", 2, "Nano Coat", "Non-standard materials, Plastics, Composites"),
    "T2B": ("ball end mill", 2, "TiAlXN",
            "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "T2BL": ("ball end mill", 2, "TiAlXN",
             "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "T4B": ("ball end mill", 4, "TiAlXN",
            "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "T4BL": ("ball end mill", 4, "TiAlXN",
             "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "P2B": ("ball end mill", 2, "TiAlXN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "P2BA": ("ball end mill", 2, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "AP2B": ("ball end mill", 2, "TAC", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "P2BL": ("ball end mill", 2, "TiAlXN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "AP2BL": ("ball end mill", 2, "TAC", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "P2BC": ("tapered mill", 2, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "T2BC": ("tapered mill", 2, "HSi",
             "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "ECP3F": ("chamfer mill", 3, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "ECP2F": ("chamfer mill", 2, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "ECZ3F": ("chamfer mill", 3, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "ICRP2F": ("bull nose end mill", 2, "TiAlN", "Steel, Carbon steel, Pre-hardened steel, Cast iron, Stainless steel"),
    "T4R": ("bull nose end mill", 4, "TiAlXN",
            "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "T4RL": ("bull nose end mill", 4, "TiAlXN",
             "Carbon steel, Alloy steel, Prehardened steel 45HRC, Stainless steel, Titanium alloy, Heat resistant alloy"),
    "TX4R": ("bull nose end mill", 4, "TiAlN", "Stainless steel, Titanium alloy, Heat resistant alloy"),
    "TX4RL": ("bull nose end mill", 4, "TiAlXN", "Stainless steel, Titanium alloy, Heat resistant alloy"),
    # ── Titanium & other ─────────────────────────────────────────────────────
    "TT4E": ("flat end mill", 4, "AlCrZr", "Titanium, Superalloy, Stainless steel"),
    # ── NON-STANDARD: Flat-tipped Cutter ─────────────────────────────────────
    "FLATCUT": ("chamfer mill", 1, "TiAlN", "Non-Ferrous, PCB, Engraving, V-carving"),
    "AFLATCUT": ("chamfer mill", 1, "TAC", "Non-Ferrous, PCB, Engraving, V-carving"),
    # ── Thread End Mills ──────────────────────────────────────────────────────
    "TRS": ("thread mill", 2, "TiAlN",
            "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRT": ("thread mill", 3, "AlTiSiN",
            "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRTUNF": ("thread mill", 3, "TiAlN",
               "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRTUNC": ("thread mill", 3, "TiAlN",
               "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRZ": ("thread mill", 3, "TiAlN",
            "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRZUNC": ("thread mill", 4, "TiAlN",
               "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRZBSP": ("thread mill", 4, "TiAlN",
               "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRZNPT": ("thread mill", 4, "TiAlN",
               "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "TRZNPTF": ("thread mill", 4, "TiAlN",
                "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    "ISOTAT": ("thread mill", 3, "DLC",
               "Carbon steel, Alloy steel, Cast iron, Stainless steel, Prehardened steel, Hardened steel"),
    # ── Twist Drill Bits ──────────────────────────────────────────────────────
    "ETG": ("drill", 2, "TiAlN", "Hardened steel, High temperature alloy, Difficult-to-machine materials"),
    "STN": ("drill", 2, "Uncoated", "Aluminum, Aluminum alloy, Die cast aluminum"),
}

# Sanity check at import time: every hsm type string used above must be a
# real HSMToolType value (this is exactly the "bull nose" vs "bullnose"
# class of bug the raw-XML version was silently exposed to).
_VALID_HSM_TYPES = {t.value for t in HSMToolType}
_bad = {v[0] for v in SERIES_META.values() if v[0] not in _VALID_HSM_TYPES}
if _bad:
    raise ValueError(f"SERIES_META uses unknown HSMToolType value(s): {_bad}")


# ─── Helper functions (unchanged from the original PDF parser) ──────────────

def parse_float(s):
    if s is None:
        return None
    try:
        cleaned = re.sub(r'[^0-9.,+-]+', '', str(s).strip())
        return float(cleaned.replace(',', '.'))
    except ValueError:
        return None


def parse_range_mid(s):
    """Midpoint of a range '1-1.5'; returns single value immediately."""
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r'^([0-9.,]+)-([0-9.,]+)$', s)
    if m:
        lo = float(m.group(1).replace(',', '.'))
        hi = float(m.group(2).replace(',', '.'))
        return round((lo + hi) / 2, 4)
    try:
        return float(re.sub(r'[^0-9.,]', '', s).replace(',', '.'))
    except ValueError:
        return None


def parse_overall_cutting(s):
    """Parses 'Overall-Cutting' format like '50-8' -> (overall=50.0, cutting=8.0)."""
    if s is None:
        return None, None
    s = str(s).strip()
    m = re.match(r'^([0-9]+)-([0-9]+)$', s)
    if m:
        return float(m.group(1)), float(m.group(2))
    v = parse_float(s)
    return v, None


def split_cell(cell):
    if cell is None:
        return []
    return [v.strip() for v in str(cell).split('\n') if v.strip()]


def normalize_code(raw):
    """Returns (normalized_code, series_key) or (raw, None) when unknown."""
    raw = raw.strip()

    if raw.startswith('ISO TAT'):
        return raw, "ISOTAT"

    m = re.match(r'^(ETG|STN)\s+(.+)$', raw)
    if m:
        return raw, m.group(1)

    if re.match(r'^A[0-9]', raw):
        return raw, "AFLATCUT"

    if re.match(r'^[0-9]', raw):
        return raw, "FLATCUT"

    thread_map = [
        (r'^TRZ-NPTF', "TRZNPTF"),
        (r'^TRZ-NPT', "TRZNPT"),
        (r'^TRZ-BSP', "TRZBSP"),
        (r'^TRZ-UNC', "TRZUNC"),
        (r'^TRZ-UNF', "TRZUNC"),
        (r'^TRZ', "TRZ"),
        (r'^TRT-UNF', "TRTUNF"),
        (r'^TRT-UNC', "TRTUNF"),
        (r'^TRT', "TRT"),
        (r'^TRS', "TRS"),
    ]
    for pattern, key in thread_map:
        if re.match(pattern, raw):
            return raw, key

    series = raw.split('-')[0] if '-' in raw else raw
    if series in SERIES_META:
        return raw, series

    return raw, None


def detect_columns(header_row):
    cols = {}
    for i, cell in enumerate(header_row):
        if cell is None:
            continue
        c = str(cell).lower().replace('\n', ' ')

        if 'item code' in c:
            if 'tiac' in c or 'tialn' in c or 'tiain' in c:
                cols['item_code'] = i
            elif 'tac' in c:
                cols['item_code2'] = i
            elif 'item_code' not in cols:
                cols['item_code'] = i
            elif 'item_code2' not in cols:
                cols['item_code2'] = i

        if 'outside diameter' in c or ('d1' in c and 'dia' in c) or 'cutting dia' in c:
            if 'dia' not in cols:
                cols['dia'] = i

        if 'd2' in c:
            cols['d2'] = i

        if 'cutting radius' in c and 'r(' in c:
            cols['radius'] = i

        if ('l1' in c and ('cutting length' in c or 'flute' in c)) or 'l1(mm)' in c:
            cols['flute_len'] = i
        elif 'neck length' in c:
            cols['flute_len'] = i

        if ('l2' in c and ('cutting length' in c)) or 'l2(mm)' in c:
            cols['L2'] = i

        if ('shank' in c and 'dia' in c) or 'd(mm)' in c or 'shank diameter' in c:
            cols['shank_dia'] = i
        elif 'k dia o' in c:
            cols['shank_dia'] = i - 1
        if 'neck dia' in c or ('d2' in c and 'neck' in c):
            cols['neck_dia'] = i

        if ('overall' in c and 'length' in c and 'cutting' not in c) or "l(mm)" in c:
            cols['overall'] = i

        if 'overall length' in c and 'cutting length' in c:
            cols['overall_cutting_3d'] = i

        if 'corner' in c or ('radius' in c and 'ball' not in c and 'cutting' not in c):
            cols['corner_radius'] = i
        if 'ball radius' in c:
            cols['corner_radius'] = i

        if 'angle' in c or 'a(°)' in c:
            cols['angle'] = i

        if 'pitch' in c and 'size' in c:
            cols['pitch_size'] = i

        if c.strip() in ('flute', 'flute no.', 'flutes'):
            cols['flutes_col'] = i

    return cols


# ─── PDF-Parsing (unchanged logic; still returns raw dicts, one per code) ────

def extract_all_tools(pdf_path):
    tools = {}

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 4,
        "join_tolerance": 3,
        "edge_min_length": 10,
        "min_words_vertical": 2,
        "min_words_horizontal": 2,
        "intersection_tolerance": 3,
    }

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            if page.page_number == 20:
                new_settings = dict(table_settings)
                new_settings['snap_tolerance'] = 6
                tables = page.extract_tables(new_settings)
            elif page.page_number == 15:
                new_settings = dict(table_settings)
                new_settings['snap_tolerance'] = 6
                new_settings['join_tolerance'] = 4
                tables = page.extract_tables(new_settings)
            else:
                tables = page.extract_tables(table_settings)

            for table in tables:
                if not table or len(table) < 2:
                    continue

                header_idx = None
                for ri, row in enumerate(table):
                    flat = ' '.join(str(c) for c in row if c).lower()
                    if 'item code' in flat or 'outside diameter' in flat:
                        header_idx = ri
                        break
                if header_idx is None:
                    continue

                cols = detect_columns(table[header_idx])

                is_drill_table = (
                        'item_code' not in cols and
                        'dia' in cols and
                        any(
                            re.match(r'^(ETG|STN)\s', str(r[0] or ''))
                            for r in table[header_idx + 1: header_idx + 4]
                        )
                )
                if is_drill_table:
                    cols['item_code'] = 0

                if 'item_code' not in cols:
                    continue

                for row in table[header_idx + 1:]:
                    if not row or all(c is None or str(c).strip() == '' for c in row):
                        continue

                    if row[0] and str(row[0]).strip() in ('3D', '5D', ''):
                        first_nonempty = next((str(c).strip() for c in row if c and str(c).strip()), '')
                        if first_nonempty in ('3D', '5D'):
                            continue

                    ic_idx = cols['item_code']
                    ic2_idx = cols.get('item_code2')
                    code_cells = split_cell(row[ic_idx] if ic_idx < len(row) else None)
                    variants = []
                    if ic2_idx is not None and ic2_idx < len(row) and row[ic2_idx]:
                        var_raws = split_cell(row[ic2_idx])
                        for var in var_raws:
                            variants = expand_variants(var)

                    if len(variants) > 0:
                        code_cells = variants + code_cells

                    def get_col(key):
                        idx = cols.get(key)
                        if idx is None or idx >= len(row):
                            return []
                        return split_cell(row[idx])

                    dias = get_col('dia')
                    radii = get_col('radius')
                    flute_len = get_col('flute_len')
                    shank_dias = get_col('shank_dia')
                    overalls = get_col('overall')
                    corner_radii = get_col('corner_radius')
                    angles = get_col('angle')
                    neck_dias = get_col('neck_dia')
                    pitch_sizes = get_col('pitch_size')
                    flutes_vals = get_col('flutes_col')
                    overall_cut_3d = get_col('overall_cutting_3d')
                    flute_len2 = get_col('L2')
                    dia2 = get_col('d2')

                    for idx, raw_code in enumerate(code_cells):
                        raw_code = raw_code.strip()
                        normalized, series_key = normalize_code(raw_code)
                        if series_key is None or series_key not in SERIES_META:
                            continue

                        def pick(lst, i):
                            if lst and i < len(lst):
                                return parse_float(lst[i])
                            return parse_float(lst[0]) if lst else None

                        if normalized not in tools:
                            d1 = None
                            if series_key in ('ETG', 'STN'):
                                m = re.match(r'^(?:ETG|STN)\s+(.+)$', normalized)
                                if m:
                                    d1 = parse_range_mid(m.group(1))
                            else:
                                d1 = pick(dias, idx)
                            if d1 is None or d1 == 0:
                                r = pick(radii, idx)
                                if r:
                                    d1 = round(r * 2, 4)

                            shank_raw = pick(shank_dias, idx)
                            overall_val = None
                            flute_val = pick(flute_len, idx)
                            flute_length2 = pick(flute_len2, idx)
                            dia2 = pick(dia2, idx)

                            if series_key in ('ETG', 'STN'):
                                oc_raw = (overall_cut_3d[idx] if overall_cut_3d and idx < len(overall_cut_3d)
                                          else (overall_cut_3d[0] if overall_cut_3d else None))
                                if not oc_raw and overalls:
                                    oc_raw = overalls[idx] if idx < len(overalls) else (
                                        overalls[0] if overalls else None)
                                ov, cut = parse_overall_cutting(oc_raw)
                                overall_val = ov
                                flute_val = cut
                            else:
                                overall_val = pick(overalls, idx)

                            flute_count_raw = pick(flutes_vals, idx)
                            flute_count = int(flute_count_raw) if flute_count_raw else None

                            tool_type, flutes_nr, coating, material = SERIES_META[series_key]
                            description = normalized + " | suitable for " + material

                            tools[normalized] = {
                                'name': normalized,
                                'description': description,
                                'series_key': series_key,
                                'type': tool_type,
                                'material': "Ti coated" if "Ti" in coating else "Carbide",
                                'coating': coating,
                                'dia': d1,
                                'flute_len': flute_val,
                                'shank_dia': shank_raw,
                                'overall': overall_val,
                                'corner_radius': pick(corner_radii, idx),
                                'angle': pick(angles, idx),
                                'neck_dia': pick(neck_dias, idx),
                                'pitch_size': (pitch_sizes[idx] if pitch_sizes and idx < len(pitch_sizes)
                                               else (pitch_sizes[0] if pitch_sizes else None)),
                                'flute_count': flute_count if flute_count else flutes_nr,
                                'flute_len2': flute_length2,
                                'dia2': dia2,
                            }

    return list(tools.values())


# ─── raw dict -> Tool ────────────────────────────────────────────────────────

def raw_to_tool(raw: dict) -> Tool:
    """
    Converts one raw PDF-extracted dict (as produced by extract_all_tools())
    into a Tool dataclass instance, filling in the geometry fields the
    dataclass actually has. Missing values stay at the Tool defaults
    (0 / "carbide" / etc.) rather than None, since Tool fields are typed
    float/int/str, not Optional.

    Notes:
    - A missing flute_length for angle-only tools (engravers / chamfer-like
      profiles where the PDF only gives an included angle, no explicit flute
      length) is approximated as cos(angle/2) * shank_dia, mirroring the
      diagnostic estimate the original script only printed but never stored.
    - corner_radius from the PDF ('ball radius' / 'corner radius' column)
      maps directly to Tool.corner_radius; for tapered/tool angle profiles
      this may be 0 if the catalog only lists an included angle.
    """
    tool_type = raw['type']
    flute_dia = raw.get('dia') or 0.0
    shank_dia = raw.get('shank_dia') or flute_dia
    overall_length = raw.get('overall') or 0.0
    flute_length = raw.get('flute_len')
    angle = raw.get('angle') or 0.0
    corner_radius = raw.get('corner_radius') or 0.0
    nr_flutes = raw.get('flute_count') or 1

    if flute_length is None:
        if angle and shank_dia:
            flute_length = round(math.cos(math.radians(angle / 2.0)) * shank_dia, 4)
        else:
            flute_length = 0.0

    tool = Tool(
        name=raw.get('name'),
        type=tool_type,
        vendor="Dreanique",
        description=raw.get('description'),
        material=raw.get('material', ''),
        coating=raw.get('coating', 'None'),
        overall_length=overall_length,
        shank_dia=shank_dia,
        shoulder_length=flute_length,
        shoulder_dia=flute_dia,
        nr_flutes=nr_flutes,
        flute_length=flute_length,
        flute_dia=flute_dia,
        angle=angle,
        corner_radius=corner_radius,
        clockwise=True,
    )

    if tool.type == HSMToolType.THREAD_MILL.value:
        tool = raw_to_thread(raw, tool)

    if tool.type == HSMToolType.FLAT_END_MILL.value:
        tool = raw_to_flatend(raw, tool)

    if tool.type == HSMToolType.CHAMFER_MILL.value:
        tool = raw_to_chamfer(raw, tool)

    if tool.type == HSMToolType.RADIUS_MILL.value:
        tool = raw_to_radius_mill(raw, tool)

    if tool_type == HSMToolType.TAPERED_MILL.value:
        tool = raw_to_tapered(raw, tool)

    if tool_type == HSMToolType.DOVETAIL_MILL.value:
        tool = raw_to_dovetail(raw, tool)

    if tool_type == HSMToolType.DRILL.value:
        tool = raw_to_drill(raw, tool)

    return tool


def raw_to_thread(raw, tool) -> Tool:
    thread_pitch_mm = 0.0
    profile_angle = 60.0  # Tool-Default

    if raw.get('pitch_size'):
        pitch_mm, dia_mm, standard, profile_angle = parse_pitch_size_full(raw['pitch_size'])
        if pitch_mm is not None:
            thread_pitch_mm = pitch_mm

    tool.thread_profile_angle = profile_angle
    tool.thread_pitch = thread_pitch_mm

    if "TRS" in tool.description:
        # single tooth threadmill
        tool.thread_nr_teeth = 1
        tool.shoulder_length = tool.flute_length  # flute length set from L1 (neck length)
        tool.flute_length = tool.thread_pitch
        tool.shank_length = tool.overall_length - tool.shoulder_length - tool.flute_length
        tool.shoulder_dia = raw.get('neck_dia')

    if "TRT" in tool.description:
        tool.thread_nr_teeth = 3
        tool.shoulder_dia = raw.get('neck_dia')
        tool.shoulder_length = tool.flute_length  # flute length set from L1 (neck length)
        tool.flute_length = tool.thread_pitch * tool.thread_nr_teeth

    if "TAT" in tool.description:
        tool.thread_nr_teeth = 1  # essentially one teeth for the thread, the first is for boring

    return tool


def raw_to_chamfer(raw, tool) -> Tool:
    tool.shoulder_dia = raw.get('shank_dia')
    tool.flute_dia = raw.get('shank_dia')
    tool.shank_dia = raw.get('shank_dia')
    tool.angle = tool.angle / 2
    return tool


def raw_to_flatend(raw, tool) -> Tool:
    if "DW1F" in tool.description:
        if raw['flute_len2']:
            tool.flute_length = raw['flute_len2']

    if "ST3FK" in tool.description:
        # cluster fuck in catalog. switched dia and cutting length
        flute_length = tool.shank_dia
        tool.shank_dia = tool.flute_length
        tool.flute_length = flute_length

    # error in catalog
    if "AU2EL-D20.0" in tool.description:
        flute_dia = tool.shank_dia
        tool.shank_dia = tool.flute_dia
        tool.flute_dia = flute_dia

    return tool


def raw_to_bullnose(raw, tool) -> Tool:
    tool.corner_radius = raw.get('corner_radius')
    return tool


def raw_to_ballend(raw, tool) -> Tool:
    tool.corner_radius = raw.get('corner_radius')
    return tool


def raw_to_tapered(raw, tool) -> Tool:
    tool.corner_radius = raw.get('dia')  # really is the radius not diameter
    tool.tapered_type = 'tapered_ball'
    tool.flute_dia = raw.get('dia')
    return tool


def raw_to_drill(raw, tool) -> Tool:
    tool.tip_angle = 120
    return tool


def raw_to_radius_mill(raw, tool) -> Tool:
    tool.flute_length = tool.corner_radius * 2
    tool.shoulder_length = tool.flute_length
    tool.shank_length = tool.overall_length - tool.flute_length

    return tool


def raw_to_dovetail(raw, tool) -> Tool:
    tool.shoulder_dia = raw.get('dia2')
    tool.shoulder_length = raw.get('flute_len2')
    tool.flute_length = dovetail_flute_length(tool.flute_dia, tool.shoulder_dia, tool.angle, tool.flute_length)
    return tool


def tools_to_meta(raw_tools: list) -> list:
    """Converts a list of raw PDF dicts into a list of Tool objects."""
    return [raw_to_tool(t) for t in raw_tools]


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Dreanique PDF catalog -> Tool meta CSV/JSON")
    parser.add_argument("pdf_path", type=Path, help="Path to the Dreanique catalog PDF")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("."),
                        help="Output directory for the meta file(s) (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Write meta JSON only")
    parser.add_argument("--csv", action="store_true", help="Write meta CSV only")
    args = parser.parse_args()

    as_json = args.json or not args.csv
    as_csv = args.csv or not args.json

    print(f"📖 Reading PDF: {args.pdf_path}")
    raw_tools = extract_all_tools(args.pdf_path)
    raw_tools.sort(key=lambda t: (t['series_key'], t['dia'] or 0, t['name']))

    print(f"✅ {len(raw_tools)} Tools extracted from catalog.")
    series_count = Counter(t['series_key'] for t in raw_tools)
    print("\nTools per series:")
    for s, n in sorted(series_count.items()):
        print(f"  {s:12s}: {n}")

    angle_tools = [t for t in raw_tools if t.get('angle') is not None and t['flute_len'] is None]
    if angle_tools:
        print(f"\n🔺 {len(angle_tools)} angle-tools (flute_len approximated = cos(angle/2) * shank_dia):")
        for t in angle_tools[:4]:
            sd = t['shank_dia'] or 0
            if t['angle'] and sd:
                fl = round(math.cos(math.radians(t['angle'] / 2.0)) * sd, 4)
                print(f"    {t['name']:35s} angle={t['angle']}° → flute_len={fl}")
        if len(angle_tools) > 4:
            print(f"    ... and {len(angle_tools) - 4} of following")

    thread_tools = [t for t in raw_tools if SERIES_META[t['series_key']][0] == "thread mill"]
    drill_tools = [t for t in raw_tools if SERIES_META[t['series_key']][0] == "drill"]
    flat_tools = [t for t in raw_tools if t['series_key'] in ('FLATCUT', 'AFLATCUT')]
    print(f"\n🔩 {len(thread_tools)} Thread End Mills (ISO TAT, TRS, TRT, TRZ...)")
    print(f"🔨 {len(drill_tools)} Twist Drill Bits (ETG, STN)")
    print(f"🔪 {len(flat_tools)} Flat-tipped Cutter")

    tools = tools_to_meta(raw_tools)

    base_name = args.pdf_path.stem
    written = write_meta(tools, args.output_dir, base_name, as_json=as_json, as_csv=as_csv)

    print(f"\n💾 {len(written)} Meta-file written:")
    for p in written:
        print(f"    {p}")


if __name__ == '__main__':
    main()
