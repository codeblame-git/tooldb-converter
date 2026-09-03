#!/usr/bin/env python3
"""
to_swcam.py

Converts to swcam format and contains a lot of necessary boilerplate code

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
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from helper import *


# ─── SolidWorks CSV Header ────────────────────────────────────────────────────────────────────────────────────────────
# SW/CAMWorks is coded by monkeys on lsd, broken out of a psychiatry, who used MSWord as IDE.
# The "creators" in their infinite wisdom are not capable of using the same column names for all their tools
# and variables. Between exported csv files, even whitespaces, special characters and typos matter.
# The colossal clusterfuck that is their data structures are a sight to behold.

def make_header(sw_tool_type, unit):
    tool_type = sw_tool_type
    tool_name = sw_tool_type.value

    if sw_tool_type == SWToolType.FLAT_END_MILL or sw_tool_type == SWToolType.BALL_NOSE_MILL or sw_tool_type == SWToolType.HOG_NOSE_MILL:
        tool_name = "MILLC"
    if sw_tool_type == SWToolType.TAPER_FLATEND or sw_tool_type == SWToolType.TAPER_BALLNOSE or sw_tool_type == SWToolType.TAPER_HOG_NOSE:
        tool_name = "Taper"

    row1_cols = TOOL_TYPE_HEADER_MAP.get(tool_type, HEADER_FLAT_END)
    row1 = ",".join(row1_cols)

    return (
        # First row is the masterpiece of an unpaid intern when the boss tells him "Write a data export format, how hard could it be?"
        # Of course every tool type has to get it's special one, otherwise he would have been done coding this nightmare 2 weeks earlier.
        f"{row1}\n"
        f"File Info:,ToolName,Unit,Language\n"
        f",{tool_name},{unit},English\n"
        f"Reserved,For future use\n" # which future?
        f"Reserved,For future use\n" # almost a decade has passed and you have not changed anything for the better
        f"Note:,Please don't delete or modify rows 1 thru 6. "  # When you have failed in your task and all there is left 
        # is begging people not to add a whitespace by mistake or the entire database file becomes unusable.
        f"Tool data field names are in row 9. Tool data starts from 10th row onwards. "  # no shit sherlock
        f"User comments can be put in row 7 and 8\n" # put me on death row first
        f"User note 1,This field can be used by the user for comments/notes\n"  # I have a note: "Liberate tute me ex inferis"
        f"User note 2\n"
    )


COLS_BORES = ["ID", "Active", "Tool ID", "Min. Bore Dia.(D1)", "Max. Rad. Cut Depth", "Rad. Adjust. Range",
              "Flute Length (L2)", "Overall Length (L1)", "Ineffective Length (L5)", "Tool Material", "Min.  TPI",
              "Comment", "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type",
              "Spindle_Speed", "Z_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type",
              "Shank Length (L6)", "Shoulder Dia (D4)", "Vendor", "Description", "HandOfCutID"]
COLS_CENTER_DRILL = ["ID", "Active", "Tool ID", "Size Designation", "Shank Dia (D2)", "Drill Dia. (D1)",
                     "C\'Sink Angle (A)", " Tip  Angle (A)", "Flute Length   (L2)", "Overall Length (L1)",
                     "No. Of Flutes", "Tool Material", "Comment", "Protrusion   (L3)", "Coolant Type", "Spindle_Speed",
                     "Z_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type",
                     "Shank Length (L6)", "Shoulder Dia (D4)", "Vendor", "Description", "ShoulderLen", "HandOfCutID"]
COLS_COUNTERSINK = ["ID", "Active", "Tool ID", "Size Designation", "Diameter (D1)", "C\'Sink Angle (A)", "Length (L1)",
                    "No. Of Flutes", "Tool Material", "Comment", "Protrusion (L3)", "ShankDia", "EndDia",
                    "Shoulder Length (L4)", "Coolant Type", "Spindle_Speed", "Z_Feedrate", "SurfaceFeed", "FeedPerRev",
                    "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)", "Vendor",
                    "Description", "HandOfCutID"]
COLS_CORNER_ROUNDING = ["ID", "Active", "Tool ID", "Radius (R1)", "End Dia.(D1)", "Body Dia.", "Shank Dia.",
                        "Flute Length (L2)", "Overall Length (L1)", "Body Length (L5)", "No. Of Flutes",
                        "Tool Material", "Comment", "Protrusion   (L3)", "Output", "Coolant Type", "Spindle_Speed",
                        "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                        "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)",
                        "Center Cutting", "Vendor", "Description", "HandOfCutID"]
COLS_DOVETAIL = ["ID", "Active", "Tool ID", "Diameter  (D1)", "Shank Dia.  (D2)", "Radius (R)", " Tip  Angle (A)",
                 "Overall Length (L1)", "No. Of Flutes", "Tool Material", "Comment", "Protrusion   (L3)",
                 "Coolant Type", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate",
                 "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)",
                 "Shoulder Dia (D4)", "Center Cutting", "Vendor", "Description", "Shoulder Length (L4)", "HandOfCutID"]
COLS_DRILLS = ["ID", "Active", "Tool ID", "Fraction Or No.", "Diameter (D1)", "Flute Length (L2)",
               "Overall Length (L1)", "No. Of Flutes", " Tip  Angle (A)", "Tip Length", "Tool Material", "Comment",
               "Protrusion   (L3)", "Shank Dia.  (D2)", "ToolTipType", "Shoulder Length (L4)", "Coolant Type",
               "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed",
               "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)", "Vendor",
               "Description", "HandOfCutID"]
COLS_FACE_MILL = ["ID", "Active", "Tool ID", " Diameter  (D1)", "Body Diameter (D3)", "Shank Dia.  (D2)",
                  "Flute Length (L2)", "Overall Length (L1)", "Shoulder Length (L4)", "Protrusion   (L3)",
                  "Hand Of Cut", " No. Of Inserts", "Tool Material", "Comment", "Coolant Type", "Spindle_Speed",
                  "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                  "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)", "Center Cutting",
                  "Vendor", "Description"]
COLS_KEYWAY = ["ID", "Active", "Tool ID", "Diameter  (D1)", "Shank Dia.  (D2)", "Bottom Radius (R1)", "Top Radius (R2)",
               "Flute Length (L2)", "Overall Length (L1)", "No. Of Flutes", "Tool Material", "Comment",
               "Protrusion   (L3)", "Coolant Type", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
               "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type",
               "Shank Length (L6)", "Shoulder Dia (D4)", "Center Cutting", "Vendor", "Description",
               "Shoulder Length (L4)", "HandOfCutID"]
COLS_LOLLIPOP = ["ID", "Active", "Tool ID", "Diameter (D1)", "Shank Dia.  (D2)", "Shoulder Length (L4)",
                 "Flute Length (L2)", "Overall Length (L1)", "Protrusion   (L3)", "No. Of Flutes", "Tool Material",
                 "Comment", "Coolant Type", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
                 "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type",
                 "Shank Length (L6)", "Shoulder Dia (D4)", "Vendor", "Description", "HandOfCutID"]
COLS_THREAD_MULTI = ["ID", "Active", "Dia. (D1)", "Min. Hole Dia.", "Pitch (P)", "Overall Length (L1)",
                     "Ineff. Length (L5)", "Flute Length (L2)", "Thread Pitch Angle", "Thread Angle", "No. Of Flutes",
                     "Tool Material", "Comment", "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)",
                     "Coolant Type", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
                     "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type",
                     "Shank Length (L6)", "Shoulder Dia (D4)", "Vendor", "Description", "Tool ID", "HandOfCutID"]
COLS_THREAD_SINGLE = ["ID", "Active", "Dia. (D1)", "Min. Hole Dia.", "Overall Length (L1)", "Ineff. Length (L5)",
                      "Flute Length (L2)", "Thread Pitch Angle", "No. Of Flutes", "Tool Material", "Comment",
                      "Protrusion   (L3)", "Shank Dia.  (D2)", "Coolant Type", "Spindle_Speed", "Z_Feedrate",
                      "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                      "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)", "Vendor",
                      "Description", "Tool ID", "HandOfCutID"]
COLS_TAPER_HOG_NOSE = ["ID", "Active", "Tool ID", "End Dia. (D1)", " End Radius   (R)", "Taper Angle (A)",
                       "Flute Length  (L2)", "Overall Length (L1)", "No. Of Flutes", "Tool Material", "CutEndType",
                       "Comment", "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type",
                       "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate",
                       "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)",
                       "Shoulder Dia (D4)", "Center Cutting", "Vendor", "Description", "HandOfCutID"]
COLS_TAPER_FLATEND = ["ID", "Active", "Tool ID", "End Dia. (D1)", "EndRadius", "Taper Angle (A)", "Flute Length  (L2)",
                      "Overall Length (L1)", "No. Of Flutes", "Tool Material", "CutEndType", "Comment",
                      "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type", "Spindle_Speed",
                      "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                      "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)", "Center Cutting",
                      "Vendor", "Description", "HandOfCutID"]
COLS_TAPER_BALLNOSE = ["ID", "Active", "Tool ID", "End Dia. (D1)", " End Radius   (R)", "Taper Angle (A)",
                       "Flute Length  (L2)", "Overall Length (L1)", "No. Of Flutes", "Tool Material", "CutEndType",
                       "Comment", "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type",
                       "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate",
                       "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)",
                       "Shoulder Dia (D4)", "IsCenterCuttingTool", "Vendor", "Description", "HandOfCutID"]
COLS_TAPS = ["ID", "Active", "Thread Types", "Tap Desig.", "Major Diameter (D1)", "Thread Pitch", "Tap Drill Dia.",
             "Drill Diameter - Rolling Tap Tool", "Ineffective Length (L5)", "Overall Length (L1)", "Tool Material",
             "Comment", "Comment_roll", "Protrusion   (L3)", "Shank Dia.  (D2)", "Depth >", "Depth <=", "StockGroupId",
             "Shoulder Length (L4)", "Flute Length (L2)", "NodeDesc", "CoolantType", "Spindle_Speed", "Z_Feedrate",
             "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "Spindle", "SurfaceFeed", "FeedPerRev",
             "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia", "Vendor", "Description", "Vendor_roll",
             "Description_roll", "Tool ID", "ToolID_roll", "HandOfCutID"]
COLS_FLAT_END = ["ID", "Active", "Tool ID", "Mill Tool Type", "Sub-type", "Radius", "Diameter  (D1)",
                 "Flute Length (L2)", "Overall Length (L1)", "No. Of Flutes", "Tool Material", "Comment",
                 "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type", "Spindle_Speed",
                 "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                 "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)", "Center Cutting",
                 "Vendor", "Description", "HandOfCutID"]
COLS_BALL_NOSE = ["ID", "Active", "Tool ID", "Mill Tool Type", "Sub-type", " End Radius   (R)", "Diameter  (D1)",
                  "Flute Length (L2)", "Overall Length (L1)", "No. Of Flutes", "Tool Material", "Comment",
                  "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type", "Spindle_Speed",
                  "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                  "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)",
                  "IsCenterCuttingTool", "Vendor", "Description", "HandOfCutID"]
COLS_HOG_NOSE = ["ID", "Active", "Tool ID", "Mill Tool Type", "Sub-type", "Radius", "Diameter  (D1)",
                 "Flute Length (L2)", "Overall Length (L1)", "No. Of Flutes", "Tool Material", "Comment",
                 "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type", "Spindle_Speed",
                 "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                 "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)", "Shoulder Dia (D4)", "Center Cutting",
                 "Vendor", "Description", "HandOfCutID"]

COLS_REAMERS = ["ID", "Active", "Tool ID", "Min. Cut Dia.", "Max. Cut Dia. (D1)", "Flute Length (L2)",
                "Overall Length (L1)", "No. Of Flutes", "Ineff. Length (L5)", "Tool Material", "Core  Dia.", "Comment",
                "Protrusion   (L3)", "Shank Dia.  (D2)", "Shoulder Length (L4)", "Coolant Type", "Spindle_Speed",
                "Z_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "Shank Type", "Shank Length (L6)",
                "Shoulder Dia (D4)", "Vendor", "Description", "Center Cutting", "HandOfCutID"]

# ToDo or not to do
# COLS_PROBE = ["ID","Active","Diameter (D1)","Overall Length (L1)","Effective Working Length","Comment","Protrusion   (L3)","Shank Dia.  (D2)","Shank Type","Shank Length (L6)","Shoulder Dia (D4)","Shoulder Length (L4)","XY_Feedrate","Vendor","Description","Tool ID"]
# COLS_BARREL_TOOL_STD = ["ID","ON","InsMillBdyID","Barrel Tool Type","SubType","Radius","CuttingDia","EffAxlCutLen","OverallLen","NoOfFlutes","TmcID","Comment","Protrusion","ShankDia","ShoulderLen","CoolantType","Spindle_Speed","Z_Feedrate","Diameter_Offset","Length_Offset","XY_Feedrate","Leadin_Feedrate","Leadout_Feedrate","SurfaceFeed","FeedPerRev","IsSurfaceFeedConstant","ShankType","ShankLength","ShoulderDia","IsCenterCuttingTool","Vendor","Description","ProfileRadius","TaperAngle","UpperRadius","ConvexRadius","Zcenter","FlatnessDia","HandOfCutID"]
# COLS_BARREL_TOOL_CONICAL = ["ID","ON","InsMillBdyID","Barrel Tool Type","SubType","Radius","CuttingDia","EffAxlCutLen","OverallLen","NoOfFlutes","TmcID","Comment","Protrusion","ShankDia","ShoulderLen","CoolantType","Spindle_Speed","Z_Feedrate","Diameter_Offset","Length_Offset","XY_Feedrate","Leadin_Feedrate","Leadout_Feedrate","SurfaceFeed","FeedPerRev","IsSurfaceFeedConstant","ShankType","ShankLength","ShoulderDia","IsCenterCuttingTool","Vendor","Description","ProfileRadius","TaperAngle","UpperRadius","ConvexRadius","Zcenter","FlatnessDia","HandOfCutID"]
# COLS_BARREL_TOOL_TAPER = ["ID","ON","InsMillBdyID","Barrel Tool Type","SubType","Radius","CuttingDia","EffAxlCutLen","OverallLen","NoOfFlutes","TmcID","Comment","Protrusion","ShankDia","ShoulderLen","CoolantType","Spindle_Speed","Z_Feedrate","Diameter_Offset","Length_Offset","XY_Feedrate","Leadin_Feedrate","Leadout_Feedrate","SurfaceFeed","FeedPerRev","IsSurfaceFeedConstant","ShankType","ShankLength","ShoulderDia","IsCenterCuttingTool","Vendor","Description","ProfileRadius","TaperAngle","UpperRadius","ConvexRadius","Zcenter","FlatnessDia","HandOfCutID"]
# COLS_BARREL_TOOL_LENS = ["ID","ON","InsMillBdyID","Barrel Tool Type","SubType","Radius","CuttingDia","EffAxlCutLen","OverallLen","NoOfFlutes","TmcID","Comment","Protrusion","ShankDia","ShoulderLen","CoolantType","Spindle_Speed","Z_Feedrate","Diameter_Offset","Length_Offset","XY_Feedrate","Leadin_Feedrate","Leadout_Feedrate","SurfaceFeed","FeedPerRev","IsSurfaceFeedConstant","ShankType","ShankLength","ShoulderDia","IsCenterCuttingTool","Vendor","Description","ProfileRadius","TaperAngle","UpperRadius","ConvexRadius","Zcenter","FlatnessDia","HandOfCutID"]
# COLS_BARREL_TOOL_ADVANCED = ["ID","ON","InsMillBdyID","Barrel Tool Type","SubType","Radius","CuttingDia","EffAxlCutLen","OverallLen","NoOfFlutes","TmcID","Comment","Protrusion","ShankDia","ShoulderLen","CoolantType","Spindle_Speed","Z_Feedrate","Diameter_Offset","Length_Offset","XY_Feedrate","Leadin_Feedrate","Leadout_Feedrate","SurfaceFeed","FeedPerRev","IsSurfaceFeedConstant","ShankType","ShankLength","ShoulderDia","IsCenterCuttingTool","Vendor","Description","ProfileRadius","TaperAngle","UpperRadius","ConvexRadius","Zcenter","FlatnessDia","HandOfCutID"]

COMMON_COLS = [
    "ID",
    "Comment",
    "Protrusion   (L3)",
    "Coolant Type",
    "Spindle_Speed",
    "Z_Feedrate",
    "SurfaceFeed",
    "FeedPerRev",
    "IsSurfaceFeedConstant",
    "Shank Type",
    "Shank Length (L6)",
    "Shoulder Dia (D4)",
    "Vendor",
    "Description",
    "Material",
    "HandOfCutID",
]

HEADER_BARRELTOOL_TAPERED = ["ID", "ON", "InsMillBdyID", "Barrel Tool Type", "SubType", "Radius", "CuttingDia",
                             "EffAxlCutLen", "OverallLen", "NoOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia",
                             "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "Diameter_Offset",
                             "Length_Offset", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed",
                             "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
                             "IsCenterCuttingTool", "Vendor", "Description", "ProfileRadius", "TaperAngle",
                             "UpperRadius", "ConvexRadius", "Zcenter", "FlatnessDia", "HandOfCutID"]
HEADER_BARRELTOOL_STANDARD = ["ID", "ON", "InsMillBdyID", "Barrel Tool Type", "SubType", "Radius", "CuttingDia",
                              "EffAxlCutLen", "OverallLen", "NoOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia",
                              "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "Diameter_Offset",
                              "Length_Offset", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed",
                              "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
                              "IsCenterCuttingTool", "Vendor", "Description", "ProfileRadius", "TaperAngle",
                              "UpperRadius", "ConvexRadius", "Zcenter", "FlatnessDia", "HandOfCutID"]
HEADER_BARRELTOOL_LENS = ["ID", "ON", "InsMillBdyID", "Barrel Tool Type", "SubType", "Radius", "CuttingDia",
                          "EffAxlCutLen", "OverallLen", "NoOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia",
                          "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "Diameter_Offset",
                          "Length_Offset", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed",
                          "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
                          "IsCenterCuttingTool", "Vendor", "Description", "ProfileRadius", "TaperAngle", "UpperRadius",
                          "ConvexRadius", "Zcenter", "FlatnessDia", "HandOfCutID"]
HEADER_BARRELTOOL_ADVANCED = ["ID", "ON", "InsMillBdyID", "Barrel Tool Type", "SubType", "Radius", "CuttingDia",
                              "EffAxlCutLen", "OverallLen", "NoOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia",
                              "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "Diameter_Offset",
                              "Length_Offset", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed",
                              "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
                              "IsCenterCuttingTool", "Vendor", "Description", "ProfileRadius", "TaperAngle",
                              "UpperRadius", "ConvexRadius", "Zcenter", "FlatnessDia", "HandOfCutID"]
HEADER_BARRELTOOL_CONICAL = ["ID", "ON", "InsMillBdyID", "Barrel Tool Type", "SubType", "Radius", "CuttingDia",
                             "EffAxlCutLen", "OverallLen", "NoOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia",
                             "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "Diameter_Offset",
                             "Length_Offset", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed",
                             "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
                             "IsCenterCuttingTool", "Vendor", "Description", "ProfileRadius", "TaperAngle",
                             "UpperRadius", "ConvexRadius", "Zcenter", "FlatnessDia", "HandOfCutID"]
HEADER_CENTER_DRILL = ["ID", "ON", "ToolID", "SizeDesignation", "BodyDiameter", "DrillDiameter", "CounterSinkAngle",
                       "TipAngle", "DrillLength", "OverallLength", "NumberOfTeeth", "TmcID", "Comment", "Protrusion",
                       "CoolantType", "Spindle_Speed", "Z_Feedrate", "SurfaceFeed", "FeedPerRev",
                       "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia", "Vendor", "Description",
                       "ShoulderLen", "HandOfCutID"]
HEADER_BORES = ["ID", "ON", "NonInsBorToolID", "MinBorDia", "MaxRadDepCut", "RadAdjRange", "MaxAxlCutLen", "OverallLen",
                "Ineffective Length", "TmcID", "MinTPI", "Comment", "Protrusion", "ShankDia", "ShoulderLen",
                "CoolantType", "Spindle_Speed", "Z_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant",
                "ShankType", "ShankLength", "ShoulderDia", "Vendor", "Description", "HandOfCutID"]
HEADER_CORNER_ROUNDING = ["ID", "ON", "ToolID", "Radius", "EffectiveDiameter", "BodyDiameter", "ShankDiameter",
                          "EffectiveLength", "OverallLength", "BodyLength", "NumberOfTeeth", "TmcID", "Comment",
                          "Protrusion", "Output", "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate",
                          "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant",
                          "ShankType", "ShankLength", "ShoulderDia", "IsCenterCuttingTool", "Vendor", "Description",
                          "HandOfCutID"]
HEADER_COUNTERSINK = ["ID", "ON", "ToolID", "SizeDesignation", "Diameter", "CounterSinkAngle", "Length",
                      "NumberOfTeeth", "TmcID", "Comment", "Protrusion", "ShankDia", "EndDia", "ShoulderLen",
                      "CoolantType", "Spindle_Speed", "Z_Feedrate", "SurfaceFeed", "FeedPerRev",
                      "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia", "Vendor", "Description",
                      "HandOfCutID"]
HEADER_DOVETAIL = ["ID", "ON", "ToolID", "EffectiveDia", "ShankDia", "Radius", "Angle", "OverallLen", "NoOfFlutes",
                   "TmcID", "Comment", "Protrusion", "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate",
                   "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant",
                   "ShankType", "ShankLength", "ShoulderDia", "IsCenterCuttingTool", "Vendor", "Description",
                   "ShoulderLen", "HandOfCutID"]
HEADER_FACE_MILL = ["ID", "ON", "ToolID", "ToolDia", "BodyDia", "ShankDia", "EffectiveCutLen", "OverallLen", "BodyLen",
                    "Protrusion", "HandOfCut", "NoOfInserts", "TmcID", "Comment", "CoolantType", "Spindle_Speed",
                    "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                    "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia", "IsCenterCuttingTool", "Vendor",
                    "Description"]
HEADER_KEYWAY = ["ID", "ON", "ToolID", "EffectiveDia", "ShankDia", "BottomRad", "TopRad", "CutLen", "OverallLen",
                 "NoOfFlutes", "TmcID", "Comment", "Protrusion", "CoolantType", "Spindle_Speed", "Z_Feedrate",
                 "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                 "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia", "IsCenterCuttingTool", "Vendor",
                 "Description", "ShoulderLen", "HandOfCutID"]
HEADER_LOLLIPOP = ["ID", "ON", "ToolID", "ToolDia", "ShankDia", "ShoulderLen", "EffectiveCutLen", "OverallLen",
                   "Protrusion", "NoOfFlutes", "TmcID", "Comment", "CoolantType", "Spindle_Speed", "Z_Feedrate",
                   "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev",
                   "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia", "Vendor", "Description",
                   "HandOfCutID"]
HEADER_DRILLS = ["ID", "ON", "NonInsDrillID", "FractOrNo", "CutDia", "EffAxlCutLen", "OverallLen", "NoOfFlutes",
                 "Tip Angle", "Ineffective Length", "TmcID", "Comment", "Protrusion", "ShankDia", "ToolTipType",
                 "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
                 "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength",
                 "ShoulderDia", "Vendor", "Description", "HandOfCutID"]
HEADER_BALL_NOSE = ["ID", "ON", "InsMillBdyID", "Mill Tool Type", "SubType", "Radius", "CuttingDia", "EffAxlCutLen",
                    "OverallLen", "NoOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia", "ShoulderLen",
                    "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate",
                    "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
                    "IsCenterCuttingTool", "Vendor", "Description", "HandOfCutID"]
HEADER_FLAT_END = ["ID", "ON", "InsMillBdyID", "Mill Tool Type", "SubType", "Radius", "CuttingDia", "EffAxlCutLen",
                   "OverallLen", "NoOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia", "ShoulderLen",
                   "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate",
                   "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
                   "IsCenterCuttingTool", "Vendor", "Description", "HandOfCutID"]
HEADER_HOG_NOSE = HEADER_BALL_NOSE
HEADER_TAPS = ["ID", "ON", "Thread Type", "Diameter & Pitch", "Thread Diameter", "Thread Pitch",
               "Drill Diameter - Cutting Tap Tool", "Drill Diameter - Rolling Tap Tool", "Ineffective Length",
               "Tap Length", "TmcID", "Comment", "Comment_roll", "Protrusion", "ShankDia", "KD2RangeLower",
               "KD2RangeUpper", "StockGroupId", "ShoulderLen", "Effective Cut Length", "NodeDesc", "CoolantType",
               "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate", "Leadout_Feedrate", "Spindle_Attribute",
               "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
               "Vendor", "Description", "Vendor_roll", "Description_roll", "ToolID", "ToolID_roll", "HandOfCutID"]
HEADER_PROBE = ["ID", "ON", "Diameter", "OverallLen", "EffectiveLength", "Comment", "Protrusion", "ShankDia",
                "ShankType", "ShankLength", "ShoulderDia", "ShoulderLen", "XY_Feedrate", "Vendor", "Description",
                "ToolID"]
HEADER_REAMERS = [
    "ID", "ON", "NonInsRemID", "MinCutDia", "MaxCutDia", "EffAxlLen",
    "OverallLen", "NoOfFlutes", "Ineffective Length", "TmcID", "CoreDia",
    "Comment", "Protrusion", "ShankDia", "ShoulderLen", "CoolantType",
    "Spindle_Speed", "Z_Feedrate", "SurfaceFeed", "FeedPerRev",
    "IsSurfaceFeedConstant", "ShankType", "ShankLength", "ShoulderDia",
    "Vendor", "Description", "IsCenterCuttingTool", "HandOfCutID"
]
HEADER_TAPER_BALLNOSE = ["ID", "ON", "ToolID", "ToolDiameter", "EndRadius", "TaperAngle", "TaperLength",
                         "OverallLength", "NumberOfFlutes", "TmcID", "CutEndType", "Comment", "Protrusion", "ShankDia",
                         "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
                         "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType",
                         "ShankLength", "ShoulderDia", "IsCenterCuttingTool", "Vendor", "Description", "HandOfCutID"]
HEADER_TAPER_FLATEND = ["ID", "ON", "ToolID", "ToolDiameter", "EndRadius", "TaperAngle", "TaperLength", "OverallLength",
                        "NumberOfFlutes", "TmcID", "CutEndType", "Comment", "Protrusion", "ShankDia", "ShoulderLen",
                        "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
                        "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType",
                        "ShankLength", "ShoulderDia", "IsCenterCuttingTool", "Vendor", "Description", "HandOfCutID"]
HEADER_TAPER_HOG_NOSE = ["ID", "ON", "ToolID", "ToolDiameter", "EndRadius", "TaperAngle", "TaperLength",
                         "OverallLength", "NumberOfFlutes", "TmcID", "CutEndType", "Comment", "Protrusion", "ShankDia",
                         "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
                         "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType",
                         "ShankLength", "ShoulderDia", "IsCenterCuttingTool", "Vendor", "Description", "HandOfCutID"]
HEADER_THREAD_MULTI = ["ID", "ON", "Dia", "MinHoleDia", "Pitch", "OverallLen", "IneffLen", "EffectiveLength",
                       "ThreadPitchAngle", "Thread Angle", "NumberOfFlutes", "TmcID", "Comment", "Protrusion",
                       "ShankDia", "ShoulderLen", "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate",
                       "Leadin_Feedrate", "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant",
                       "ShankType", "ShankLength", "ShoulderDia", "Vendor", "Description", "ToolID", "HandOfCutID"]
HEADER_THREAD_SINGLE = ["ID", "ON", "Dia", "MinHoleDia", "OverallLen", "IneffLen", "EffectiveLength",
                        "ThreadPitchAngle", "NumberOfFlutes", "TmcID", "Comment", "Protrusion", "ShankDia",
                        "CoolantType", "Spindle_Speed", "Z_Feedrate", "XY_Feedrate", "Leadin_Feedrate",
                        "Leadout_Feedrate", "SurfaceFeed", "FeedPerRev", "IsSurfaceFeedConstant", "ShankType",
                        "ShankLength", "ShoulderDia", "Vendor", "Description", "ToolID", "HandOfCutID"]

# ─── Dispatch: SWToolType -> Row-1 header list ───────────────────────────────

TOOL_TYPE_HEADER_MAP = {
    SWToolType.BORES: HEADER_BORES,
    SWToolType.CENTER_DRILL: HEADER_CENTER_DRILL,
    SWToolType.COUNTERSINK: HEADER_COUNTERSINK,
    SWToolType.CORNER_ROUNDING: HEADER_CORNER_ROUNDING,
    SWToolType.DOVETAIL: HEADER_DOVETAIL,
    SWToolType.DRILLS: HEADER_DRILLS,
    SWToolType.FACE_MILL: HEADER_FACE_MILL,
    SWToolType.LOLLIPOP: HEADER_LOLLIPOP,
    SWToolType.THREAD_MULTI: HEADER_THREAD_MULTI,
    SWToolType.THREAD_SINGLE: HEADER_THREAD_SINGLE,
    SWToolType.TAPER_HOG_NOSE: HEADER_TAPER_HOG_NOSE,
    SWToolType.TAPER_FLATEND: HEADER_TAPER_FLATEND,
    SWToolType.TAPER_BALLNOSE: HEADER_TAPER_BALLNOSE,
    SWToolType.TAPS_LH: HEADER_TAPS,
    SWToolType.TAPS_RH: HEADER_TAPS,
    SWToolType.BARREL_TOOL_STD: HEADER_BARRELTOOL_STANDARD,
    SWToolType.BARREL_TOOL_CONICAL: HEADER_BARRELTOOL_CONICAL,
    SWToolType.BARREL_TOOL_TAPER: HEADER_BARRELTOOL_TAPERED,
    SWToolType.BARREL_TOOL_TAPER_LENS: HEADER_BARRELTOOL_LENS,
    SWToolType.BARREL_TOOL_TAPER_ADVANCED: HEADER_BARRELTOOL_ADVANCED,
    SWToolType.FLAT_END_MILL: HEADER_FLAT_END,
    SWToolType.BALL_NOSE_MILL: HEADER_BALL_NOSE,
    SWToolType.HOG_NOSE_MILL: HEADER_HOG_NOSE,
    SWToolType.PROBE: HEADER_PROBE,
    SWToolType.REAMERS: HEADER_REAMERS,
}

# ─── hsmlib -> CSV ───────────────────────────────────────────────────────────

# ANSI/ASME B1.1 nominal major diameters for numbered machine screws.
# These are useful in the "Fraction Or No." field because US drill/tool
# libraries commonly identify compatible tools as "#0", "#1", "#2", etc.
# Values are in inches.
NUMBERED_SCREW_DIAMETERS_IN = {
    0: 0.0600,
    1: 0.0730,
    2: 0.0860,
    3: 0.0990,
    4: 0.1120,
    5: 0.1250,
    6: 0.1380,
    8: 0.1640,
    10: 0.1900,
    12: 0.2160,
}


def normalize_tool_unit(unit: str | None) -> str:
    """
    Returns either 'inches' or 'metric'.

    Tool.unit is expected to originate from hsmlib's <tool unit="...">
    attribute. Unknown/missing values intentionally fall back to metric,
    matching the existing SolidWorks CSV default.
    """
    normalized = (unit or "millimeters").strip().lower()

    if normalized in ("inch", "inches", "in"):
        return "inches"

    return "metric"


def _format_metric_diameter(diameter_mm: float) -> str:
    """
    Formats a metric drill designation without unnecessary trailing zeros.

    Examples:
      6.0   -> '6mm'
      3.175 -> '3.175mm'
      0.55  -> '0.55mm'
    """
    return f"{diameter_mm:.5f}".rstrip("0").rstrip(".") + "mm"


def _find_numbered_screw_size(diameter_in: float, tolerance: float = 0.0015):
    """
    Returns '#<number>' when diameter_in matches a nominal ANSI numbered
    screw major diameter closely enough; otherwise returns None.

    A strict tolerance avoids incorrectly converting a real non-standard
    cutter (for example 0.159 inch) into a nominal #8 designation.
    """
    for screw_no, nominal_dia in NUMBERED_SCREW_DIAMETERS_IN.items():
        if abs(diameter_in - nominal_dia) <= tolerance:
            return f"#{screw_no}"

    return None


def _format_fractional_inch(diameter_in: float,
                            max_denominator: int = 64,
                            tolerance: float = 0.0001):
    """
    Returns a standard fractional inch string such as '1/4"' or '3/32"'
    when diameter_in is sufficiently close to a fraction with denominator
    <= max_denominator. Returns None for non-standard values.

    Whole inches are rendered as '1', '2', etc.
    """
    fraction = Fraction(diameter_in).limit_denominator(max_denominator)
    fraction_value = float(fraction)

    if abs(diameter_in - fraction_value) > tolerance:
        return None

    if fraction.denominator == 1:
        return f'{fraction.numerator}'

    return f'{fraction.numerator}/{fraction.denominator}'


def drill_fraction_or_no(tool) -> str:
    """
    Creates the SolidWorks 'Fraction Or No.' field for drill tools.

    Metric tools:
        Keep the metric diameter designation, e.g. '6mm' or '0.55mm'.

    Inch tools:
        1. Prefer an ANSI numbered-screw designation (#0 through #12)
           where the diameter closely matches one.
        2. Otherwise prefer a conventional fractional-inch representation
           with denominator <= 64, e.g. '1/4"', '3/32"', '5/16"'.
        3. Fall back to a decimal inch designation for non-standard sizes,
           e.g. '0.254"', without falsely rounding it to '1/4"'.
    """
    diameter = tool.flute_dia
    unit = normalize_tool_unit(getattr(tool, "unit", None))

    if unit == "metric":
        return _format_metric_diameter(diameter)

    screw_no = _find_numbered_screw_size(diameter)
    if screw_no is not None:
        return screw_no

    fractional = _format_fractional_inch(diameter)
    if fractional is not None:
        return fractional

    return f'{diameter * 25.4:.5f}'.rstrip("0").rstrip(".") + "mm"


def _taps_thread_type(tool) -> str:
    if "UNC" in tool.name:
        return "UNC"
    elif "UNF" in tool.name:
        return "UNF"
    elif "NPS" in tool.name:
        return "NPS"
    elif "NPT" in tool.name:
        return "NPT"
    elif "BSW" in tool.name:
        return "BSW"
    elif "BSP" in tool.name:
        return "BSP"
    else:
        return "MC"


def _get_expr_map(tool):
    """Collects all <expression> elements of a tool into a dict {parameterKey: value}."""
    expr_map = {}
    expressions = tool.find('expressions')
    if expressions is not None:
        for e in expressions.findall('expression'):
            expr_map[e.get('parameterKey')] = xml_unescape(e.get('value'))
    return expr_map


def parse_hsmlib(path):
    """
    Parses a .hsmlib file and returns a list of Tool objects.

    Reads the <tool> elements' <expressions>, <body>, <nc>, <coolant>,
    <material>, <motion> and <presets> sub-elements and maps them back onto the
    Tool dataclass (reverse of tool_to_hsmlib_entry / write_hsmlib).

    Notes:
    - shank_length is reconstructed as overall_length - (flute_length + shoulder_length).
    - tip_angle / taper-angle share the same hsmlib attribute ('taper-angle' on <body>).
      For DRILLS-like types this is read back into tip_angle,
      for tapered mills it's read back into angle.
    """
    raw = Path(path).read_text(encoding='utf-16')
    raw = re.sub(r'\s+xmlns="[^"]+"', '', raw)

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"XML-Error: {e}")
        sys.exit(1)

    tools = []

    for tool_entry in root.findall('tool'):
        expr = _get_expr_map(tool_entry)

        unit = tool_entry.get('unit', 'millimeters')

        body = tool_entry.find('body')
        body = body.attrib if body is not None else {}

        motion_entry = tool_entry.find('motion')
        motion = motion_entry.attrib if motion_entry is not None else {}

        coolant_entry = tool_entry.find('coolant')
        coolant_mode = coolant_entry.get('mode') if coolant_entry is not None else 'disabled'

        material_entry = tool_entry.find('material')
        material_name = material_entry.get('name') if material_entry is not None else expr.get('tool_material',
                                                                                               'carbide')
        description_entry = tool_entry.find('description')
        manufacturer_entry = tool_entry.find('manufacturer')
        product_id_entry = tool_entry.find('product-id')
        product_link_entry = tool_entry.find('product-link')

        preset_spindle = motion.get('spindle-rpm')
        preset_feed_xy = motion.get('cutting-feedrate')
        preset_feed_z = motion.get('plunge-feedrate')
        preset_feed_in = motion.get('entry-feedrate')
        preset_feed_out = motion.get('exit-feedrate')

        presets_el = tool_entry.find('presets/preset')
        preset_name = presets_el.get('name') if presets_el is not None else 'Default'
        if presets_el is not None:
            for p in presets_el.findall('parameter'):
                key = p.get('key')
                val = p.get('value')
                if key == 'tool_spindleSpeed':
                    preset_spindle = val
                elif key == 'tool_feedCutting':
                    preset_feed_xy = val
                elif key == 'tool_feedPlunge':
                    preset_feed_z = val
                elif key == 'tool_feedEntry':
                    preset_feed_in = val
                elif key == 'tool_feedExit':
                    preset_feed_out = val

        hsm_type_str = tool_entry.get('type', '')

        overall_length = toFloat(body.get('overall-length'))
        flute_length = toFloat(body.get('flute-length'))
        shoulder_length = toFloat(body.get('shoulder-length'))

        body_length_attr = toFloat(body.get('body-length'))
        shank_dia = toFloat(body.get('shaft-diameter'))

        angle_raw = body.get('taper-angle')
        angle_val = toFloat(angle_raw) if angle_raw else 0.0

        is_tip_angle_type = hsm_type_str in (
            HSMToolType.DRILL.value,
            HSMToolType.SPOT_DRILL.value,
            HSMToolType.CENTER_DRILL.value,
            HSMToolType.COUNTERSINK.value,
            HSMToolType.CHAMFER_MILL.value,
        )

        tool = Tool(
            type=hsm_type_str,
            name=product_id_entry.text if product_id_entry is not None and product_id_entry.text else "",
            vendor=xml_unescape(manufacturer_entry.text)
            if manufacturer_entry is not None and manufacturer_entry.text
            else expr.get('tool_vendor', ''),
            description=xml_unescape(description_entry.text)
            if description_entry is not None and description_entry.text
            else expr.get('tool_description', ''),
            product_link=xml_unescape(product_link_entry.text)
            if product_link_entry is not None and product_link_entry.text
            else '',
            material=material_name,
            coating=expr.get('tool_coating', 'none'),
            coolant_type=coolant_mode,
            overall_length=overall_length,
            shank_length=0.0,
            shank_dia=shank_dia,
            shoulder_length=shoulder_length,
            shoulder_dia=toFloat(body.get('shoulder-diameter')),
            flute_length=flute_length,
            flute_dia=toFloat(body.get('diameter')),
            tip_dia=toFloat(body.get('tip-diameter')),
            tip_length=toFloat(body.get('tip-length')),
            corner_radius=toFloat(body.get('corner-radius')),

            # keep degrees
            tip_angle=angle_val if is_tip_angle_type else 0.0,
            angle=0.0 if is_tip_angle_type else angle_val,
            thread_profile_angle=body.get('thread-profile-angle', 60),
            thread_pitch=toFloat(body.get('thread-pitch')),

            nr_flutes=int(body.get('number-of-flutes', 1)),
            thread_nr_teeth=int(body.get('number-of-teeth', 0)),
            preset_name=preset_name,
            spindle=toFloat(preset_spindle, 10000),
            feed_xy=toFloat(preset_feed_xy, 300),
            feed_z=toFloat(preset_feed_z, 100),
            feed_in=toFloat(preset_feed_in, 150),
            feed_out=toFloat(preset_feed_out, 300),
            clockwise=(motion.get('clockwise', 'yes') == 'yes'),
            protrusion=overall_length,
            tapered_type=body.get('tapered-type', 'None'),
            unit=unit,
        )

        if body_length_attr:
            tool = replace(tool, shank_length=reconstruct_shank_length(tool, body_length_attr))
        else:
            # No body-length attribute (should not normally happen) — fall back
            # to the coarse subtraction as a last resort.
            tool = replace(tool, shank_length=max(overall_length - (flute_length + shoulder_length), 0.0))

        if not tool.name and tool.description:
            tool.name = tool.description

        tools.append(tool)

    return tools


# ─── SW CSV writer helpers ────────────────────────────────────────────────────

def tapered_mill_sw_type(tool) -> "SWToolType":
    """
    Disambiguates SWToolType.TAPER_FLATEND / TAPER_BALLNOSE / TAPER_HOG_NOSE
    for a hsmlib 'tapered mill'.
    """
    tt = (tool.tapered_type or "").lower()
    if tt == "tapered_ball":
        return SWToolType.TAPER_BALLNOSE
    if tool.corner_radius and tool.corner_radius > 0:
        return SWToolType.TAPER_HOG_NOSE
    return SWToolType.TAPER_FLATEND


def resolve_sw_type(tool) -> "SWToolType":
    """
    Like convert_hsm_to_sw(), but resolves context-dependent hsmlib types
    (currently only 'tapered mill') using fields on the concrete Tool
    instance rather than the static HSM_TO_SW_MAP table.
    """
    if tool.type == HSMToolType.TAPERED_MILL.value:
        return tapered_mill_sw_type(tool)
    return convert_hsm_to_sw(HSMToolType(tool.type))


def map_coolant_to_sw(hsm_coolant_mode):
    """Map hsmlib coolant mode back to a SolidWorks 'Coolant Type' string."""
    m = (hsm_coolant_mode or '').lower()
    if m == 'flood':
        return 'Flood'
    if m == 'mist':
        return 'Mist'
    if m == 'through':
        return 'Through Tool'
    return 'Off'


def map_material_to_sw(hsm_material):
    """Map hsmlib material name back to a SolidWorks 'Tool Material' string."""
    m = (hsm_material or '').lower()
    if m == 'carbide':
        return 'Carbide'
    if m == 'hss':
        return 'HSS'
    if m == 'diamond':
        return 'Diamond'
    return 'Carbide'


def calc_sfm(spindle_rpm, diameter_mm):
    """
    Surface Feet per Minute = (RPM * Diameter[inch] * pi) / 12
    Diameter is converted from mm to inch, since SFM is an imperial unit.
    """
    if not diameter_mm or not spindle_rpm:
        return 0.0
    diameter_in = diameter_mm / 25.4
    return (spindle_rpm * diameter_in * math.pi) / 12.0


def calc_feed_per_rev(feed_xy_mm_min, spindle_rpm):
    """Feed per Revolution [mm/rev] = Feed_xy [mm/min] / Spindle_Speed [rev/min]."""
    if not spindle_rpm:
        return 0.0
    return feed_xy_mm_min / spindle_rpm


def calc_fs_default_values(tool):
    tool.spindle = tool.spindle if tool.spindle > 0 else 10000
    tool.feed_z = tool.feed_z if tool.feed_z > 0 else 100
    tool.feed_xy = tool.feed_xy if tool.feed_xy > 0 else 300
    tool.feed_in = 0.75 * tool.feed_xy
    tool.feed_out = tool.feed_xy


def calc_min_hole_dia(tool) -> float:
    min_h = round(tool.flute_dia + tool.thread_pitch * 2, 4) if tool.thread_pitch > 0 else round(tool.flute_dia * 1.2,
                                                                                                 4)
    return min_h


def hand_of_cut(tool):
    return 'Right hand' if tool.clockwise else 'Left hand'


# ─── Row-dict helpers: one helper per tool type, keys pulled from COLS_* ──────
# Each function takes (tool, row_id) and returns a dict whose keys are looked
# up by index in the corresponding COLS_* list (e.g. COLS_FLAT_END[0]), so the
# key strings never have to be retyped and can't drift out of sync with the
# column list. Insertion order follows the COLS_* order, so dict.values()
# yields the correct column order downstream.

def _row_dict_flat_end(tool, row_id):
    """For COLS_FLAT_END (SWToolType.FLAT_END_MILL)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_FLAT_END[0]: str(row_id),
        COLS_FLAT_END[1]: "true",
        COLS_FLAT_END[2]: tool.name,
        COLS_FLAT_END[3]: "1",
        COLS_FLAT_END[4]: "Rough & Finish",
        COLS_FLAT_END[5]: toStr(tool.corner_radius, True),
        COLS_FLAT_END[6]: toStr(tool.flute_dia, True),
        COLS_FLAT_END[7]: toStr(tool.flute_length, True),
        COLS_FLAT_END[8]: toStr(tool.overall_length, True),
        COLS_FLAT_END[9]: str(tool.nr_flutes),
        COLS_FLAT_END[10]: map_material_to_sw(tool.material),
        COLS_FLAT_END[11]: tool.description,
        COLS_FLAT_END[12]: toStr(tool.overall_length, True),
        COLS_FLAT_END[13]: toStr(tool.shank_dia, True),
        COLS_FLAT_END[14]: toStr(tool.shoulder_length, True),
        COLS_FLAT_END[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_FLAT_END[16]: toStr(tool.spindle),
        COLS_FLAT_END[17]: toStr(tool.feed_z),
        COLS_FLAT_END[18]: toStr(tool.feed_xy),
        COLS_FLAT_END[19]: toStr(tool.feed_in),
        COLS_FLAT_END[20]: toStr(tool.feed_out),
        COLS_FLAT_END[21]: toStr(sfm_val),
        COLS_FLAT_END[22]: toStr(fpr_val),
        COLS_FLAT_END[23]: "false",
        COLS_FLAT_END[24]: "Straight",
        COLS_FLAT_END[25]: toStr(tool.flute_length, True),
        COLS_FLAT_END[26]: toStr(tool.shoulder_dia, True),
        COLS_FLAT_END[27]: "true",
        COLS_FLAT_END[28]: tool.vendor,
        COLS_FLAT_END[29]: tool.description,
        COLS_FLAT_END[30]: hand_of_cut(tool),
    }


def _row_dict_ball_nose(tool, row_id):
    """For COLS_BALL_NOSE (SWToolType.BALL_NOSE_MILL)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_BALL_NOSE[0]: str(row_id),
        COLS_BALL_NOSE[1]: "true",
        COLS_BALL_NOSE[2]: tool.name,
        COLS_BALL_NOSE[3]: "2",
        COLS_BALL_NOSE[4]: "Rough & Finish",
        COLS_BALL_NOSE[5]: toStr(tool.corner_radius, True),
        COLS_BALL_NOSE[6]: toStr(tool.flute_dia, True),
        COLS_BALL_NOSE[7]: toStr(tool.flute_length, True),
        COLS_BALL_NOSE[8]: toStr(tool.overall_length, True),
        COLS_BALL_NOSE[9]: str(tool.nr_flutes),
        COLS_BALL_NOSE[10]: map_material_to_sw(tool.material),
        COLS_BALL_NOSE[11]: tool.description,
        COLS_BALL_NOSE[12]: toStr(tool.overall_length, True),
        COLS_BALL_NOSE[13]: toStr(tool.shank_dia, True),
        COLS_BALL_NOSE[14]: toStr(tool.shoulder_length, True),
        COLS_BALL_NOSE[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_BALL_NOSE[16]: toStr(tool.spindle),
        COLS_BALL_NOSE[17]: toStr(tool.feed_z),
        COLS_BALL_NOSE[18]: toStr(tool.feed_xy),
        COLS_BALL_NOSE[19]: toStr(tool.feed_in),
        COLS_BALL_NOSE[20]: toStr(tool.feed_out),
        COLS_BALL_NOSE[21]: toStr(sfm_val),
        COLS_BALL_NOSE[22]: toStr(fpr_val),
        COLS_BALL_NOSE[23]: "false",
        COLS_BALL_NOSE[24]: "Straight",
        COLS_BALL_NOSE[25]: toStr(tool.flute_length, True),
        COLS_BALL_NOSE[26]: toStr(tool.shoulder_dia, True),
        COLS_BALL_NOSE[27]: "true",
        COLS_BALL_NOSE[28]: tool.vendor,
        COLS_BALL_NOSE[29]: tool.description,
        COLS_BALL_NOSE[30]: hand_of_cut(tool),
    }


def _row_dict_hog_nose(tool, row_id):
    """For COLS_HOG_NOSE (SWToolType.HOG_NOSE_MILL)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_HOG_NOSE[0]: str(row_id),
        COLS_HOG_NOSE[1]: "true",
        COLS_HOG_NOSE[2]: tool.name,
        COLS_HOG_NOSE[3]: "3",
        COLS_HOG_NOSE[4]: "Rough & Finish",
        COLS_HOG_NOSE[5]: toStr(tool.corner_radius, True),
        COLS_HOG_NOSE[6]: toStr(tool.flute_dia, True),
        COLS_HOG_NOSE[7]: toStr(tool.flute_length, True),
        COLS_HOG_NOSE[8]: toStr(tool.overall_length, True),
        COLS_HOG_NOSE[9]: str(tool.nr_flutes),
        COLS_HOG_NOSE[10]: map_material_to_sw(tool.material),
        COLS_HOG_NOSE[11]: tool.description,
        COLS_HOG_NOSE[12]: toStr(tool.overall_length, True),
        COLS_HOG_NOSE[13]: toStr(tool.shank_dia, True),
        COLS_HOG_NOSE[14]: toStr(tool.shoulder_length, True),
        COLS_HOG_NOSE[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_HOG_NOSE[16]: toStr(tool.spindle),
        COLS_HOG_NOSE[17]: toStr(tool.feed_z),
        COLS_HOG_NOSE[18]: toStr(tool.feed_xy),
        COLS_HOG_NOSE[19]: toStr(tool.feed_in),
        COLS_HOG_NOSE[20]: toStr(tool.feed_out),
        COLS_HOG_NOSE[21]: toStr(sfm_val),
        COLS_HOG_NOSE[22]: toStr(fpr_val),
        COLS_HOG_NOSE[23]: "false",
        COLS_HOG_NOSE[24]: "Straight",
        COLS_HOG_NOSE[25]: toStr(tool.flute_length, True),
        COLS_HOG_NOSE[26]: toStr(tool.shoulder_dia, True),
        COLS_HOG_NOSE[27]: "true",
        COLS_HOG_NOSE[28]: tool.vendor,
        COLS_HOG_NOSE[29]: tool.description,
        COLS_HOG_NOSE[30]: hand_of_cut(tool),
    }


def _row_dict_countersink(tool, row_id):
    """For COLS_COUNTERSINK (SWToolType.COUNTERSINK)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_COUNTERSINK[0]: str(row_id),
        COLS_COUNTERSINK[1]: "true",
        COLS_COUNTERSINK[2]: tool.name,
        COLS_COUNTERSINK[3]: toStr(tool.flute_dia, True) + " X " + toStr(int(tool.angle * 2)),
        COLS_COUNTERSINK[4]: toStr(tool.flute_dia, True),
        COLS_COUNTERSINK[5]: toStr(int(tool.angle * 2)),
        COLS_COUNTERSINK[6]: toStr(tool.overall_length, True),
        COLS_COUNTERSINK[7]: str(tool.nr_flutes),
        COLS_COUNTERSINK[8]: map_material_to_sw(tool.material),
        COLS_COUNTERSINK[9]: tool.description,
        COLS_COUNTERSINK[10]: toStr(tool.overall_length, True),
        COLS_COUNTERSINK[11]: toStr(tool.shank_dia, True),
        COLS_COUNTERSINK[12]: toStr(tool.tip_dia, True) if tool.tip_dia > 0 else toStr(0.1),
        COLS_COUNTERSINK[13]: toStr(tool.shoulder_length, True),
        COLS_COUNTERSINK[14]: map_coolant_to_sw(tool.coolant_type),
        COLS_COUNTERSINK[15]: toStr(tool.spindle),
        COLS_COUNTERSINK[16]: toStr(tool.feed_z),
        COLS_COUNTERSINK[17]: toStr(sfm_val),
        COLS_COUNTERSINK[18]: toStr(fpr_val),
        COLS_COUNTERSINK[19]: "false",
        COLS_COUNTERSINK[20]: "Straight",
        COLS_COUNTERSINK[21]: toStr(tool.shoulder_length, True),
        COLS_COUNTERSINK[22]: toStr(tool.shoulder_dia, True),
        COLS_COUNTERSINK[23]: tool.vendor,
        COLS_COUNTERSINK[24]: tool.description,
        COLS_COUNTERSINK[25]: hand_of_cut(tool),
    }


def _row_dict_taper_flatend(tool, row_id):
    """For COLS_TAPER_FLATEND (SWToolType.TAPER_FLATEND). Uses 'EndRadius', not ' End Radius (R)'."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_TAPER_FLATEND[0]: str(row_id),
        COLS_TAPER_FLATEND[1]: "true",
        COLS_TAPER_FLATEND[2]: tool.name,
        COLS_TAPER_FLATEND[3]: toStr(tool.flute_dia, True),
        COLS_TAPER_FLATEND[4]: toStr(tool.corner_radius, True),
        COLS_TAPER_FLATEND[5]: toStr(tool.angle, True),
        COLS_TAPER_FLATEND[6]: toStr(tool.flute_length, True),
        COLS_TAPER_FLATEND[7]: toStr(tool.overall_length, True),
        COLS_TAPER_FLATEND[8]: str(tool.nr_flutes),
        COLS_TAPER_FLATEND[9]: map_material_to_sw(tool.material),
        COLS_TAPER_FLATEND[10]: "1",
        COLS_TAPER_FLATEND[11]: tool.description,
        COLS_TAPER_FLATEND[12]: toStr(tool.overall_length, True),
        COLS_TAPER_FLATEND[13]: toStr(tool.shank_dia, True),
        COLS_TAPER_FLATEND[14]: toStr(tool.shoulder_length, True),
        COLS_TAPER_FLATEND[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_TAPER_FLATEND[16]: toStr(tool.spindle),
        COLS_TAPER_FLATEND[17]: toStr(tool.feed_z),
        COLS_TAPER_FLATEND[18]: toStr(tool.feed_xy),
        COLS_TAPER_FLATEND[19]: toStr(tool.feed_in),
        COLS_TAPER_FLATEND[20]: toStr(tool.feed_out),
        COLS_TAPER_FLATEND[21]: toStr(sfm_val),
        COLS_TAPER_FLATEND[22]: toStr(fpr_val),
        COLS_TAPER_FLATEND[23]: "false",
        COLS_TAPER_FLATEND[24]: "Straight",
        COLS_TAPER_FLATEND[25]: toStr(tool.shoulder_length, True),
        COLS_TAPER_FLATEND[26]: toStr(tool.flute_dia, True),  # shoulder dia = flute dia for sw
        COLS_TAPER_FLATEND[27]: "true",
        COLS_TAPER_FLATEND[28]: tool.vendor,
        COLS_TAPER_FLATEND[29]: tool.description,
        COLS_TAPER_FLATEND[30]: hand_of_cut(tool),
    }


def _row_dict_taper_ballnose(tool, row_id):
    """For COLS_TAPER_BALLNOSE (SWToolType.TAPER_BALLNOSE)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_TAPER_BALLNOSE[0]: str(row_id),
        COLS_TAPER_BALLNOSE[1]: "true",
        COLS_TAPER_BALLNOSE[2]: tool.name,
        COLS_TAPER_BALLNOSE[3]: toStr(tool.flute_dia, True),
        COLS_TAPER_BALLNOSE[4]: toStr(tool.corner_radius, True),
        COLS_TAPER_BALLNOSE[5]: toStr(tool.angle, True),
        COLS_TAPER_BALLNOSE[6]: toStr(tool.flute_length, True),
        COLS_TAPER_BALLNOSE[7]: toStr(tool.overall_length, True),
        COLS_TAPER_BALLNOSE[8]: str(tool.nr_flutes),
        COLS_TAPER_BALLNOSE[9]: map_material_to_sw(tool.material),
        COLS_TAPER_BALLNOSE[10]: "2",
        COLS_TAPER_BALLNOSE[11]: tool.description,
        COLS_TAPER_BALLNOSE[12]: toStr(tool.overall_length, True),
        COLS_TAPER_BALLNOSE[13]: toStr(tool.shank_dia, True),
        COLS_TAPER_BALLNOSE[14]: toStr(tool.shoulder_length, True),
        COLS_TAPER_BALLNOSE[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_TAPER_BALLNOSE[16]: toStr(tool.spindle),
        COLS_TAPER_BALLNOSE[17]: toStr(tool.feed_z),
        COLS_TAPER_BALLNOSE[18]: toStr(tool.feed_xy),
        COLS_TAPER_BALLNOSE[19]: toStr(tool.feed_in),
        COLS_TAPER_BALLNOSE[20]: toStr(tool.feed_out),
        COLS_TAPER_BALLNOSE[21]: toStr(sfm_val),
        COLS_TAPER_BALLNOSE[22]: toStr(fpr_val),
        COLS_TAPER_BALLNOSE[23]: "false",
        COLS_TAPER_BALLNOSE[24]: "Straight",
        COLS_TAPER_BALLNOSE[25]: toStr(tool.shoulder_length, True),
        COLS_TAPER_BALLNOSE[26]: toStr(tool.flute_dia, True),  # shoulder dia = flute dia for sw
        COLS_TAPER_BALLNOSE[27]: "true",
        COLS_TAPER_BALLNOSE[28]: tool.vendor,
        COLS_TAPER_BALLNOSE[29]: tool.description,
        COLS_TAPER_BALLNOSE[30]: hand_of_cut(tool),
    }


def _row_dict_taper_hog_nose(tool, row_id):
    """For COLS_TAPER_HOG_NOSE (SWToolType.TAPER_HOG_NOSE)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_TAPER_HOG_NOSE[0]: str(row_id),
        COLS_TAPER_HOG_NOSE[1]: "true",
        COLS_TAPER_HOG_NOSE[2]: tool.name,
        COLS_TAPER_HOG_NOSE[3]: toStr(tool.flute_dia, True),
        COLS_TAPER_HOG_NOSE[4]: toStr(tool.corner_radius, True),
        COLS_TAPER_HOG_NOSE[5]: toStr(tool.angle, True),
        COLS_TAPER_HOG_NOSE[6]: toStr(tool.flute_length, True),
        COLS_TAPER_HOG_NOSE[7]: toStr(tool.overall_length, True),
        COLS_TAPER_HOG_NOSE[8]: str(tool.nr_flutes),
        COLS_TAPER_HOG_NOSE[9]: map_material_to_sw(tool.material),
        COLS_TAPER_HOG_NOSE[10]: "3",
        COLS_TAPER_HOG_NOSE[11]: tool.description,
        COLS_TAPER_HOG_NOSE[12]: toStr(tool.overall_length, True),
        COLS_TAPER_HOG_NOSE[13]: toStr(tool.shank_dia, True),
        COLS_TAPER_HOG_NOSE[14]: toStr(tool.shoulder_length, True),
        COLS_TAPER_HOG_NOSE[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_TAPER_HOG_NOSE[16]: toStr(tool.spindle),
        COLS_TAPER_HOG_NOSE[17]: toStr(tool.feed_z),
        COLS_TAPER_HOG_NOSE[18]: toStr(tool.feed_xy),
        COLS_TAPER_HOG_NOSE[19]: toStr(tool.feed_in),
        COLS_TAPER_HOG_NOSE[20]: toStr(tool.feed_out),
        COLS_TAPER_HOG_NOSE[21]: toStr(sfm_val),
        COLS_TAPER_HOG_NOSE[22]: toStr(fpr_val),
        COLS_TAPER_HOG_NOSE[23]: "false",
        COLS_TAPER_HOG_NOSE[24]: "Straight",
        COLS_TAPER_HOG_NOSE[25]: toStr(tool.shoulder_length, True),
        COLS_TAPER_HOG_NOSE[26]: toStr(tool.flute_dia, True),  # shoulder dia = flute dia for sw
        COLS_TAPER_HOG_NOSE[27]: "true",
        COLS_TAPER_HOG_NOSE[28]: tool.vendor,
        COLS_TAPER_HOG_NOSE[29]: tool.description,
        COLS_TAPER_HOG_NOSE[30]: hand_of_cut(tool),
    }


def _row_dict_thread_multi(tool, row_id):
    """For COLS_THREAD_MULTI (SWToolType.THREAD_MULTI)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_THREAD_MULTI[0]: str(row_id),
        COLS_THREAD_MULTI[1]: "true",
        COLS_THREAD_MULTI[2]: toStr(tool.flute_dia, True),
        COLS_THREAD_MULTI[3]: toStr(calc_min_hole_dia(tool), decimals=2),
        COLS_THREAD_MULTI[4]: toStr(tool.thread_pitch, True),
        COLS_THREAD_MULTI[5]: toStr(tool.overall_length, True),
        COLS_THREAD_MULTI[6]: "0",  # Ineff. Length (L5)
        COLS_THREAD_MULTI[7]: toStr(tool.flute_length),  # Flute Length (L2)
        COLS_THREAD_MULTI[8]: toStr(tool.thread_profile_angle, True),
        COLS_THREAD_MULTI[9]: toStr(tool.thread_profile_angle, True),
        COLS_THREAD_MULTI[10]: str(tool.nr_flutes),
        COLS_THREAD_MULTI[11]: map_material_to_sw(tool.material),
        COLS_THREAD_MULTI[12]: tool.description,
        COLS_THREAD_MULTI[13]: toStr(tool.overall_length, True),
        COLS_THREAD_MULTI[14]: toStr(tool.shank_dia, True),
        COLS_THREAD_MULTI[15]: toStr(tool.shoulder_length, True),
        COLS_THREAD_MULTI[16]: map_coolant_to_sw(tool.coolant_type),
        COLS_THREAD_MULTI[17]: toStr(tool.spindle),
        COLS_THREAD_MULTI[18]: toStr(tool.feed_z),
        COLS_THREAD_MULTI[19]: toStr(tool.feed_xy),
        COLS_THREAD_MULTI[20]: toStr(tool.feed_in),
        COLS_THREAD_MULTI[21]: toStr(tool.feed_out),
        COLS_THREAD_MULTI[22]: toStr(sfm_val),
        COLS_THREAD_MULTI[23]: toStr(fpr_val),
        COLS_THREAD_MULTI[24]: "false",
        COLS_THREAD_MULTI[25]: "Straight",
        COLS_THREAD_MULTI[26]: toStr(tool.flute_length, True),  # Shank Length (L6) ~= Flute Length (L2)
        COLS_THREAD_MULTI[27]: toStr(tool.shoulder_dia, True),
        COLS_THREAD_MULTI[28]: tool.vendor,
        COLS_THREAD_MULTI[29]: tool.description,
        COLS_THREAD_MULTI[30]: tool.name,
        COLS_THREAD_MULTI[31]: hand_of_cut(tool),
    }


def _row_dict_thread_single(tool, row_id):
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_THREAD_SINGLE[0]: str(row_id),
        COLS_THREAD_SINGLE[1]: "true",
        COLS_THREAD_SINGLE[2]: toStr(tool.flute_dia),
        COLS_THREAD_SINGLE[3]: toStr(calc_min_hole_dia(tool), decimals=2),
        COLS_THREAD_SINGLE[4]: toStr(tool.overall_length),

        # SW-specific field, not hsmlib shoulder_length.
        COLS_THREAD_SINGLE[5]: "0",

        # Actual axial cutting/profile width.
        COLS_THREAD_SINGLE[6]: toStr(tool.flute_length),

        COLS_THREAD_SINGLE[7]: toStr(tool.thread_profile_angle),
        COLS_THREAD_SINGLE[8]: str(tool.nr_flutes),
        COLS_THREAD_SINGLE[9]: map_material_to_sw(tool.material),
        COLS_THREAD_SINGLE[10]: tool.description,
        COLS_THREAD_SINGLE[11]: toStr(tool.overall_length, True),
        COLS_THREAD_SINGLE[12]: toStr(tool.shank_dia, True),
        COLS_THREAD_SINGLE[13]: map_coolant_to_sw(tool.coolant_type),
        COLS_THREAD_SINGLE[14]: toStr(tool.spindle),
        COLS_THREAD_SINGLE[15]: toStr(tool.feed_z),
        COLS_THREAD_SINGLE[16]: toStr(tool.feed_xy),
        COLS_THREAD_SINGLE[17]: toStr(tool.feed_in),
        COLS_THREAD_SINGLE[18]: toStr(tool.feed_out),
        COLS_THREAD_SINGLE[19]: toStr(sfm_val),
        COLS_THREAD_SINGLE[20]: toStr(fpr_val),
        COLS_THREAD_SINGLE[21]: "false",
        COLS_THREAD_SINGLE[22]: "Straight",

        # SW-specific generated/default value for SinglePt.
        COLS_THREAD_SINGLE[23]: "1",

        # For SinglePt this is the reduced diameter behind the thread form,
        # not the nominal thread/cutting diameter.
        COLS_THREAD_SINGLE[24]: toStr(tool.shoulder_dia, True),

        COLS_THREAD_SINGLE[25]: tool.vendor,
        COLS_THREAD_SINGLE[26]: tool.description,
        COLS_THREAD_SINGLE[27]: tool.name,
        COLS_THREAD_SINGLE[28]: hand_of_cut(tool),
    }


def _row_dict_drills(tool, row_id):
    """For COLS_DRILLS (SWToolType.DRILLS)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_DRILLS[0]: str(row_id),
        COLS_DRILLS[1]: "true",
        COLS_DRILLS[2]: tool.name,
        COLS_DRILLS[3]: drill_fraction_or_no(tool),
        COLS_DRILLS[4]: toStr(tool.flute_dia, True),
        COLS_DRILLS[5]: toStr(tool.flute_length, True),
        COLS_DRILLS[6]: toStr(tool.overall_length, True),
        COLS_DRILLS[7]: str(tool.nr_flutes),
        COLS_DRILLS[8]: toStr(tool.tip_angle, True),
        COLS_DRILLS[9]: toStr(calc_tip_length(tool.flute_dia, tool.tip_angle / 2), True),
        COLS_DRILLS[10]: map_material_to_sw(tool.material),
        COLS_DRILLS[11]: tool.description,
        COLS_DRILLS[12]: toStr(tool.overall_length, True),
        COLS_DRILLS[13]: toStr(tool.shank_dia, True),
        COLS_DRILLS[14]: "1",
        COLS_DRILLS[15]: toStr(tool.shoulder_length, True),
        COLS_DRILLS[16]: map_coolant_to_sw(tool.coolant_type),
        COLS_DRILLS[17]: toStr(tool.spindle, True),
        COLS_DRILLS[18]: toStr(tool.feed_z, True),
        COLS_DRILLS[19]: toStr(tool.feed_xy, True),
        COLS_DRILLS[20]: toStr(tool.feed_in, True),
        COLS_DRILLS[21]: toStr(tool.feed_out, True),
        COLS_DRILLS[22]: toStr(sfm_val, True),
        COLS_DRILLS[23]: toStr(fpr_val, True),
        COLS_DRILLS[24]: "false",
        COLS_DRILLS[25]: "Straight",
        COLS_DRILLS[26]: toStr(tool.shoulder_length, True),
        COLS_DRILLS[27]: toStr(tool.shoulder_dia, True),
        COLS_DRILLS[28]: tool.vendor,
        COLS_DRILLS[29]: tool.description,
        COLS_DRILLS[30]: hand_of_cut(tool),
    }


def _row_dict_face_mill(tool, row_id):
    """For COLS_FACE_MILL (SWToolType.FACE_MILL). This list has no HandOfCutID column."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_FACE_MILL[0]: str(row_id),
        COLS_FACE_MILL[1]: "true",
        COLS_FACE_MILL[2]: tool.name,
        COLS_FACE_MILL[3]: toStr(tool.flute_dia, True),
        COLS_FACE_MILL[4]: toStr(tool.flute_dia, True),
        COLS_FACE_MILL[5]: toStr(tool.shank_dia, True),
        COLS_FACE_MILL[6]: toStr(tool.flute_length, True),
        COLS_FACE_MILL[7]: toStr(tool.overall_length, True),
        COLS_FACE_MILL[8]: toStr(tool.shoulder_length, True),
        COLS_FACE_MILL[9]: toStr(tool.overall_length, True),
        COLS_FACE_MILL[10]: hand_of_cut(tool),
        COLS_FACE_MILL[11]: str(tool.nr_flutes),
        COLS_FACE_MILL[12]: map_material_to_sw(tool.material),
        COLS_FACE_MILL[13]: tool.description,
        COLS_FACE_MILL[14]: map_coolant_to_sw(tool.coolant_type),
        COLS_FACE_MILL[15]: toStr(tool.spindle),
        COLS_FACE_MILL[16]: toStr(tool.feed_z),
        COLS_FACE_MILL[17]: toStr(tool.feed_xy),
        COLS_FACE_MILL[18]: toStr(tool.feed_in),
        COLS_FACE_MILL[19]: toStr(tool.feed_out),
        COLS_FACE_MILL[20]: toStr(sfm_val),
        COLS_FACE_MILL[21]: toStr(fpr_val),
        COLS_FACE_MILL[22]: "false",
        COLS_FACE_MILL[23]: "Straight",
        COLS_FACE_MILL[24]: toStr(tool.shank_length, True),
        COLS_FACE_MILL[25]: toStr(tool.shoulder_dia, True),
        COLS_FACE_MILL[26]: "true",
        COLS_FACE_MILL[27]: tool.vendor,
        COLS_FACE_MILL[28]: tool.description,
    }


def _row_dict_center_drill(tool, row_id):
    """For COLS_CENTER_DRILL (SWToolType.CENTER_DRILL)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_CENTER_DRILL[0]: str(row_id),
        COLS_CENTER_DRILL[1]: "true",
        COLS_CENTER_DRILL[2]: tool.name,
        COLS_CENTER_DRILL[3]: toStr(tool.flute_dia, True) + " X " + toStr(tool.flute_length, decimals=1),
        COLS_CENTER_DRILL[4]: toStr(tool.shank_dia, True),
        COLS_CENTER_DRILL[5]: toStr(tool.flute_dia, True),
        COLS_CENTER_DRILL[6]: toStr(tool.tip_angle, True),
        COLS_CENTER_DRILL[7]: toStr(tool.tip_angle, True),
        COLS_CENTER_DRILL[8]: toStr(tool.flute_length, True),
        COLS_CENTER_DRILL[9]: toStr(tool.overall_length, True),
        COLS_CENTER_DRILL[10]: str(tool.nr_flutes),
        COLS_CENTER_DRILL[11]: map_material_to_sw(tool.material),
        COLS_CENTER_DRILL[12]: tool.description,
        COLS_CENTER_DRILL[13]: toStr(tool.overall_length, True),
        COLS_CENTER_DRILL[14]: map_coolant_to_sw(tool.coolant_type),
        COLS_CENTER_DRILL[15]: toStr(tool.spindle),
        COLS_CENTER_DRILL[16]: toStr(tool.feed_z),
        COLS_CENTER_DRILL[17]: toStr(sfm_val),
        COLS_CENTER_DRILL[18]: toStr(fpr_val),
        COLS_CENTER_DRILL[19]: "false",
        COLS_CENTER_DRILL[20]: "Straight",
        COLS_CENTER_DRILL[21]: toStr(tool.shoulder_length, True),
        COLS_CENTER_DRILL[22]: toStr(tool.flute_dia, True),
        COLS_CENTER_DRILL[23]: tool.vendor,
        COLS_CENTER_DRILL[24]: tool.description,
        COLS_CENTER_DRILL[25]: toStr(tool.shoulder_length),
        COLS_CENTER_DRILL[26]: hand_of_cut(tool),
    }


def _row_dict_corner_rounding(tool, row_id):
    """For COLS_CORNER_ROUNDING (SWToolType.CORNER_ROUNDING)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    total_flute_length = tool.corner_radius + tool.tip_length
    return {
        COLS_CORNER_ROUNDING[0]: str(row_id),
        COLS_CORNER_ROUNDING[1]: "true",
        COLS_CORNER_ROUNDING[2]: tool.name,
        COLS_CORNER_ROUNDING[3]: toStr(tool.corner_radius, True),
        COLS_CORNER_ROUNDING[4]: toStr(tool.flute_dia, True),
        COLS_CORNER_ROUNDING[5]: toStr(tool.taper_dia, True) if tool.taper_dia else toStr(tool.flute_dia, True),
        COLS_CORNER_ROUNDING[6]: toStr(tool.shank_dia, True),
        COLS_CORNER_ROUNDING[7]: toStr(total_flute_length, True),
        COLS_CORNER_ROUNDING[8]: toStr(tool.overall_length, True),
        COLS_CORNER_ROUNDING[9]: toStr(tool.shoulder_length, True),  # Body Length (L5)
        COLS_CORNER_ROUNDING[10]: str(tool.nr_flutes),
        COLS_CORNER_ROUNDING[11]: map_material_to_sw(tool.material),
        COLS_CORNER_ROUNDING[12]: tool.description,
        COLS_CORNER_ROUNDING[13]: toStr(tool.overall_length, True),
        COLS_CORNER_ROUNDING[14]: "Tip",  # Output — SW constant observed in every sampled row
        COLS_CORNER_ROUNDING[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_CORNER_ROUNDING[16]: toStr(tool.spindle),
        COLS_CORNER_ROUNDING[17]: toStr(tool.feed_z),
        COLS_CORNER_ROUNDING[18]: toStr(tool.feed_xy),
        COLS_CORNER_ROUNDING[19]: toStr(tool.feed_in),
        COLS_CORNER_ROUNDING[20]: toStr(tool.feed_out),
        COLS_CORNER_ROUNDING[21]: toStr(sfm_val),
        COLS_CORNER_ROUNDING[22]: toStr(fpr_val),
        COLS_CORNER_ROUNDING[23]: "false",
        COLS_CORNER_ROUNDING[24]: "Straight",
        COLS_CORNER_ROUNDING[25]: "1",  # Shank Length (L6) — SW constant, no real shoulder geometry
        COLS_CORNER_ROUNDING[26]: toStr(tool.flute_dia),  # Shoulder Dia (D4) == End Dia. (D1)
        COLS_CORNER_ROUNDING[27]: "true",
        COLS_CORNER_ROUNDING[28]: tool.vendor,
        COLS_CORNER_ROUNDING[29]: tool.description,
        COLS_CORNER_ROUNDING[30]: hand_of_cut(tool),
    }


def _row_dict_dovetail(tool, row_id):
    """For COLS_DOVETAIL (SWToolType.DOVETAIL)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_DOVETAIL[0]: str(row_id),
        COLS_DOVETAIL[1]: "true",
        COLS_DOVETAIL[2]: tool.name,
        COLS_DOVETAIL[3]: toStr(tool.flute_dia, True),
        COLS_DOVETAIL[4]: toStr(tool.shank_dia, True),
        COLS_DOVETAIL[5]: toStr(tool.corner_radius, True),
        COLS_DOVETAIL[6]: toStr(tool.angle, True),
        COLS_DOVETAIL[7]: toStr(tool.overall_length, True),
        COLS_DOVETAIL[8]: str(tool.nr_flutes),
        COLS_DOVETAIL[9]: map_material_to_sw(tool.material),
        COLS_DOVETAIL[10]: tool.description,
        COLS_DOVETAIL[11]: toStr(tool.overall_length, True),
        COLS_DOVETAIL[12]: map_coolant_to_sw(tool.coolant_type),
        COLS_DOVETAIL[13]: toStr(tool.spindle),
        COLS_DOVETAIL[14]: toStr(tool.feed_z),
        COLS_DOVETAIL[15]: toStr(tool.feed_xy),
        COLS_DOVETAIL[16]: toStr(tool.feed_in),
        COLS_DOVETAIL[17]: toStr(tool.feed_out),
        COLS_DOVETAIL[18]: toStr(sfm_val),
        COLS_DOVETAIL[19]: toStr(fpr_val),
        COLS_DOVETAIL[20]: "false",
        COLS_DOVETAIL[21]: "Straight",
        COLS_DOVETAIL[22]: "1",  # Shank Length (L6) — SW constant, observed in every sampled row
        COLS_DOVETAIL[23]: toStr(tool.flute_dia, True),  # Shoulder Dia (D4) == Diameter (D1)
        COLS_DOVETAIL[24]: "true",
        COLS_DOVETAIL[25]: tool.vendor,
        COLS_DOVETAIL[26]: tool.description,
        COLS_DOVETAIL[27]: "10",  # Shoulder Length (L4) — SW constant, observed in every sampled row
        COLS_DOVETAIL[28]: hand_of_cut(tool),
    }


def _row_dict_keyway(tool, row_id):
    """For COLS_KEYWAY (SWToolType.KEYWAY)."""
    tool.spindle = tool.spindle if tool.spindle > 0 else 10000
    tool.feed_z = tool.feed_z if tool.feed_z > 0 else 100
    tool.feed_xy = tool.feed_xy if tool.feed_xy > 0 else 300

    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)
    return {
        COLS_KEYWAY[0]: str(row_id),
        COLS_KEYWAY[1]: "true",
        COLS_KEYWAY[2]: tool.name,
        COLS_KEYWAY[3]: toStr(tool.flute_dia, True),
        COLS_KEYWAY[4]: toStr(tool.shank_dia, True),
        COLS_KEYWAY[5]: toStr(tool.corner_radius, True),  # Bottom Radius (R1)
        COLS_KEYWAY[6]: toStr(tool.corner_radius, True),  # Top Radius (R2) — same radius unless a second is tracked
        COLS_KEYWAY[7]: toStr(tool.flute_length, True),
        COLS_KEYWAY[8]: toStr(tool.overall_length, True),
        COLS_KEYWAY[9]: str(tool.nr_flutes),
        COLS_KEYWAY[10]: map_material_to_sw(tool.material),
        COLS_KEYWAY[11]: tool.description,
        COLS_KEYWAY[12]: toStr(tool.overall_length, True),
        COLS_KEYWAY[13]: map_coolant_to_sw(tool.coolant_type),
        COLS_KEYWAY[14]: toStr(tool.spindle),
        COLS_KEYWAY[15]: toStr(tool.feed_z),
        COLS_KEYWAY[16]: toStr(tool.feed_xy),
        COLS_KEYWAY[17]: toStr(tool.feed_in),
        COLS_KEYWAY[18]: toStr(tool.feed_out),
        COLS_KEYWAY[19]: toStr(sfm_val),
        COLS_KEYWAY[20]: toStr(fpr_val),
        COLS_KEYWAY[21]: "false",
        COLS_KEYWAY[22]: "Straight",
        COLS_KEYWAY[23]: "1",  # Shank Length (L6) — SW constant, observed in every sampled row
        COLS_KEYWAY[24]: toStr(tool.flute_dia, True),  # Shoulder Dia (D4) == Diameter (D1)
        COLS_KEYWAY[25]: "true",
        COLS_KEYWAY[26]: tool.vendor,
        COLS_KEYWAY[27]: tool.description,
        COLS_KEYWAY[28]: "10",  # Shoulder Length (L4) — SW constant, observed in every sampled row
        COLS_KEYWAY[29]: hand_of_cut(tool),
    }


def _row_dict_lollipop(tool, row_id):
    """
    For COLS_LOLLIPOP (SWToolType.LOLLIPOP).
    Shoulder Length (L4) and Shank Length (L6) are both derived from the ball-head
    spherical-cap geometry, not read from the Tool object directly.
    """
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    shoulder_len = lollipop_shoulder_length(tool.flute_dia, tool.shank_dia)
    return {
        COLS_LOLLIPOP[0]: str(row_id),
        COLS_LOLLIPOP[1]: "true",
        COLS_LOLLIPOP[2]: tool.name,
        COLS_LOLLIPOP[3]: toStr(tool.flute_dia, True),
        COLS_LOLLIPOP[4]: toStr(tool.shank_dia, True),
        COLS_LOLLIPOP[5]: toStr(shoulder_len, True),  # Shoulder Length (L4), derived
        COLS_LOLLIPOP[6]: toStr(tool.flute_length, True),
        COLS_LOLLIPOP[7]: toStr(tool.overall_length, True),
        COLS_LOLLIPOP[8]: toStr(int(tool.overall_length), True),  # Protrusion (L3)
        COLS_LOLLIPOP[9]: str(tool.nr_flutes),
        COLS_LOLLIPOP[10]: map_material_to_sw(tool.material),
        COLS_LOLLIPOP[11]: tool.description,
        COLS_LOLLIPOP[12]: map_coolant_to_sw(tool.coolant_type),
        COLS_LOLLIPOP[13]: toStr(tool.spindle),
        COLS_LOLLIPOP[14]: toStr(tool.feed_z),
        COLS_LOLLIPOP[15]: toStr(tool.feed_xy),
        COLS_LOLLIPOP[16]: toStr(tool.feed_in),
        COLS_LOLLIPOP[17]: toStr(tool.feed_out),
        COLS_LOLLIPOP[18]: toStr(sfm_val),
        COLS_LOLLIPOP[19]: toStr(fpr_val),
        COLS_LOLLIPOP[20]: "false",
        COLS_LOLLIPOP[21]: "Straight",
        COLS_LOLLIPOP[22]: toStr(shoulder_len, decimals=6),  # Shank Length (L6) == Shoulder Length (L4)
        COLS_LOLLIPOP[23]: toStr(tool.flute_dia, True),
        COLS_LOLLIPOP[24]: tool.vendor,
        COLS_LOLLIPOP[25]: tool.description,
        COLS_LOLLIPOP[26]: hand_of_cut(tool),
    }


def _row_dict_bores(tool, row_id):
    """For COLS_BORES (SWToolType.BORES)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_BORES[0]: str(row_id),
        COLS_BORES[1]: "true",
        COLS_BORES[2]: tool.name,
        COLS_BORES[3]: toStr(tool.flute_dia, True),
        COLS_BORES[4]: "",
        COLS_BORES[5]: "",
        COLS_BORES[6]: toStr(tool.flute_length, True),
        COLS_BORES[7]: toStr(tool.overall_length, True),
        COLS_BORES[8]: toStr(tool.shoulder_length, True),
        COLS_BORES[9]: map_material_to_sw(tool.material),
        COLS_BORES[10]: "",
        COLS_BORES[11]: tool.description,
        COLS_BORES[12]: toStr(tool.overall_length, True),
        COLS_BORES[13]: toStr(tool.shank_dia, True),
        COLS_BORES[14]: toStr(tool.shoulder_length, True),
        COLS_BORES[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_BORES[16]: toStr(tool.spindle),
        COLS_BORES[17]: toStr(tool.feed_z),
        COLS_BORES[18]: toStr(sfm_val),
        COLS_BORES[19]: toStr(fpr_val),
        COLS_BORES[20]: "false",
        COLS_BORES[21]: "Straight",
        COLS_BORES[22]: toStr(tool.shank_length, True),
        COLS_BORES[23]: toStr(tool.shoulder_dia, True),
        COLS_BORES[24]: tool.vendor,
        COLS_BORES[25]: tool.description,
        COLS_BORES[26]: hand_of_cut(tool),
    }


def _row_dict_reamer(tool, row_id):
    """For COLS_REAMERS (SWToolType.REAMER)."""
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_REAMERS[0]: str(row_id),
        COLS_REAMERS[1]: "true",
        COLS_REAMERS[2]: tool.name,
        COLS_REAMERS[3]: toStr(tool.flute_dia, True),
        COLS_REAMERS[4]: toStr(tool.flute_dia, True),
        COLS_REAMERS[5]: toStr(tool.flute_length, True),
        COLS_REAMERS[6]: toStr(tool.overall_length, True),
        COLS_REAMERS[7]: str(tool.nr_flutes),
        COLS_REAMERS[8]: "0",
        COLS_REAMERS[9]: map_material_to_sw(tool.material),
        COLS_REAMERS[10]: "0",
        COLS_REAMERS[11]: tool.description,
        COLS_REAMERS[12]: toStr(tool.overall_length, True),
        COLS_REAMERS[13]: toStr(tool.shank_dia, True),
        COLS_REAMERS[14]: toStr(tool.flute_length, True),  # shoulder length = flute length
        COLS_REAMERS[15]: map_coolant_to_sw(tool.coolant_type),
        COLS_REAMERS[16]: toStr(tool.spindle),
        COLS_REAMERS[17]: toStr(tool.feed_z),
        COLS_REAMERS[18]: toStr(sfm_val),
        COLS_REAMERS[19]: toStr(fpr_val),
        COLS_REAMERS[20]: "false",
        COLS_REAMERS[21]: "Straight",
        COLS_REAMERS[22]: toStr(tool.flute_length, True),  # shank length = flute length
        COLS_REAMERS[23]: toStr(tool.flute_dia, True),
        COLS_REAMERS[24]: tool.vendor,
        COLS_REAMERS[25]: tool.description,
        COLS_REAMERS[26]: "true",
        COLS_REAMERS[27]: hand_of_cut(tool),
    }


def _row_dict_tap(tool, row_id):
    """
    For COLS_TAPS (SWToolType.TAPS_LH / SWToolType.TAPS_RH).
    Both hsmlib types "tap right hand" and "tap left hand" map to the same
    SolidWorks tool type string "nTaps" and therefore land in the same CSV
    file. The hand of cut is not encoded in the filename or tool type, but
    purely in the "HandOfCutID" column via tool.clockwise.
    """
    calc_fs_default_values(tool)
    sfm_val = calc_sfm(tool.spindle, tool.flute_dia)
    fpr_val = calc_feed_per_rev(tool.feed_xy, tool.spindle)

    return {
        COLS_TAPS[0]: str(row_id),
        COLS_TAPS[1]: "true",
        COLS_TAPS[2]: _taps_thread_type(tool),
        COLS_TAPS[3]: toStr(tool.flute_dia, True) + " X " + toStr(tool.thread_pitch, decimals=1),
        COLS_TAPS[4]: toStr(tool.flute_dia, True),
        COLS_TAPS[5]: toStr(tool.thread_pitch, True),
        COLS_TAPS[6]: toStr(tool.flute_dia, True),
        COLS_TAPS[7]: toStr(tool.flute_dia, True),
        COLS_TAPS[8]: "0",
        COLS_TAPS[9]: toStr(tool.overall_length, True),
        COLS_TAPS[10]: map_material_to_sw(tool.material),
        COLS_TAPS[11]: tool.description,
        COLS_TAPS[12]: tool.description,
        COLS_TAPS[13]: toStr(tool.overall_length, True),
        COLS_TAPS[14]: toStr(tool.shank_dia, True),
        COLS_TAPS[15]: "0",
        COLS_TAPS[16]: "1000",
        COLS_TAPS[17]: "1",
        COLS_TAPS[18]: toStr(tool.flute_length, True),
        COLS_TAPS[19]: toStr(tool.flute_length, True),
        COLS_TAPS[20]: "",
        COLS_TAPS[21]: map_coolant_to_sw(tool.coolant_type),
        COLS_TAPS[22]: toStr(tool.spindle),
        COLS_TAPS[23]: toStr(tool.feed_z),
        COLS_TAPS[24]: toStr(tool.feed_xy),
        COLS_TAPS[25]: toStr(tool.feed_in),
        COLS_TAPS[26]: toStr(tool.feed_out),
        COLS_TAPS[27]: "10000",
        COLS_TAPS[28]: toStr(sfm_val),
        COLS_TAPS[29]: toStr(fpr_val),
        COLS_TAPS[30]: "false",
        COLS_TAPS[31]: "Straight",
        COLS_TAPS[32]: "1",
        COLS_TAPS[33]: "0.5",
        COLS_TAPS[34]: tool.vendor,
        COLS_TAPS[35]: tool.description,
        COLS_TAPS[36]: tool.vendor,
        COLS_TAPS[37]: tool.description,
        COLS_TAPS[38]: tool.name,
        COLS_TAPS[39]: "",
        COLS_TAPS[40]: hand_of_cut(tool),
    }


# ─── Dispatch table: SWToolType -> (row_dict_builder, COLS_* list) ───────────

ROW_BUILDERS = {
    SWToolType.FLAT_END_MILL: (_row_dict_flat_end, COLS_FLAT_END),
    SWToolType.BALL_NOSE_MILL: (_row_dict_ball_nose, COLS_BALL_NOSE),
    SWToolType.HOG_NOSE_MILL: (_row_dict_hog_nose, COLS_HOG_NOSE),
    SWToolType.COUNTERSINK: (_row_dict_countersink, COLS_COUNTERSINK),
    SWToolType.TAPER_FLATEND: (_row_dict_taper_flatend, COLS_TAPER_FLATEND),
    SWToolType.TAPER_BALLNOSE: (_row_dict_taper_ballnose, COLS_TAPER_BALLNOSE),
    SWToolType.TAPER_HOG_NOSE: (_row_dict_taper_hog_nose, COLS_TAPER_HOG_NOSE),
    SWToolType.THREAD_SINGLE: (_row_dict_thread_single, COLS_THREAD_SINGLE),
    SWToolType.THREAD_MULTI: (_row_dict_thread_multi, COLS_THREAD_MULTI),
    SWToolType.DRILLS: (_row_dict_drills, COLS_DRILLS),
    SWToolType.FACE_MILL: (_row_dict_face_mill, COLS_FACE_MILL),
    SWToolType.CENTER_DRILL: (_row_dict_center_drill, COLS_CENTER_DRILL),
    SWToolType.LOLLIPOP: (_row_dict_lollipop, COLS_LOLLIPOP),
    SWToolType.BORES: (_row_dict_bores, COLS_BORES),
    SWToolType.CORNER_ROUNDING: (_row_dict_corner_rounding, COLS_CORNER_ROUNDING),
    SWToolType.DOVETAIL: (_row_dict_dovetail, COLS_DOVETAIL),
    SWToolType.REAMERS: (_row_dict_reamer, COLS_REAMERS),
    SWToolType.TAPS_RH: (_row_dict_tap, COLS_TAPS),
    SWToolType.TAPS_LH: (_row_dict_tap, COLS_TAPS),
}


def normalize_sw_unit(unit: str | None) -> str:
    """
    Converts hsmlib Tool.unit variants into the exact unit strings expected
    by SolidWorks CSV file-info row 3 and the output filename convention.

    hsmlib usually provides:
      - "inches"
      - "millimeters"

    SolidWorks CSV uses:
      - "inches"
      - "metric"
    """
    normalized = (unit or "millimeters").strip().lower()

    if normalized in ("inch", "inches", "in"):
        return "inches"

    if normalized in ("millimeter", "millimeters", "millimetres", "mm", "metric"):
        return "metric"

    print(f"⚠️ Unknown tool unit {unit!r}; exporting as metric.")
    return "metric"


def write_csv(tools_by_type, output_dir, base_name):
    """
    Writes one SolidWorks CAM CSV per combination of:

      1. SolidWorks tool type
      2. tool unit: metric or inches

    SolidWorks rejects CSV files that mix metric and inch tools. An hsmlib
    library may contain both unit="millimeters" and unit="inches" tools,
    so each SWToolType bucket is split again by Tool.unit before writing.

    Output names:
      <base_name>_<SWToolType>_(metric)_en.csv
      <base_name>_<SWToolType>_(inches)_en.csv

    The unit written in CSV line 3 matches the filename suffix:
      ,MILLC,metric,English
      ,MILLC,inches,English
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for sw_type, tools in tools_by_type.items():
        builder_entry = ROW_BUILDERS.get(sw_type)
        if not builder_entry or not tools:
            continue

        row_dict_builder, columns = builder_entry

        # Important: one hsmlib library can contain tools with both
        # unit="inches" and unit="millimeters"; never write those into the
        # same SolidWorks CSV.
        tools_by_unit = {}

        for tool in tools:
            sw_unit = normalize_sw_unit(getattr(tool, "unit", "millimeters"))
            tools_by_unit.setdefault(sw_unit, []).append(tool)

        # Deterministic order: metric first, then inches.
        for sw_unit in ("metric", "inches"):
            unit_tools = tools_by_unit.get(sw_unit, [])
            if not unit_tools:
                continue

            out_path = output_dir / (
                f"{base_name}_{sw_type.value}_({sw_unit})_en.csv"
            )

            with out_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, lineterminator="\n")

                # make_header() writes lines 1-8; `sw_unit` is used on
                # line 3: ",<tool-name>,metric|inches,English".
                f.write(make_header(sw_type, sw_unit))

                # Row 9 and all data rows.
                writer.writerow(columns)

                # Row IDs are local to every physical CSV output file.
                # Therefore each metric/inch group starts again at 1.
                for row_id, tool in enumerate(unit_tools, start=1):
                    row_dict = row_dict_builder(tool, row_id)
                    writer.writerow(list(row_dict.values()))

            written.append(out_path)
            print(
                f" ✅ {out_path.name} "
                f"({len(unit_tools)} Tools, {sw_unit})"
            )

    return written


def convert_hsmlib_to_solidworks(input_path, output_dir):
    """
    Converts a .hsmlib tool library into one or more SolidWorks CAM CSV files
    (one CSV per SolidWorks tool type, since SW expects a separate file per type).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = Path(input_path).stem
    tools = parse_hsmlib(input_path)

    if not tools:
        print('⚠️ No tools found!')
        return []

    tools_by_type = {}
    unsupported_type = ""
    for tool in tools:
        try:
            HSMToolType(tool.type)
        except ValueError as e:
            if tool.type != unsupported_type:
                unsupported_type = tool.type
                print(e)
                print("Currently not supported! Skipping...")
            continue

        sw_type = resolve_sw_type(tool)
        # special case: thread mills
        if sw_type is SWToolType.THREAD_MULTI and tool.thread_nr_teeth == 0:
            sw_type = SWToolType.THREAD_SINGLE

        # Left-hand and right-hand taps share the same SW file (value "nTaps");
        # collapse both enum members onto a single dict key so write_csv()
        # doesn't overwrite one hand's rows with the other's.
        if sw_type in (SWToolType.TAPS_LH, SWToolType.TAPS_RH):
            sw_type = SWToolType.TAPS_RH

        tools_by_type.setdefault(sw_type, []).append(tool)

    written = write_csv(tools_by_type, output_dir, name)
    print(f"\n✅ Done — {len(tools)} tools exported into {len(written)} CSV file(s).")
    return written
