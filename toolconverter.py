#!/usr/bin/env python3
"""
toolconverter.py

Converter between HSMWorks .hsmlib and SolidworksCAM csv and meta file formats of tool libraries.

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

import argparse

from to_hsmlib import *
from to_meta import (
    is_meta_csv,
    is_meta_json,
    write_meta,
    convert_meta_to_hsmlib,
    convert_meta_to_solidworks,
    convert_meta
)
from to_swcam import *


def process_file(input: Path, output: Path, args):
    if not input.exists():
        print(f'Input not found: {input}')
        return False

    input_file_type = input.suffix.lower()
    out = output if output.exists() else (
            input.parent / ('solidworks_csv' if args.to_solidworks else 'hsmlib_output'))

    print("Writing to " + str(out) + ".")

    dump_json = args.dump_meta_json
    dump_csv = args.dump_meta_csv
    name = input.stem
    convert_meta_files = args.convert_meta

    if "hsmlib" in input_file_type:
        tools = parse_hsmlib(input)
        if dump_json or dump_csv:
            write_meta(tools, out, name, as_json=dump_json, as_csv=dump_csv)
        convert_hsmlib_to_solidworks(input, out)

    elif input_file_type == ".json":
        # A meta JSON file (Tool dataclass dump) is used directly as the
        # conversion source; the normal hsmlib/CSV parsers are skipped since
        # the Tool objects are already fully typed.
        if not is_meta_json(input):
            print(f'Unsupported JSON file (not a recognized meta file): {input}')
            return False
        if args.to_solidworks:
            convert_meta_to_solidworks(input, out)
        elif convert_meta_files:
            convert_meta(input, out, False)
        else:
            out_file = out if out.suffix else (out / f"{name}.hsmlib")
            convert_meta_to_hsmlib(input, out_file)

    elif input_file_type == ".csv":
        # ".csv" is ambiguous between a SolidWorks-exported tool CSV and a
        # meta CSV (Tool dataclass dump); disambiguate via the header row.
        if is_meta_csv(input):
            if args.to_solidworks:
                convert_meta_to_solidworks(input, out)
            elif convert_meta_files:
                convert_meta(input, out)
            else:
                out_file = out if out.suffix else (out / f"{name}.hsmlib")
                convert_meta_to_hsmlib(input, out_file)
        else:
            tools = parse_solidworks_csv(input)
            if dump_json or dump_csv:
                write_meta(tools, out, name, as_json=dump_json, as_csv=dump_csv)
            convert_solidworks_to_hsmlib(input, out)

    else:
        print(f'Unsupported file type: {input_file_type}')
        return False

    return True


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Convert tool data between file formats.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument('-i', '--input', type=str, help='input file or glob pattern (e.g. "F:\\Files\\*.hsmlib")',
                    default=None, required=True)
    ap.add_argument('-o', '--output', type=Path, help='output path', default=None, required=True)
    ap.add_argument('--to-solidworks', action='store_true',
                    help='when the input is a meta JSON/CSV file, convert it to SolidWorks CSV '
                         'instead of hsmlib (default: hsmlib)')
    ap.add_argument('--dump-meta-json', action='store_true',
                    help='additionally write the parsed Tool list as a meta JSON file '
                         '("{name}.json") alongside the normal conversion output')
    ap.add_argument('--dump-meta-csv', action='store_true',
                    help='additionally write the parsed Tool list as a meta CSV file '
                         '("{name}.csv") alongside the normal conversion output')
    ap.add_argument('--convert-meta', action='store_true',
                    help='Converts one meta format (.json or .csv) to the other.')

    args = ap.parse_args()

    raw_input = args.input

    if any(ch in raw_input for ch in ('*', '?', '[')):
        pattern_path = Path(raw_input)
        folder = pattern_path.parent
        pattern = pattern_path.name

        if not folder.exists():
            print(f'Input folder not found: {folder}')
            sys.exit(1)

        matches = sorted(folder.glob(pattern))
        matches = [m for m in matches if m.is_file()]

        if not matches:
            print(f'No files matched pattern: {raw_input}')
            sys.exit(1)

        print(f'{len(matches)} file(s) matched "{raw_input}":')
        for m in matches:
            print(f'  - {m}')

        success_count = 0
        for match in matches:
            print(f'\n--- Processing: {match} ---')
            if process_file(match, args.output, args):
                success_count += 1

        print(f'\nDone: {success_count}/{len(matches)} file(s) processed successfully.')
        if success_count == 0:
            sys.exit(1)

    else:
        single_input = Path(raw_input)
        if not process_file(single_input, args.output, args):
            sys.exit(1)


if __name__ == '__main__':
    main()
