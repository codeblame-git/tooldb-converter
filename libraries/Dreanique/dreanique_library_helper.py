#!/usr/bin/env python3

"""
Dreanique Catalog specific helper functions

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

import re
from fractions import Fraction

# ANSI/ASME B1.1 numbered-screw-size major diameters (inches), used only to
# resolve a diameter when the source string uses 'NO.<n>' instead of a
# fractional or decimal inch value. Not needed for the pitch itself.
_NUMBERED_SCREW_MAJOR_DIA_IN = {
    0: 0.0600, 1: 0.0730, 2: 0.0860, 3: 0.0990, 4: 0.1120,
    5: 0.1250, 6: 0.1380, 8: 0.1640, 10: 0.1900, 12: 0.2160,
}

_INCH_PIPE_OR_UNIFIED_PREFIXES = r'BSPT|BSPP|BSP|NPTF|NPT|UNC|UNF|UNEF|UN'

# Thread profile (flank) angle in degrees, keyed by the 'standard' string
# returned from parse_pitch_size(). Only BSP-family threads deviate from
# the otherwise universal 60° angle.
PROFILE_ANGLE_BY_STANDARD = {
    "metric": 60.0,
    "metric_coarse_unspecified": 60.0,
    "unified_inch": 60.0,
    "unified_numbered": 60.0,
    "UNC": 60.0,
    "UNF": 60.0,
    "UNEF": 60.0,
    "UN": 60.0,
    "NPT": 60.0,
    "NPTF": 60.0,
    "BSP": 55.0,
    "BSPT": 55.0,
    "BSPP": 55.0,
    "unknown": 60.0,  # falls back to the Tool dataclass default
}


def parse_inch_diameter_to_mm(dia_raw):
    """
    Converts a raw inch diameter token ('1/16', '3/4', 'NO.1', '10', '.500')
    into millimeters. Returns None if the token can't be parsed.
    """
    if dia_raw is None:
        return None
    s = str(dia_raw).strip()

    m = re.match(r'^NO\.?\s*([0-9]+)$', s, re.IGNORECASE)
    if m:
        no = int(m.group(1))
        in_val = _NUMBERED_SCREW_MAJOR_DIA_IN.get(no)
        return round(in_val * 25.4, 4) if in_val is not None else None

    if '/' in s:
        try:
            return round(float(Fraction(s)) * 25.4, 4)
        except (ValueError, ZeroDivisionError):
            return None

    try:
        return round(float(s) * 25.4, 4)
    except ValueError:
        return None


def _normalize_pitch_string(raw):
    """
    Normalizes a raw 'Pitch Size' catalog cell before regex dispatch:
      - strips surrounding whitespace and a trailing ';' catalog separator
      - collapses typographic inch/quote marks (″, “, ”, ') to a plain
        ASCII '"', since PDF text extraction frequently emits these
        instead of the straight quote U+0022 (e.g. 'NPTF 1″-11.5' or
        'NPTF 1"-11.5' both must resolve to the same inch-diameter token)
    """
    if raw is None:
        return ""
    s = str(raw).strip().rstrip(';').strip()
    return s.replace('″', '"').replace('“', '"').replace('”', '"').replace("'", '"')


def parse_pitch_size(raw):
    s = _normalize_pitch_string(raw)
    if not s:
        return None, None, "unknown"

    # ── Metric: M<dia>*<pitch> / M<dia>x<pitch> / M<dia>-<pitch> ────────────
    m = re.match(r'^M\s*([0-9.,]+)\s*[*xX-]\s*([0-9.,]+)$', s)
    if m:
        dia_mm = float(m.group(1).replace(',', '.'))
        pitch_mm = float(m.group(2).replace(',', '.'))
        return pitch_mm, dia_mm, "metric"

    m = re.match(r'^M\s*([0-9.,]+)$', s)
    if m:
        return None, float(m.group(1).replace(',', '.')), "metric_coarse_unspecified"

    # ── Inch pipe / unified threads with explicit standard prefix ──────────
    m = re.match(
        rf'^({_INCH_PIPE_OR_UNIFIED_PREFIXES})\s+([0-9/.\"]+)\s*-\s*([0-9.,]+)$',
        s, re.IGNORECASE,
    )
    if m:
        standard = m.group(1).upper()
        dia_raw = m.group(2).replace('"', '')
        tpi = float(m.group(3).replace(',', '.'))
        pitch_mm = round(25.4 / tpi, 4) if tpi else None
        return pitch_mm, parse_inch_diameter_to_mm(dia_raw), standard

    # ── Plain fractional/decimal inch thread, no standard prefix ───────────
    m = re.match(r'^([0-9/.\"]+)\s*-\s*([0-9.,]+)$', s)
    if m:
        dia_raw = m.group(1).replace('"', '')
        tpi = float(m.group(2).replace(',', '.'))
        pitch_mm = round(25.4 / tpi, 4) if tpi else None
        return pitch_mm, parse_inch_diameter_to_mm(dia_raw), "unified_inch"

    # ── Numbered screw sizes: 'NO.1-72', 'No.10-32' ─────────────────────────
    m = re.match(r'^NO\.?\s*([0-9]+)\s*-\s*([0-9.,]+)$', s, re.IGNORECASE)
    if m:
        screw_no = m.group(1)
        tpi = float(m.group(2).replace(',', '.'))
        pitch_mm = round(25.4 / tpi, 4) if tpi else None
        return pitch_mm, parse_inch_diameter_to_mm(f"NO.{screw_no}"), "unified_numbered"

    return None, None, "unknown"


def parse_pitch_size_full(raw):
    """
    Like parse_pitch_size(), but also resolves the thread profile (flank)
    angle for the detected standard, so callers get everything needed to
    populate Tool.thread_pitch AND Tool.thread_profile_angle correctly in
    one call.

    Returns (pitch_mm, thread_dia_mm, standard, profile_angle_deg).
    profile_angle_deg is 55.0 for BSP/BSPT/BSPP (Whitworth form) and 60.0
    for every other recognized standard (NPT, NPTF, UN, UNC, UNF, UNEF,
    metric) — this is the one place where BSP threads are NOT just a table
    lookup difference from NPT/UN, but a genuinely different thread
    geometry, so it must not be left at the Tool default of 60.
    """
    pitch_mm, dia_mm, standard = parse_pitch_size(raw)
    profile_angle = PROFILE_ANGLE_BY_STANDARD.get(standard, 60.0)
    return pitch_mm, dia_mm, standard, profile_angle


def expand_variants(s: str):
    parts = s.split('/')
    reference = parts[-1]
    others = parts[:-1]

    ref_segments = reference.split('-')
    ref_code = ref_segments[0]
    fixed_suffix = '-' + '-'.join(ref_segments[1:]) if len(ref_segments) > 1 else ''

    results = []
    for o in others:
        o_code = o.split('-')[0]
        replaced_len = len(o_code)
        new_code = o_code + ref_code[replaced_len:]
        results.append(new_code + fixed_suffix)

    results.append(ref_code + fixed_suffix)
    return results
