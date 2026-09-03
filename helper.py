#!/usr/bin/env python3
"""
helper.py

Helper functions for converter between HSMWorks .hsmlib and SolidworksCAM csv and meta file formats of tool libraries.

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

import math
import re
from uuid import uuid4

from data import *


# ─── Helpers ────────────────────────────────────────────────────────────────

def toStr(v, strip: bool = False, decimals: int = 4):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float) and strip:
        return f"{v:.{decimals}f}".rstrip("0").rstrip(".")
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def toFloat(s, default=0.0, decimals: int = 5):
    try:
        value = float(re.sub(r"[^0-9.\-]", "", str(s)))
        factor = 10 ** decimals
        return math.trunc(value * factor) / factor
    except Exception:
        return default


def xml_escape_attr(s):
    return "" if s is None else (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'",
                                                                                                              "&apos;"))


def xml_unescape(s):
    return "" if s is None else (
        str(s).replace("&apos;", "'").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;",
                                                                                                               "&"))


def xml_text(s):
    """For XML element text content (element.text = value). ElementTree
    escapes &, < and > automatically when writing .text, and double
    quotes are not special in element text at all — passing the raw
    string avoids the double-escaping bug (&quot; becoming &amp;quot;)."""
    return "" if s is None else str(s)


def make_guid():
    return str(uuid4()).upper()


def extract_angle(description):
    m = re.search(r'Angle:\s*([\d.]+)\s*deg', description or "", re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


def extract_pitch(description):
    m = re.search(r'M[\d.]+\*([0-9.]+)', description or "")
    if m:
        return float(m.group(1))
    m = re.search(r'-(\d+)(?:$|\s)', description or "")
    if m:
        return round(25.4 / float(m.group(1)), 4)
    return 0.0


def reference_length(tool) -> float:
    """
    Returns the length term that feeds compute_body_length() /
    shank_length_from_body_length(), chosen according to the tool's family:

      - milling tools    -> flute_length
      - holemaking tools  -> shoulder_length (already includes tip length)
      - everything else   -> flute_length (best available fallback; custom
                              -cutter tools should not rely on this at all,
                              see note above)
    """
    family = tool_family(tool.type)
    if family == "holemaking":
        return tool.shoulder_length
    return tool.flute_length


# ─── Geometry helpers ────────────────────────────────────────────────────────

def calc_tip_length(dia, angle_deg):
    if angle_deg <= 0:
        return 0.0
    tan_angle = math.tan(math.radians(angle_deg))
    if abs(tan_angle) < 1e-12:
        return 0.0
    return (dia / 2.0) / tan_angle


def dovetail_max_flute_length(flute_dia: float, shoulder_dia: float, angle_deg: float) -> float:
    """
    Returns the maximum geometrically valid flute_length for a dovetail
    mill: the axial height at which a cone with full included angle
    `angle_deg`, starting at `shoulder_dia`, reaches `flute_dia`.

        h = ((flute_dia - shoulder_dia) / 2) / tan(angle_deg / 2)

    Any flute_length beyond this value would mean the cutting profile
    keeps widening past flute_dia, which is geometrically inconsistent
    with a dovetail cutter's fixed included angle — the intersection of
    the tapered flute surface with shoulder_dia caps how far the flute
    can extend. Returns 0.0 if the geometry is degenerate (angle <= 0,
    or flute_dia <= shoulder_dia).
    """
    if angle_deg <= 0 or flute_dia <= shoulder_dia:
        return 0.0
    tan_angle = math.tan(math.radians(angle_deg))
    if abs(tan_angle) < 1e-12:
        return 0.0
    return ((flute_dia - shoulder_dia) / 2.0) / tan_angle


def dovetail_flute_length(flute_dia: float, shoulder_dia: float, angle_deg: float,
                          candidate_flute_length: float = None) -> float:
    """
    Computes flute_length for a dovetail mill, clamped so it never exceeds
    the axial height needed for the cutting profile to reach flute_dia
    starting from shoulder_dia at the given included angle (see
    dovetail_max_flute_length()).

    If candidate_flute_length is given (e.g. read from a source column),
    it is clamped to the geometric maximum. If omitted, the geometric
    maximum itself is returned directly — matching the existing
    parse_solidworks_csv() DOVETAIL behavior, which currently derives
    flute_length purely from calc_tip_length(d1 - d2, tip_angle) with no
    independent source value to clamp.
    """
    max_len = dovetail_max_flute_length(flute_dia, shoulder_dia, angle_deg)
    if candidate_flute_length is None:
        return max_len
    return min(max(candidate_flute_length, 0.0), max_len)


def tap_shoulder_length(overall_length: float) -> float:
    """
    Reconstruct hsmlib shoulder/body length for tap tools.

    shoulder_length / overall_length:
        average = 0.662
        median  = 0.664

    Taps in the examined hsmlib library have no <shaft> sections and use:
        body-length == shoulder-length
    """
    return overall_length * 0.66


def build_shaft_sections(shoulder_dia: float, shoulder_length: float,
                         shank_dia: float, shank_length: float) -> list:
    """
    Builds the <shaft><section> entries for tools with a neck/transition
    (shoulder_dia over shoulder_length, then transitioning to shank_dia over
    shank_length). For tools with no neck (shoulder_dia == shank_dia and
    shoulder_length == 0), this degenerates to the simple 2-section case
    seen in most Flat/Ball/Bullnose end mills.
    """
    return [
        (shoulder_dia, 0.0),
        (shoulder_dia, shoulder_length),
        (shank_dia, shank_length),
    ]


def compute_body_length(reference_length: float, shaft_sections: list) -> float:
    """
    hsmlib body-length = reference_length + sum(section lengths)
                          + (diameter of the LAST section) / 2

    `reference_length` is flute_length for milling tools, shoulder_length
    for hole-making tools (see _reference_length()). Verified exact on
    36/36 milling-tool samples and 4/5 hole-making-tool samples across four
    different hsmlib libraries (Harvey Tool End Mills / Specialty Profiles /
    Holemaking & Threading, Helical Solutions End Mills).
    """
    sum_sections = sum(length for _, length in shaft_sections)
    last_diameter = shaft_sections[-1][0]
    return reference_length + sum_sections + last_diameter / 2.0


def shank_length_from_body_length(body_length: float, reference_length: float,
                                  shoulder_length: float, shank_dia: float) -> float:
    """
    Exact inverse of compute_body_length() for the standard 3-section shaft
    pattern. `reference_length` must be chosen the same way as in
    compute_body_length() (flute_length for milling tools, shoulder_length
    for hole-making tools) — for hole-making tools this means the call
    becomes shank_length_from_body_length(body_length, shoulder_length, 0.0,
    shank_dia), since shoulder_length is already the reference term and must
    not be subtracted twice.
    """
    return body_length - reference_length - shoulder_length - (shank_dia / 2.0)


def build_shaft_and_body_length(tool) -> tuple:
    """
    Returns (shaft_sections, body_length) for a given Tool, using the
    family-aware geometry formula. Call this from tool_to_hsmlib_entry()
    right before writing the <body> and <shaft> elements — this now works
    correctly for ALL tool types (milling and hole-making), not just
    Dovetail/Keyway/Lollipop.
    """
    family = tool_family(tool.type)
    ref_len = reference_length(tool)

    if tool.type == HSMToolType.LOLLIPOP_MILL.value:
        transition_length = ((tool.shank_dia - tool.shoulder_dia) / 2.0) * math.sqrt(3) \
            if tool.shank_dia > tool.shoulder_dia else 0.0

        shaft_sections = [
            (tool.shoulder_dia, 0.0),
            (tool.shoulder_dia, tool.shoulder_length),
            (tool.shank_dia, transition_length),
        ]

        return shaft_sections, tool.overall_length

    if tool.type == HSMToolType.RADIUS_MILL.value:
        shaft_sections = []
        return shaft_sections, tool.overall_length

    if tool.type == HSMToolType.DOVETAIL_MILL.value:
        transition_length = ((tool.shank_dia - tool.shoulder_dia) / 2.0) / math.tan(math.radians(60))

        shaft_sections = [
            (tool.shoulder_dia, 0.0),
            (tool.shoulder_dia, 0.0),
            (tool.shank_dia, transition_length),
        ]
        return shaft_sections, tool.overall_length

    if family == "holemaking":
        # For hole-making tools, shoulder_length already is the reference
        # term, so the "neck" portion of build_shaft_sections would double
        # count it. Hole-making tools observed in the sampled libraries only
        # ever have a single shank_dia transition section (no separate neck
        # diameter stage), so shoulder_length is passed as 0.0 into the
        # section builder and shank_length carries the remaining length.
        shaft_sections = build_shaft_sections(
            shoulder_dia=tool.flute_dia,
            shoulder_length=0.0,
            shank_dia=tool.shank_dia,
            shank_length=tool.shank_length,
        )
    else:
        diameter_diff = ((tool.shank_dia - tool.shoulder_dia) / 2.0)
        transition_angle = 60
        if diameter_diff < 0.25 * tool.shank_dia:
            transition_angle = 30

        transition_length = diameter_diff / math.tan(math.radians(transition_angle))
        shaft_sections = build_shaft_sections(
            shoulder_dia=tool.shoulder_dia,
            shoulder_length=tool.shoulder_length,
            shank_dia=tool.shank_dia,
            shank_length=transition_length,
        )

    body_length = compute_body_length(ref_len, shaft_sections)
    return shaft_sections, body_length


def lollipop_shoulder_dia(flute_dia: float, shank_dia: float, ratio: float = 0.65) -> float:
    """
    Approximates the neck/shoulder diameter of a Lollipop mill from the ball
    (flute) diameter, since SolidWorks CSV exports do not carry this value
    separately and instead treat the tool as if it were a constant diameter
    from ball to shank transition.

    Verified against 16 manufacturer catalog datasets (AB Tools, RedLine
    Tools): neck_dia / ball_dia is consistently ~0.64 (stdev 0.4-1%) across
    the entire 0.040"-0.340" size range. Rounded slightly up to 0.65 as a
    safe approximation, since underestimating the neck diameter risks
    predicting a tool that is weaker/more flexible than reality, while a
    stronger tool is the safer approximation error for collision checking.

    The result is clamped so the neck is never wider than the ball head and
    never wider than the final shank (a Lollipop neck is, by definition, the
    narrowest section of the tool).
    """
    shoulder_dia = flute_dia * ratio
    return min(shoulder_dia, flute_dia, shank_dia) if shank_dia > 0 else min(shoulder_dia, flute_dia)


def reconstruct_shank_length(tool, body_length: float) -> float:
    """
    Reconstructs shank_length from a known body_length using the family-
    aware exact inverse. Use this both in parse_hsmlib() (body_length taken
    from the hsmlib <body body-length="..."> attribute) and, where
    applicable, in parse_solidworks_csv() (body_length approximated by SW's
    "Overall Length (L1)" field, per the earlier Dovetail/Keyway/Lollipop
    reasoning).
    """
    family = tool_family(tool.type)
    ref_len = reference_length(tool)

    if family == "holemaking":
        # shoulder_length is the reference term itself here; pass 0.0 as the
        # "neck length" argument to avoid double-subtracting it.
        return max(shank_length_from_body_length(body_length, ref_len, 0.0, tool.shank_dia), 0.0)

    return max(shank_length_from_body_length(body_length, ref_len, tool.shoulder_length, tool.shank_dia), 0.0)


def threadmill_shoulder_length(overall_length: float, flute_dia: float) -> float:
    """
    Reconstructs shoulder_length for a thread mill from overall_length and
    flute_dia, using the empirically observed hsmlib convention:

        shoulder_length = overall_length * ratio(flute_dia)

    ratio(flute_dia) is a size-dependent step function, calibrated against
    8 monolithic Sandvik CoroMill Plura thread mills (R217.x series):

        flute_dia <=  6 mm  -> ratio ~= 0.37  (small thread mills)
        flute_dia <= 12 mm  -> ratio ~= 0.46  (mid-size thread mills)
        flute_dia  > 12 mm  -> ratio ~= 0.54  (large thread mills)

    Note: this is an approximation, not an exact geometric formula
    """
    if flute_dia <= 6:
        ratio = 0.37
    elif flute_dia <= 12:
        ratio = 0.46
    else:
        ratio = 0.54
    return overall_length * ratio


def clamp_body_length(body_length: float, overall_length: float) -> float:
    """
    Returns a valid hsmlib body-length.

    body-length is the modeled tool length below the holder reference. It
    must never exceed overall-length, otherwise the generated geometry is
    self-contradictory and HSMWorks/Fusion may reject or display it wrongly.
    """
    if overall_length <= 0.0:
        return max(body_length, 0.0)
    return min(max(body_length, 0.0), overall_length)


def thread_tooth_height(thread_pitch: float, thread_profile_angle: float = 60.0) -> float:
    """
    Returns the radial height of an ideal symmetric V-thread tooth.

    For a thread with pitch P and included profile angle alpha:

        h = P / (2 * tan(alpha / 2))

    The profile angle controls the radial height. The thread/cutting diameter
    is not sufficient to determine h by itself. The result is the theoretical
    sharp-V height; real ISO/UN thread forms have crest/root truncation, so
    this is a conservative geometry approximation for hsmlib reconstruction.
    """
    if thread_pitch <= 0.0 or thread_profile_angle <= 0.0:
        return 0.0
    half_angle_rad = math.radians(thread_profile_angle / 2.0)
    tan_half_angle = math.tan(half_angle_rad)
    if abs(tan_half_angle) < 1e-12:
        return 0.0
    return thread_pitch / (2.0 * tan_half_angle)


def threadmill_tooth_count_from_flute_length(flute_length: float,
                                             thread_pitch: float) -> int:
    """
    Returns the number of complete axial thread teeth for a multi-point
    thread mill.

    The axial width/repetition distance of one thread tooth is the THREAD
    PITCH, not a value derived from the cutter diameter or profile angle.
    Therefore:

        number_of_teeth = floor(flute_length / thread_pitch)

    floor() is deliberate: the SolidWorks flute length can include a partial
    lead-in/lead-out profile. Rounding could create a fictitious complete
    tooth that extends beyond the available cutting length. At least one tooth
    is emitted whenever pitch is valid, because the object is explicitly a
    thread mill.
    """
    if thread_pitch <= 0.0:
        return 1
    return max(1, math.floor(flute_length / thread_pitch + 1e-9))


def threadmill_shoulder_dia(thread_dia: float,
                            thread_pitch: float,
                            thread_profile_angle: float = 60.0) -> float:
    """
    Reconstructs the neck/shoulder diameter of a single-point thread mill.

    thread_dia is the outer thread/cutting diameter stored by SolidWorks as
    "Dia. (D1)". The shoulder is located behind the V-thread profile and must
    be reduced by twice the radial tooth height:

        shoulder_dia = thread_dia - 2 * tooth_height

    The value is clamped to >= 0 to prevent invalid XML for incomplete or
    unusual CSV data.
    """
    tooth_height = thread_tooth_height(thread_pitch, thread_profile_angle)
    return max(0.0, thread_dia - 2.0 * tooth_height)


def lollipop_shoulder_length(diameter: float, shank_dia: float) -> float:
    """
    Computes Shoulder Length (L4) = Shank Length (L6) for Lollipop tools.
    Geometric spherical-cap height: h = R + sqrt(R^2 - r_shank^2)
    (R = ball-head radius, r_shank = shank radius; the ball center sits R above the tip).
    """
    R = diameter / 2.0
    r_shank = shank_dia / 2.0
    if R < r_shank:
        raise ValueError("Shank diameter must not exceed tool diameter for a Lollipop tool")
    return R + math.sqrt(R ** 2 - r_shank ** 2)


def tapered_mill_shoulder_dia(flute_dia: float, corner_radius: float,
                              flank_angle_deg: float, flute_length: float) -> float:
    """
    Computes the shoulder diameter of a tapered mill (ball-nose or flat/
    bullnose taper) from flute_dia, corner_radius (ball radius; 0 for a
    flat/pointed taper), flank_angle_deg (half-angle from the tool axis —
    same convention as hsmlib's taper-angle and SolidWorks' Taper Angle
    (A) / Tip Angle (A)), and flute_length.

    Ball-nose case (corner_radius > 0): the ball of radius R sits at the
    tip, tangent to the cone wall. The tangent point (radius, axial height
    measured from the very tip) is:

        r_t = R * cos(theta)
        z_t = R * (1 - sin(theta))

    Beyond the tangent point the cone continues linearly, so the radius at
    any axial position z >= z_t is:

        r(z) = r_t + (z - z_t) * tan(theta)

    Flat/pointed taper case (corner_radius == 0 or not given): the cone
    starts directly at flute_dia/2 at z=0:

        r(z) = flute_dia / 2 + z * tan(theta)

    shoulder_dia = 2 * r(flute_length)

    Verified exact (to 6 decimal places) against 4 independent
    tapered-ball-nose Harvey Tool records (corner_radius 0.015"-0.03",
    flank angle 1°-20°) and 1 tapered-flat/bullnose record.
    """
    if flank_angle_deg <= 0:
        return flute_dia
    theta = math.radians(flank_angle_deg)
    if corner_radius and corner_radius > 0:
        r_t = corner_radius * math.cos(theta)
        z_t = corner_radius * (1.0 - math.sin(theta))
        shoulder_r = r_t + (flute_length - z_t) * math.tan(theta)
    else:
        shoulder_r = flute_dia / 2.0 + flute_length * math.tan(theta)
    return 2.0 * shoulder_r
