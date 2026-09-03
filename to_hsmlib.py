#!/usr/bin/env python3
"""
to_hsmlib.py

Converts to hsmlib format.

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
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

from helper import *


# ─── Helpers ────────────────────────────────────────────────────────────────
def map_coolant(csv_coolant):
    """Map SolidWorks 'Coolant Type' to hsmlib coolant mode."""
    c = (csv_coolant or '').lower()
    if 'flood' in c or 'on' in c or 'yes' in c:
        return 'flood'
    if 'mist' in c:
        return 'mist'
    if 'through' in c:
        return 'through'
    return 'disabled'


def map_material(csv_material):
    """Map SolidWorks 'Tool Material' to hsmlib material name."""
    m = (csv_material or '').lower()
    if 'carbide' in m or 'hardmetal' in m or 'hartmetall' in m:
        return 'carbide'
    if 'hss' in m:
        return 'hss'
    if 'diamond' in m:
        return 'diamond'
    return 'carbide'  # default


def normalize_tool_unit(unit: str | None) -> str:
    """
    Returns either 'inches' or 'millimeter'.

    Tool.unit is expected to originate from solidworks unit field
    """
    normalized = (unit or "millimeters").strip().lower()

    if normalized in ("inch", "inches", "in"):
        return "inches"
    else:  # metric -> millimeters
        return "millimeters"


# ─── SW CSV -> hsmlib ─────────────────────────────────────────────────────────
# ─── Summary of all constant / derived values discovered, for reference ─────
#
# Tool type        | Field                  | Behavior
# -----------------|------------------------|------------------------------------------
# CornerRounding   | Output                 | constant "Tip"
# CornerRounding   | Shank Length (L6)      | constant "1" (placeholder, not geometry)
# CornerRounding   | Shoulder Dia (D4)      | always == End Dia. (D1)
# Dovetail         | Shank Length (L6)      | constant "1"
# Dovetail         | Shoulder Length (L4)   | constant "10"
# Dovetail         | Shoulder Dia (D4)      | always == Diameter (D1)
# Keyway           | Shank Length (L6)      | constant "1"
# Keyway           | Shoulder Length (L4)   | constant "10"
# Keyway           | Shoulder Dia (D4)      | always == Diameter (D1)
# Lollipop         | Shoulder Length (L4)   | derived: R + sqrt(R^2 - r_shank^2)
# Lollipop         | Shank Length (L6)      | identical to Shoulder Length (L4)
# ThreadMillSinglePt | Shank Length (L6)    | constant "1"
# ThreadMillMultiPt  | Shank Length (L6)    | approx. == Flute Length (L2)

def _parse_common_csv_fields(entry, tool_type, columns):
    """Read type-dependent common fields using only indexes from columns."""
    indices = {
        SWToolType.FLAT_END_MILL: (28, 11, 10, 15, 12, 16, 17, 18, 19, 20, 30),
        SWToolType.BALL_NOSE_MILL: (28, 11, 10, 15, 12, 16, 17, 18, 19, 20, 30),
        SWToolType.HOG_NOSE_MILL: (28, 11, 10, 15, 12, 16, 17, 18, 19, 20, 30),
        SWToolType.COUNTERSINK: (23, 9, 8, 14, 10, 15, 16, None, None, None, 25),
        SWToolType.CORNER_ROUNDING: (28, 12, 11, 15, 13, 16, 17, 18, 19, 20, 30),
        SWToolType.DOVETAIL: (25, 10, 9, 12, 11, 13, 14, 15, 16, 17, 28),
        SWToolType.KEYWAY: (26, 11, 10, 13, 12, 14, 15, 16, 17, 18, 29),
        SWToolType.LOLLIPOP: (24, 11, 10, 12, 8, 13, 14, 15, 16, 17, 26),
        SWToolType.THREAD_MULTI: (28, 12, 11, 16, 13, 17, 18, 19, 20, 21, 31),
        SWToolType.THREAD_SINGLE: (25, 10, 9, 13, 11, 14, 15, 16, 17, 18, 28),
        SWToolType.DRILLS: (28, 11, 10, 16, 12, 17, 18, 19, 20, 21, 30),
        SWToolType.CENTER_DRILL: (23, 12, 11, 14, 13, 15, 16, None, None, None, 26),
        SWToolType.FACE_MILL: (27, 13, 12, 14, 9, 15, 16, 17, 18, 19, None),
        SWToolType.BORES: (24, 11, 9, 15, 12, 16, 17, None, None, None, 26),
        SWToolType.TAPER_FLATEND: (28, 11, 9, 15, 12, 16, 17, 18, 19, 20, 30),
        SWToolType.TAPER_BALLNOSE: (28, 11, 9, 15, 12, 16, 17, 18, 19, 20, 30),
        SWToolType.TAPER_HOG_NOSE: (28, 11, 9, 15, 12, 16, 17, 18, 19, 20, 30),
        SWToolType.TAPS_RH: (34, 11, 10, 21, 13, 22, 23, 24, 25, 26, 40),
        SWToolType.TAPS_LH: (34, 11, 10, 21, 13, 22, 23, 24, 25, 26, 40),
    }

    try:
        vendor_i, comment_i, material_i, coolant_i, protrusion_i, spindle_i, feed_z_i, feed_xy_i, feed_in_i, feed_out_i, hand_i = \
            indices[tool_type]
    except KeyError as exc:
        raise ValueError(f"No common-field index map for {tool_type.value}") from exc

    def value(index, default=""):
        return default if index is None else entry[columns[index]]

    hand = value(hand_i, "Right hand")
    return {
        "vendor": value(vendor_i),
        "description": value(comment_i),
        "material": map_material(value(material_i)),
        "coolant_type": value(coolant_i),
        "protrusion": toFloat(value(protrusion_i)),
        "spindle": toFloat(value(spindle_i)),
        "feed_z": toFloat(value(feed_z_i)),
        "feed_xy": toFloat(value(feed_xy_i)),
        "feed_in": toFloat(value(feed_in_i)),
        "feed_out": toFloat(value(feed_out_i)),
        "clockwise": hand == "Right hand",
    }


def parse_csv_as_dicts(csv_path):
    """
    Reads a CSV file where:
    - Lines 1–8 are ignored
    - Line 9 is used as the header (column names)
    - From line 10 onward, data is returned as a list of dictionaries

    Returns: List[Dict[str, str]], ToolType
    """
    csv_path = Path(csv_path)

    with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
        # Read all lines
        all_lines = list(csv.reader(f))

    # Line 9 is the header (index 8, since 0-based)
    if len(all_lines) < 9:
        raise ValueError("CSV file has fewer than 9 lines.")

    header = all_lines[8]  # Line 9
    data_rows = all_lines[9:]  # From line 10 onward

    # Convert to dictionaries
    result = []
    for row in data_rows:
        # Skip empty lines
        if not row or all(c.strip() == '' for c in row):
            continue
        row_dict = dict(zip(header, row))
        row_dict['Unit'] = all_lines[2][2]
        result.append(row_dict)

    return result, get_tool_type(all_lines, result)


def parse_solidworks_csv(path):
    parsed_data, tool_type = parse_csv_as_dicts(path)
    tools = []

    for entry in parsed_data:
        # get hsm lib string for tooltype
        hsm_tooltype = convert_sw_to_hsm(tool_type)

        tool = Tool(type=hsm_tooltype.value, vendor=entry['Vendor'],
                    description=entry['Comment'],
                    name=entry.get('Tool ID', ''),
                    material=entry['Tool Material'].lower(),
                    protrusion=toFloat(entry['Protrusion   (L3)']),
                    spindle=toFloat(entry['Spindle_Speed']), feed_z=toFloat(entry['Z_Feedrate']),
                    unit=normalize_tool_unit(entry.get('Unit', 'millimeters')),
                    )

        if tool_type != SWToolType.TAPS_LH and tool_type != SWToolType.TAPS_RH:
            tool = replace(tool, coolant_type=entry['Coolant Type'],
                           shoulder_dia=toFloat(entry['Shoulder Dia (D4)']))
        else:
            tool = replace(tool, coolant_type=entry['CoolantType'],
                           shoulder_dia=toFloat(entry['ShoulderDia']))

        if 'XY_Feedrate' in entry:
            tool.feed_xy = entry['XY_Feedrate']
        if "Leadin_Feedrate" in entry:
            tool.feed_in = entry['Leadin_Feedrate']
        if "Leadout_Feedrate" in entry:
            tool.feed_out = entry['Leadout_Feedrate']

        if tool_type == SWToolType.FACE_MILL:
            tool = replace(tool, shank_dia=toFloat(entry['Shank Dia.  (D2)']),
                           flute_dia=toFloat(entry[' Diameter  (D1)']),
                           flute_length=toFloat(entry["Flute Length (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry[" No. Of Inserts"]),
                           shoulder_length=toFloat(entry["Shoulder Length (L4)"]),
                           angle=0.0, corner_radius=0.0,
                           clockwise=True if entry["Hand Of Cut"] == "Right hand" else False
                           , shank_length=toFloat(entry['Shank Length (L6)']))

        if tool_type == SWToolType.FLAT_END_MILL:
            tool = replace(tool, shank_dia=toFloat(entry['Shank Dia.  (D2)']),
                           flute_dia=toFloat(entry['Diameter  (D1)']),
                           flute_length=toFloat(entry["Flute Length (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]),
                           shoulder_length=toFloat(entry["Shoulder Length (L4)"]),
                           angle=0.0, corner_radius=0.0,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False
                           , shank_length=toFloat(entry['Shank Length (L6)']))
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia))

        if tool_type == SWToolType.BALL_NOSE_MILL or tool_type == SWToolType.HOG_NOSE_MILL:
            tool = replace(tool, shank_dia=toFloat(entry['Shank Dia.  (D2)']),
                           flute_dia=toFloat(entry['Diameter  (D1)']),
                           flute_length=toFloat(entry["Flute Length (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]),
                           shoulder_length=toFloat(entry["Shoulder Length (L4)"]),
                           angle=0.0, corner_radius=toFloat(entry[" End Radius   (R)"]),
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           shank_length=toFloat(entry['Shank Length (L6)']))
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia))

        if tool_type == SWToolType.COUNTERSINK:
            tool = replace(tool, shank_dia=toFloat(entry["ShankDia"]), flute_dia=toFloat(entry['Diameter (D1)']),
                           flute_length=calc_tip_length(toFloat(entry['Diameter (D1)']),
                                                        toFloat(entry["C\"Sink Angle (A)"]) / 2),
                           overall_length=toFloat(entry["Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]),
                           shoulder_length=toFloat(entry["Shoulder Length (L4)"]),
                           corner_radius=0, angle=toFloat(entry["C\"Sink Angle (A)"]) / 2,
                           tip_dia=toFloat(entry["EndDia"]),
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           shank_length=toFloat(entry['Shank Length (L6)']))

        if tool_type == SWToolType.TAPER_BALLNOSE:
            tool = replace(tool, flute_dia=toFloat(entry["End Dia. (D1)"]),
                           corner_radius=toFloat(entry[" End Radius   (R)"]), angle=toFloat(entry["Taper Angle (A)"]),
                           flute_length=toFloat(entry["Flute Length  (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]), shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                           shoulder_length=toFloat(entry["Flute Length  (L2)"]),
                           tapered_type="tapered_ball",
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           shank_length=toFloat(entry['Shank Length (L6)']),
                           shoulder_dia=toFloat(entry["Shank Dia.  (D2)"]))

        if tool_type == SWToolType.TAPER_FLATEND:
            tool = replace(tool, flute_dia=toFloat(entry["End Dia. (D1)"]), corner_radius=toFloat(entry["EndRadius"]),
                           angle=toFloat(entry["Taper Angle (A)"]),
                           flute_length=toFloat(entry["Flute Length  (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]), shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                           shoulder_length=toFloat(entry["Flute Length  (L2)"]),
                           tapered_type='tapered_bullnose',
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           shank_length=toFloat(entry['Shank Length (L6)']),
                           shoulder_dia=toFloat(entry["Shank Dia.  (D2)"]))

        if tool_type == SWToolType.TAPER_HOG_NOSE:
            tool = replace(tool, flute_dia=toFloat(entry["End Dia. (D1)"]),
                           corner_radius=toFloat(entry[" End Radius   (R)"]),
                           angle=toFloat(entry["Taper Angle (A)"]),
                           flute_length=toFloat(entry["Flute Length  (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]), shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                           shoulder_length=toFloat(entry["Flute Length  (L2)"]), tapered_type="tapered_bullnose",
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           shank_length=toFloat(entry['Shank Length (L6)']),
                           shoulder_dia=toFloat(entry["Shank Dia.  (D2)"])
                           )
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia))

        if tool_type == SWToolType.DRILLS:
            tool = replace(tool, flute_dia=toFloat(entry["Diameter (D1)"]),
                           flute_length=toFloat(entry["Flute Length (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]), tip_angle=toFloat(entry[" Tip  Angle (A)"]),
                           shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                           shoulder_length=toFloat(entry["Shoulder Length (L4)"]),
                           angle=toFloat(entry[" Tip  Angle (A)"]),
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False)
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.shoulder_length, 0.0, tool.shank_dia))

        if tool_type == SWToolType.THREAD_SINGLE:
            thread_dia = toFloat(entry["Dia. (D1)"])
            flute_length = toFloat(entry["Flute Length (L2)"])
            overall_length = toFloat(entry["Overall Length (L1)"])
            profile_angle = toFloat(entry["Thread Pitch Angle"], 60.0)

            # A SolidWorks SinglePt CSV has no explicit pitch column. Its small
            # "Flute Length (L2)" is the one-form cutting width and is the best
            # available pitch proxy in the current source format.
            thread_pitch = flute_length
            shoulder_length = clamp_body_length(
                threadmill_shoulder_length(overall_length, thread_dia),
                overall_length,
            )
            shoulder_dia = threadmill_shoulder_dia(
                thread_dia, thread_pitch, profile_angle,
            )

            tool = replace(tool,
                           flute_dia=thread_dia,
                           flute_length=flute_length,
                           overall_length=overall_length,
                           nr_flutes=int(entry["No. Of Flutes"]),
                           shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                           shoulder_length=shoulder_length,
                           shoulder_dia=shoulder_dia,
                           thread_pitch=thread_pitch,
                           thread_profile_angle=profile_angle,
                           thread_nr_teeth=1,
                           angle=0.0,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           shank_length=toFloat(entry['Shank Length (L6)']))

        if tool_type == SWToolType.THREAD_MULTI:
            thread_dia = toFloat(entry["Dia. (D1)"])
            flute_length = toFloat(entry["Flute Length (L2)"])
            overall_length = toFloat(entry["Overall Length (L1)"])
            thread_pitch = toFloat(entry["Pitch (P)"])
            profile_angle = toFloat(entry["Thread Pitch Angle"], 60.0)

            shoulder_dia = threadmill_shoulder_dia(
                thread_dia, thread_pitch, profile_angle,
            )

            shoulder_length = clamp_body_length(
                threadmill_shoulder_length(overall_length, thread_dia),
                overall_length,
            )
            tooth_count = threadmill_tooth_count_from_flute_length(
                flute_length, thread_pitch,
            )

            tool = replace(tool,
                           flute_dia=thread_dia,
                           flute_length=flute_length,
                           overall_length=overall_length,
                           nr_flutes=int(entry["No. Of Flutes"]),
                           shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                           shoulder_length=shoulder_length,
                           # Multi-point mills retain the thread diameter as their
                           # shoulder diameter unless a dedicated neck diameter is
                           # available in the source CSV. Unlike single-point mills,
                           # their axial multi-form profile does not imply a single
                           # V-notch neck reduction at this location.
                           # At least for threadmills with more than a few teeth
                           shoulder_dia=thread_dia if tooth_count > 5 else shoulder_dia,
                           thread_pitch=thread_pitch,
                           thread_profile_angle=profile_angle,
                           thread_nr_teeth=tooth_count,
                           angle=0.0,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           shank_length=toFloat(entry['Shank Length (L6)']))

        if tool_type == SWToolType.CORNER_ROUNDING:
            tool = replace(tool, flute_dia=toFloat(entry["End Dia.(D1)"]),
                           corner_radius=toFloat(entry["Radius (R1)"]),
                           flute_length=toFloat(entry["Flute Length (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]), shank_dia=toFloat(entry["Shank Dia."]),
                           shoulder_length=toFloat(entry["Body Length (L5)"]),
                           shoulder_dia=toFloat(entry["End Dia.(D1)"]),
                           angle=0.0,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False)
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia))

        if tool_type == SWToolType.DOVETAIL:
            d1 = toFloat(entry["Diameter  (D1)"])
            shank_dia = toFloat(entry["Shank Dia.  (D2)"])
            tip_angle = toFloat(entry[" Tip  Angle (A)"])

            if d1 > shank_dia and tip_angle > 0:
                flute_length = calc_tip_length(d1 - shank_dia, tip_angle)
            elif "Flute Length (L2)" in entry:
                flute_length = toFloat(entry["Flute Length (L2)"])
            else:
                flute_length = 0.0

            tool = replace(tool, flute_dia=d1,
                           corner_radius=toFloat(entry["Radius (R)"]), angle=toFloat(entry[" Tip  Angle (A)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]), shank_dia=shank_dia,
                           shoulder_dia=shank_dia,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False,
                           flute_length=flute_length)
            tool = replace(tool, shoulder_length=toFloat(entry["Shoulder Length (L4)"]))
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia))

        if tool_type == SWToolType.KEYWAY:
            tool = replace(tool, flute_dia=toFloat(entry["Diameter  (D1)"]),
                           corner_radius=toFloat(entry["Bottom Radius (R1)"]),
                           flute_length=toFloat(entry["Flute Length (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]), shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                           shoulder_dia=toFloat(entry["Shank Dia.  (D2)"]), angle=0.0,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False)
            tool = replace(tool, shoulder_length=0.0)
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia))

        if tool_type == SWToolType.LOLLIPOP:
            diameter = toFloat(entry["Diameter (D1)"])
            shank_dia = toFloat(entry["Shank Dia.  (D2)"])
            shoulder_len = lollipop_shoulder_length(diameter, shank_dia)
            tool = replace(tool,
                           flute_dia=diameter,
                           flute_length=toFloat(entry["Flute Length (L2)"]),
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]),
                           shank_dia=shank_dia,
                           shoulder_length=shoulder_len,
                           shoulder_dia=lollipop_shoulder_dia(diameter, shank_dia),
                           angle=0.0,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False)
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia),
                           corner_radius=tool.flute_dia / 2)

        if tool_type == SWToolType.TAPS_RH:
            tool = replace(
                tool,
                flute_dia=toFloat(entry["Major Diameter (D1)"]),
                flute_length=toFloat(entry["Flute Length (L2)"]),
                overall_length=toFloat(entry["Overall Length (L1)"]),
                shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                thread_pitch=toFloat(entry["Thread Pitch"]),
                thread_profile_angle=60.0,
                shoulder_dia=toFloat(entry["Major Diameter (D1)"]),
                clockwise=True,
                angle=0.0,
            )

            tool = replace(
                tool,
                shoulder_length=tap_shoulder_length(tool.overall_length),
                shank_length=0.0,
            )

        if tool_type == SWToolType.TAPS_LH:
            tool = replace(
                tool,
                flute_dia=toFloat(entry["Major Diameter (D1)"]),
                flute_length=toFloat(entry["Flute Length (L2)"]),
                overall_length=toFloat(entry["Overall Length (L1)"]),
                shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
                thread_pitch=toFloat(entry["Thread Pitch"]),
                thread_profile_angle=60.0,
                shoulder_dia=toFloat(entry["Major Diameter (D1)"]),
                clockwise=False,
                angle=0.0,
            )

            tool = replace(
                tool,
                shoulder_length=tap_shoulder_length(tool.overall_length),
                shank_length=0.0,
            )

        if tool_type == SWToolType.REAMERS:
            tool = replace(
                tool,
                flute_dia=toFloat(entry["Max. Cut Dia. (D1)"]),
                flute_length=toFloat(entry["Flute Length (L2)"]),
                overall_length=toFloat(entry["Overall Length (L1)"]),
                nr_flutes=int(entry["No. Of Flutes"]),
                shoulder_length=toFloat(entry["Protrusion   (L3)"]),  # == body length in hsm
                shank_dia=toFloat(entry["Shank Dia.  (D2)"]),
            )

        if tool_type == SWToolType.CORNER_ROUNDING:
            corner_radius = toFloat(entry["Radius (R1)"])
            flute_length = toFloat(entry["Flute Length (L2)"])
            # SolidWorks only stores the combined axial cutting length. Recover
            # the flat-tip portion (Harvey-style) as the excess over the pure
            # quarter-circle arc (Sandvik-style, tip_length == 0).
            tip_length = max(0.0, flute_length - corner_radius)

            tool = replace(tool,
                           flute_dia=toFloat(entry["End Dia.(D1)"]),
                           corner_radius=corner_radius,
                           flute_length=flute_length,
                           tip_length=tip_length,
                           overall_length=toFloat(entry["Overall Length (L1)"]),
                           nr_flutes=int(entry["No. Of Flutes"]),
                           shoulder_length=flute_length,
                           shoulder_dia=toFloat(entry["End Dia.(D1)"]),
                           angle=0.0,
                           clockwise=True if entry["HandOfCutID"] == "Right hand" else False)
            tool = replace(tool, shank_length=shank_length_from_body_length(
                tool.overall_length, tool.flute_length, tool.shoulder_length, tool.shank_dia),
                           shank_dia=tool.corner_radius * 2 + tool.flute_dia,
                           )

        if not tool.name and tool.description:
            tool.name = tool.description

        tools.append(tool)
    return tools


# ─── hsmlib writer  ───────────────────────────────────────

def add_expr(parent, key, value, unit=''):
    e = ET.SubElement(parent, 'expression')
    e.set('parameterKey', key)
    e.set('value', f"{xml_escape_attr(value)}{unit}")


def add_param(parent, key, value, unit=''):
    p = ET.SubElement(parent, 'parameter')
    p.set('key', key)
    p.set('value', f"{xml_escape_attr(value)}{unit}")


def tool_to_hsmlib_entry(root, tool):
    tool_entry = ET.SubElement(root, 'tool')
    tool_entry.set('guid', make_guid())
    tool_entry.set('type', tool.type)
    tool_entry.set('unit', tool.unit)
    tool_entry.set('version', '1.5')
    #
    ET.SubElement(tool_entry, 'description').text = xml_text(tool.description)
    ET.SubElement(tool_entry, 'manufacturer').text = xml_text(tool.vendor)
    ET.SubElement(tool_entry, 'product-id').text = xml_text(tool.name)
    ET.SubElement(tool_entry, 'product-link').text = xml_text(tool.product_link)
    #
    expressions = ET.SubElement(tool_entry, 'expressions')
    add_expr(expressions, 'tool_coating', tool.coating)
    add_expr(expressions, 'tool_diameter', toStr(tool.flute_dia), 'mm')
    add_expr(expressions, 'tool_fluteLength', toStr(tool.flute_length), 'mm')
    add_expr(expressions, 'tool_overallLength', toStr(tool.overall_length), 'mm')
    add_expr(expressions, 'tool_numberOfFlutes', toStr(tool.nr_flutes))
    add_expr(expressions, 'tool_shaftDiameter', toStr(tool.shank_dia), 'mm')
    add_expr(expressions, 'tool_shoulderLength', toStr(tool.shoulder_length), 'mm')

    if tool.corner_radius:
        add_expr(expressions, 'tool_cornerRadius', toStr(tool.corner_radius), 'mm')
    if tool.type == "chamfer mill":
        add_expr(expressions, 'tool_tipDiameter', toStr(tool.tip_dia), 'mm')
    if tool.angle:
        add_expr(expressions, 'tool_taperedAngle', toStr(tool.angle), 'deg')

    # ─── body ───────────────────────────────────
    # fix missing shank-length
    if not tool.shank_length:
        useable_length = tool.flute_length + tool.shoulder_length if tool.shoulder_length != tool.flute_length else tool.flute_length
        tool.shank_length = tool.overall_length - useable_length
    shaft_sections, body_length = build_shaft_and_body_length(tool)

    body = ET.SubElement(tool_entry, 'body')
    body.set('assembly-gauge-length', toStr(tool.overall_length))  # is dependent on holder and not tool geometry

    body_length = clamp_body_length(body_length, tool.overall_length)
    body.set('body-length', toStr(body_length))

    body.set('coolant-support', 'no')
    body.set('diameter', toStr(tool.flute_dia))
    body.set('flute-length', toStr(tool.flute_length))
    body.set('number-of-flutes', str(tool.nr_flutes))
    body.set('overall-length', toStr(tool.overall_length))
    body.set('shaft-diameter', toStr(tool.shank_dia))
    body.set('shoulder-length', toStr(tool.shoulder_length))
    body.set('thread-pitch', toStr(tool.thread_pitch))
    body.set('thread-profile-angle', toStr(tool.thread_profile_angle))

    if tool.type != HSMToolType.TAPERED_MILL.value:
        body.set('shoulder-diameter', toStr(tool.shoulder_dia))

    if tool.type == HSMToolType.REAMER.value:
        # body-length = shoulder length
        body.set('body-length', toStr(tool.shoulder_length))

    if tool.type == HSMToolType.LOLLIPOP_MILL:
        body.set('corner-radius', toStr(tool.corner_radius))

    if tool.type == HSMToolType.THREAD_MILL.value:
        body.set('number-of-teeth', toStr(tool.thread_nr_teeth))
        body_length = clamp_body_length(tool.shoulder_length + 2, tool.overall_length)  # show bit of shaft
        body.set('body-length', toStr(body_length))
        body.set('shoulder-length', toStr(tool.shoulder_length))

        teeth = tool.thread_nr_teeth
        if teeth <= 0:
            teeth = threadmill_tooth_count_from_flute_length(
                tool.flute_length, tool.thread_pitch)
        body.set('number-of-teeth', str(teeth))

    body.set('taper-angle', toStr(tool.angle))
    if tool.corner_radius:
        body.set('corner-radius', toStr(tool.corner_radius))
    if tool.type == HSMToolType.CHAMFER_MILL.value:
        body.set('tip-diameter', toStr(tool.tip_dia))

    if tool.type == HSMToolType.TAPERED_MILL.value:
        body.set('taper-angle', toStr(tool.angle))
        body.set('tapered-type', tool.tapered_type)
    if tool.type == HSMToolType.DRILL.value:
        body.set('taper-angle', toStr(tool.tip_angle))  # overwrite

    is_tap = tool.type in (
        HSMToolType.RIGHT_HAND_TAP.value,
        HSMToolType.LEFT_HAND_TAP.value,
    )

    if is_tap:
        body.set("body-length", toStr(tool.shoulder_length))
        body.set("shoulder-length", toStr(tool.shoulder_length))

    # ─── shaft ───────────────────────────────────
    if tool.type not in CUSTOM_PROFILE_HSM_TYPES:
        shaft = ET.SubElement(tool_entry, 'shaft')
        for diameter, length in shaft_sections:
            section = ET.SubElement(shaft, 'section')
            section.set('diameter', toStr(diameter))
            section.set('length', toStr(length))

    # ─── nc, coolant, material (required) ───────────────────────────────────
    nc = ET.SubElement(tool_entry, 'nc')
    nc.set('break-control', '0')
    nc.set('diameter-offset', '1')
    nc.set('length-offset', '1')
    nc.set('live-tool', '1')
    nc.set('manual-tool-change', '0')
    nc.set('number', '1')
    nc.set('turret', '0')
    #
    coolant_mode = map_coolant(tool.coolant_type)
    coolant = ET.SubElement(tool_entry, 'coolant')
    coolant.set('mode', coolant_mode)

    material_el = ET.SubElement(tool_entry, 'material')
    material_el.set('name', tool.material)
    #
    # ─── motion, presets (optional but common) ─────────────────────────────
    motion = ET.SubElement(tool_entry, 'motion')
    motion.set('spindle-rpm', toStr(tool.spindle))
    motion.set('cutting-feedrate', toStr(tool.feed_xy))
    motion.set('plunge-feedrate', toStr(tool.feed_z))
    motion.set('entry-feedrate', toStr(tool.feed_in))
    motion.set('exit-feedrate', toStr(tool.feed_out))
    motion.set('clockwise', "yes" if tool.clockwise else "no")

    presets = ET.SubElement(tool_entry, 'presets')
    preset = ET.SubElement(presets, 'preset')
    preset.set('name', tool.preset_name)
    add_param(preset, 'tool_spindleSpeed', str(int(tool.spindle)))
    add_param(preset, 'tool_feedCutting', toStr(tool.feed_xy))
    add_param(preset, 'tool_feedPlunge', toStr(tool.feed_z))
    add_param(preset, 'tool_feedEntry', toStr(tool.feed_in))
    add_param(preset, 'tool_feedExit', toStr(tool.feed_out))


def write_hsmlib(tools, output_path):
    """
    Writes a hsmlib file
    - XML-Header + Stylesheet
    - tool-library Root-Element
    - per tool: description, manufacturer, product-link, expressions, body, nc, coolant, material
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        '<?xml version="1.0" encoding="UTF-16" standalone="no" ?>\n'
        '<?xml-stylesheet type=\'text/xsl\' href=\'tool-library.xsl\'?>\n'
    )
    ns = 'http://www.hsmworks.com/xml/2004/cnc/tool-library'
    ET.register_namespace('', ns)

    root = ET.Element('{%s}tool-library' % ns)
    root.set('version', '35')

    for t in tools:
        tool_to_hsmlib_entry(root, t)

    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')

    with open(output_path, 'wb') as f:
        f.write(header.encode('utf-16'))
        tree.write(f, encoding='utf-16', xml_declaration=False)

    print(f" ✅ {output_path.name} ({len(tools)} Tools)")


# ─── CSV -> hsmlib conversion ────────────────────────────────────────────────

def convert_solidworks_to_hsmlib(input_path, output_dir):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_files = list(input_path.glob('*.csv')) if input_path.is_dir() else [input_path]
    all_tools = []
    for f in csv_files:
        all_tools.extend(parse_solidworks_csv(f))
    if not all_tools:
        print('⚠️  No tools found!')
        return
    out = output_dir / (csv_files[0].stem + '.hsmlib' if len(csv_files) == 1 else 'solidworks_converted.hsmlib')
    write_hsmlib(all_tools, out)
    print(f"\n✅ Done — {len(all_tools)} tools exported.")
