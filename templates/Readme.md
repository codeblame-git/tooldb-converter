# Notes

Please see data.py file for the data structures and how they are used by the program.

# Data fields

Due to the different data formats, some values look redundant but are used differently in the csv/hsmlib formats.
Sometimes they need to be set to defaults to allow parsing of the files etc.

- "type": "flat end mill", # see types description below
- "vendor": "",
- "description": "",
- "name": "", # name shown as Tool Id or Product-Id field, use manufacturer Id number
- "product_link": "", # url
- "material": "carbide", # carbide, hss, ti coated, diamond
- "coating": "",
- "coolant_type": "Mist", # Flood, Air Blast, None
- "overall_length":0, #total length of tool
- "shank_length": 0, #length of shank (overall - flute-length - shoulder-length)
- "shank_dia": 0, 
- "shoulder_length": 0, # part above the flute, with flute length or alone: useable length
- "shoulder_dia": 0, #  < shank_dia
- "nr_flutes": 0,
- "flute_length": 0, # for single-tooth thread mills: set flute_length to max. pitch size!
- "flute_dia": 0,
- "tip_dia": 0, # for chamfer tools, engraving bits etc.
- "tip_angle": 0, # for chamfer / drills, often same as the "angle" property
- "tip_length": 0, # calculated often based on chamfer angle
- "angle": 0, # can be used as taper-angle, chamfer-flute angle etc. 
- "corner_radius": 0.0, #used by ball, bull-nose etc.
- "thread_pitch": 0, #
- "thread_profile_angle": 60,
- "thread_nr_teeth": 0, # as it says, distinguishes single/multi thread mills, also for thread drills
- "taper_dia": 0, # tool diameter at the bottom of a tapered mill, often set to flute_dia
- "taper_angle": 0, # angle between vertical and tool flank
- "preset_name": "Default",
- "spindle": 10000,
- "feed_xy": 300,
- "feed_z": 100,
- "feed_in": 150,
- "feed_out": 300,
- "clockwise": true,
- "protrusion": 0, # mainly used by SW/ sometimes converted to "length below holder" in most cases select total tool length!
- "tapered_type": "None",
- "unit": "millimeters" # or "inches"
  },

# Tooltypes

Tooltypes used by hsmlib format and possible values for the type field.

  - "flat end mill"
  - "ball end mill"
  - "bull nose end mill"
  - "chamfer mill" #countersink/engrave bits
  - "lollipop mill"
  - "thread mill"
  - "slot mill"
  - "face mill"
  - "dovetail mill"

  - "tapered mill"

To distinguish tapered mills (flatend, ball nose, bullnose):

- flatend : tapered_type = "tapered_bullnose" + corner_radius = 0
- ball nose: tapered_type = "tapered_ball" + corner_radius = ball radius
- bull nose : tapered_type = "tapered_bullnose" + corner_radius != 0

Hole Making & Drilling Tool Types
  - "drill"
  - "spot drill"
  - "center drill"
  - "counter bore"
  - "counter sink"
  - "tap right hand"
  - "tap left hand"
  - "reamer"
  - "boring bar"
  - "block drill"
  - "radius mill"

Turning Tool Types (Lathe) - currently not supported
  - "turning general"
  - "turning boring"
  - "turning grooving"
  - "turning threading"

Special & Custom Types - currently not supported
  - "form mill"
  - "probe"
  - "unknown"

