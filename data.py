#!/usr/bin/env python3
"""
data.py

Data structures and mappings between formats.

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

from dataclasses import dataclass
from enum import Enum


# ─── Definitions ─────────────────────────────────────────────────────────────
class SWToolType(Enum):
    BORES = "BORES"
    CENTER_DRILL = "CenterDrill"
    COUNTERSINK = "CounterSink"  # aka chamfer
    CORNER_ROUNDING = "CornerRounding"
    DOVETAIL = "Dovetail"
    KEYWAY = "Keyway"
    DRILLS = "DRILLS"
    FACE_MILL = "FaceMillTool"
    LOLLIPOP = "Lollipop"
    THREAD_MULTI = "ThreadMillMultiPt"
    THREAD_SINGLE = "ThreadMillSinglePt"
    TAPER_HOG_NOSE = "Taper_Hog_Nose"
    TAPER_FLATEND = "Taper_Flatend"
    TAPER_BALLNOSE = "Taper_BallNose"
    TAPS_LH = "nTaps"
    TAPS_RH = "nTaps"
    BARREL_TOOL_STD = "BarrelTool_Standard"
    BARREL_TOOL_CONICAL = "BarrelTool_Conical"
    BARREL_TOOL_TAPER = "BarrelTool_Taper"
    BARREL_TOOL_TAPER_LENS = "BarrelTool_Taper_Lens"
    BARREL_TOOL_TAPER_ADVANCED = "BarrelTool_Taper_Advanced"
    FLAT_END_MILL = "MILLC_FLAT_END"
    BALL_NOSE_MILL = "MILLC_BALL_NOSE"
    HOG_NOSE_MILL = "MILLC_HOG_NOSE"
    PROBE = "ProbeTool"
    UNKNOWN = "unknown"
    REAMERS = "REAMERS"


class HSMToolType(Enum):
    # Milling Tool Types
    FLAT_END_MILL = "flat end mill"
    BALL_END_MILL = "ball end mill"
    BULLNOSE_END_MILL = "bull nose end mill"
    CHAMFER_MILL = "chamfer mill"
    TAPERED_MILL = "tapered mill"
    LOLLIPOP_MILL = "lollipop mill"
    THREAD_MILL = "thread mill"
    SLOT_MILL = "slot mill"
    FACE_MILL = "face mill"
    DOVETAIL_MILL = "dovetail mill"

    # Hole Making & Drilling Tool Types
    DRILL = "drill"
    SPOT_DRILL = "spot drill"
    CENTER_DRILL = "center drill"
    COUNTERBORE = "counter bore"
    COUNTERSINK = "counter sink"
    RIGHT_HAND_TAP = "tap right hand"
    LEFT_HAND_TAP = "tap left hand"
    REAMER = "reamer"
    BORING_BAR = "boring bar"
    BLOCK_DRILL = "block drill"
    RADIUS_MILL = "radius mill"
    # Turning Tool Types (Lathe)
    # TURNING_GENERAL = "turning general"
    # TURNING_BORING = "turning boring"
    # TURNING_GROOVING = "turning grooving"
    # TURNING_THREADING = "turning threading"

    # Special & Custom Types
    # FORM_MILL = "form mill"
    PROBE = "probe"
    UNKNOWN = "unknown"


# Bidirectional mapping table
# SWToolType -> HSMToolType
SW_TO_HSM_MAP = {
    "FLAT_END_MILL": HSMToolType.FLAT_END_MILL,
    "BALL_NOSE_MILL": HSMToolType.BALL_END_MILL,
    "HOG_NOSE_MILL": HSMToolType.BULLNOSE_END_MILL,
    "COUNTERSINK": HSMToolType.CHAMFER_MILL,
    "TAPER_FLATEND": HSMToolType.TAPERED_MILL,
    "TAPER_BALLNOSE": HSMToolType.TAPERED_MILL,
    "TAPER_HOG_NOSE": HSMToolType.TAPERED_MILL,
    "THREAD_MULTI": HSMToolType.THREAD_MILL,
    "THREAD_SINGLE": HSMToolType.THREAD_MILL,
    "DRILLS": HSMToolType.DRILL,
    "CENTER_DRILL": HSMToolType.CENTER_DRILL,
    "FACE_MILL": HSMToolType.FACE_MILL,
    "LOLLIPOP": HSMToolType.LOLLIPOP_MILL,
    "DOVETAIL": HSMToolType.DOVETAIL_MILL,
    "BORES": HSMToolType.BORING_BAR,
    "TAPS_RH": HSMToolType.RIGHT_HAND_TAP,
    "TAPS_LH": HSMToolType.LEFT_HAND_TAP,
    "PROBE": HSMToolType.PROBE,
    "CORNER_ROUNDING": HSMToolType.RADIUS_MILL,
    "KEYWAY": HSMToolType.SLOT_MILL,
    "REAMERS": HSMToolType.REAMER,
}

HSM_TO_SW_MAP = {
    "FLAT_END_MILL": SWToolType.FLAT_END_MILL,
    "BALL_END_MILL": SWToolType.BALL_NOSE_MILL,
    "BULLNOSE_END_MILL": SWToolType.HOG_NOSE_MILL,
    "CHAMFER_MILL": SWToolType.COUNTERSINK,
    "TAPERED_MILL": SWToolType.TAPER_FLATEND,
    "THREAD_MILL": SWToolType.THREAD_MULTI,
    "DRILL": SWToolType.DRILLS,
    "CENTER_DRILL": SWToolType.CENTER_DRILL,
    "SPOT_DRILL": SWToolType.DRILLS,
    "COUNTERSINK": SWToolType.COUNTERSINK,
    "COUNTERBORE": SWToolType.DRILLS,
    "RIGHT_HAND_TAP": SWToolType.TAPS_RH,
    "LEFT_HAND_TAP": SWToolType.TAPS_LH,
    "REAMER": SWToolType.REAMERS,
    "BORING_BAR": SWToolType.BORES,
    "FACE_MILL": SWToolType.FACE_MILL,
    "LOLLIPOP_MILL": SWToolType.LOLLIPOP,
    "DOVETAIL_MILL": SWToolType.DOVETAIL,
    "PROBE": SWToolType.PROBE,
    "SLOT_MILL": SWToolType.KEYWAY,
    "RADIUS_MILL": SWToolType.CORNER_ROUNDING
}

MILLING_HSM_TYPES = {
    HSMToolType.FLAT_END_MILL.value,
    HSMToolType.BALL_END_MILL.value,
    HSMToolType.BULLNOSE_END_MILL.value,
    HSMToolType.LOLLIPOP_MILL.value,
    HSMToolType.DOVETAIL_MILL.value,
    HSMToolType.SLOT_MILL.value,
    HSMToolType.FACE_MILL.value,
    HSMToolType.CHAMFER_MILL.value,
    HSMToolType.RADIUS_MILL.value
}

HOLEMAKING_HSM_TYPES = {
    HSMToolType.DRILL.value,
    HSMToolType.SPOT_DRILL.value,
    HSMToolType.COUNTERBORE.value,
    HSMToolType.CENTER_DRILL.value,
    HSMToolType.REAMER.value,
    HSMToolType.BORING_BAR.value,
    HSMToolType.BLOCK_DRILL.value,
}

CUSTOM_PROFILE_HSM_TYPES = {
    HSMToolType.THREAD_MILL.value,
    HSMToolType.LEFT_HAND_TAP.value,
    HSMToolType.RIGHT_HAND_TAP.value,
    HSMToolType.RADIUS_MILL.value,
    HSMToolType.TAPERED_MILL.value,
    # "form mill" is not a formal HSMToolType member in this script (Harvey
    # Tool exports thread mills and reamers under the generic hsmlib type
    # "form mill" with a <custom-cutter> profile); handle by raw string:
    "form mill",
}


@dataclass
class Tool:
    """ Meta tool data structure to collect variables for conversion between file formats"""
    type: str = "FLAT_END_MILL"
    vendor: str = ""
    description: str = ""
    name: str = ""
    product_link: str = ""
    material: str = "carbide"
    coating: str = "None"
    coolant_type: str = "Mist"
    overall_length: float = 0
    shank_length: float = 0
    shank_dia: float = 0
    shoulder_length: float = 0
    shoulder_dia: float = 0
    nr_flutes: int = 1
    flute_length: float = 0
    flute_dia: float = 0
    tip_dia: float = 0
    tip_angle: float = 0
    tip_length: float = 0
    angle: float = 0  # taper angle
    corner_radius: float = 0
    thread_pitch: float = 0
    thread_profile_angle: float = 60
    thread_nr_teeth: int = 0
    taper_dia: float = 0
    taper_angle: float = 0
    # presets - default values
    preset_name: str = "Default"
    spindle: float = 10000
    feed_xy: float = 300
    feed_z: float = 100
    feed_in: float = 150
    feed_out: float = 300
    clockwise: bool = True
    # mainly used by SW, however, generally this is a holder specific value
    # and should therefore not be set for new tool libraries
    protrusion: float = 0
    # hsmlib specific
    tapered_type: str = "None"
    unit: str = "millimeters"


def convert_sw_to_hsm(sw_tool_type: SWToolType) -> HSMToolType:
    """
    Convert SolidWorks tool type to HSMWorks tool type.

    Args:
        sw_tool_type: SWToolType enum member

    Returns:
        HSMToolType enum member
    """
    return SW_TO_HSM_MAP.get(sw_tool_type.name, HSMToolType.FLAT_END_MILL)


def convert_hsm_to_sw(hsm_tool_type: HSMToolType) -> SWToolType:
    """
    Convert HSMWorks tool type to SolidWorks tool type.

    Args:
        hsm_tool_type: HSMToolType enum member

    Returns:
        SWToolType enum member
    """
    return HSM_TO_SW_MAP.get(hsm_tool_type.name, SWToolType.UNKNOWN)


def convert_tool_type(tool_type: Enum, to_hsm: bool = True) -> Enum:
    """
    Generic bidirectional converter between SWToolType and HSMToolType.

    Args:
        tool_type: Either SWToolType or HSMToolType enum member
        to_hsm: If True, convert SW->HSM. If False, convert HSM->SW

    Returns:
        Converted enum member (HSMToolType or SWToolType)
    """
    if to_hsm:
        if isinstance(tool_type, SWToolType):
            return convert_sw_to_hsm(tool_type)
        elif isinstance(tool_type, HSMToolType):
            return tool_type  # Already HSM
        else:
            raise TypeError(f"Expected SWToolType or HSMToolType, got {type(tool_type)}")
    else:
        if isinstance(tool_type, HSMToolType):
            return convert_hsm_to_sw(tool_type)
        elif isinstance(tool_type, SWToolType):
            return tool_type  # Already SW
        else:
            raise TypeError(f"Expected SWToolType or HSMToolType, got {type(tool_type)}")


def tool_family(hsm_type_str: str) -> str:
    """
    Classifies an hsmlib type string into one of three geometry families,
    which determines which reference length feeds the body-length formula.

    Returns one of: "milling", "holemaking", "custom_profile", "unknown".
    """
    if hsm_type_str in MILLING_HSM_TYPES:
        return "milling"
    if hsm_type_str in HOLEMAKING_HSM_TYPES:
        return "holemaking"
    if hsm_type_str in CUSTOM_PROFILE_HSM_TYPES:
        return "custom_profile"
    return "unknown"


def get_tool_type(raw_data, data_dict):
    tool_name = raw_data[2][1]
    tool_type = SWToolType.UNKNOWN

    # remove unit prefix from name
    tool_name = tool_name.removeprefix("in_")

    # real tool type is encoded in different field
    if tool_name == 'MILLC':
        sub_type_id = data_dict[0]['Mill Tool Type']
        if sub_type_id == "1":
            tool_type = SWToolType.FLAT_END_MILL
        elif sub_type_id == "2":
            tool_type = SWToolType.BALL_NOSE_MILL
        elif sub_type_id == "3":
            tool_type = SWToolType.HOG_NOSE_MILL

    elif tool_name == 'Taper':
        sub_type_id = data_dict[0]["CutEndType"]
        if sub_type_id == "1":
            tool_type = SWToolType.TAPER_FLATEND
        if sub_type_id == "2":
            tool_type = SWToolType.TAPER_BALLNOSE
        if sub_type_id == "3":
            tool_type = SWToolType.TAPER_HOG_NOSE

    elif tool_name == 'BarrelTool':
        sub_type_id = data_dict[0]["Barrel Tool Type"]
        if sub_type_id == "Standard":
            tool_type = SWToolType.BARREL_TOOL_STD
        if sub_type_id == "Tapered":
            tool_type = SWToolType.BARREL_TOOL_TAPER
        if sub_type_id == "Conical":
            tool_type = SWToolType.BARREL_TOOL_CONICAL
    elif tool_name == 'nTaps':
        if data_dict[0]["HandOfCutID"] == "Right hand":
            tool_type = SWToolType.TAPS_RH
        else:
            tool_type = SWToolType.TAPS_LH
    else:
        tool_type = SWToolType(tool_name)

    return tool_type
