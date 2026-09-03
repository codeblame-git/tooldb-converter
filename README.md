# Tool library converter for Solidworks <-> HSM / Autodesk

This project implements the conversion of CAM tool libraries between 
SolidworksCAM CSV, HSMWorks/Fusion360 hsmlib and a meta file format.

To aid with the management of tool libraries across those two platforms, an intermediate data format was defined.
It uses simple .json/.csv files as input for later conversion to target formats.
This allows tool manufacturers and users, using any office spreadsheet tool or editor, to quickly define tool libraries 
for export to SWCAM and HSM without having to care about the quirks of the different formats and the interpretation/formatting of values.

Please understand that there are limitations to the extent this tool can work: missing or incompatible information is approximated or
substituted to fit the data requirements of the target format. This also applies to the 3d body model of tools in HSM.

Not all tool types of a platform may be possible to convert to the other. 
This application currently focuses mainly on 'normal' mills for desktop cnc and hobby users.

My main goal was to fix my broken workflow between CAM software, with hidden attributes in a file impacting
results of feed & speed calculators and ruining workpieces and tools.
However, I hope that many find it useful and that it enables smaller manufacturers to make their products more
accessible and the DIY/hobbyist community to work together and reduce redundant workload.


## Notes
### Requirements & Install

Tested with Python 3.14.7. See requirement files for python environments.

```
pip install -r requirements.txt

or with anaconda

conda create --name <env> --file conda_env_req.txt
```

### Libraries

For libraries see the https://github.com/codeblame-git/tooldb-libraries repository.

### Usage

```
python toolconverter.py -h 

usage: toolconverter.py [-h] -i INPUT -o OUTPUT [--to-solidworks] [--dump-meta-json] [--dump-meta-csv] [--convert-meta]

Convert tool data between file formats.

options:
  -h, --help           show this help message and exit
  -i, --input INPUT    input file or glob pattern (e.g. "F:\Files\*.hsmlib")
  -o, --output OUTPUT  output path
  --to-solidworks      when the input is a meta JSON/CSV file, convert it to SolidWorks CSV instead of hsmlib
                       (default: hsmlib) (default: False)
  --dump-meta-json     additionally write the parsed Tool list as a meta JSON file ("{name}.json") alongside the
                       normal conversion output (default: False)
  --dump-meta-csv      additionally write the parsed Tool list as a meta CSV file ("{name}.csv") alongside the
                       normal conversion output (default: False)
  --convert-meta       Converts one meta format (.json or .csv) to the other. (default: False)
```

```
python libraries\Dreanique\dreanique_to_meta.py -h
usage: dreanique_to_meta.py [-h] [-o OUTPUT_DIR] [--json] [--csv] pdf_path

Dreanique PDF catalog -> Tool meta CSV/JSON

positional arguments:
  pdf_path              Path to the Dreanique catalog PDF

options:
  -h, --help            show this help message and exit
  -o, --output-dir OUTPUT_DIR
                        Output directory for the meta file(s) (default: current directory)
  --json                Write meta JSON only
  --csv                 Write meta CSV only
```

# LICENSE

This software is licensed under AGPLv3 or later: https://www.gnu.org/licenses/agpl-3.0.html.en#license-text

# DISCLAIMER

THIS IS FREE AND OPEN-SOURCE SOFTWARE PROVIDED WITHOUT CHARGE. USE AT OWN RISK!

IT IS YOUR PERSONAL OBLIGATION TO CHECK ALL TOOL DATA EXPORTED BY THIS SOFTWARE FOR CORRECTNESS AND MATCHING YOUR REAL 
TOOLS BEFORE USING IT IN ANY MANUFACTURING PROCESSES.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

Copyright (C) 2026 Codeblame
