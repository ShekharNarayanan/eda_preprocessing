# EDA and ECG Preprocessing Pipeline

A Python pipeline for cleaning and segmenting physiological data recorded during a psychophysiology experiment, so that downstream analysis of EDA and ECG signals can proceed on clean, well-labelled data.

## Table of contents

- [1. Introduction](#1-introduction)
- [2. Project layout and configuration](#2-project-layout-and-configuration)
  - [2.1 Project structure](#21-project-structure)
  - [2.2 What each script does](#22-what-each-script-does)
  - [2.3 Configuration](#23-configuration)
- [3. Data segmentation](#3-data-segmentation)
  - [3.1 Why a segmentation step is needed](#31-why-a-segmentation-step-is-needed)
  - [3.2 The trigger column](#32-the-trigger-column)
  - [3.3 Output](#33-output)
  - [3.4 Inspecting a single participant](#34-inspecting-a-single-participant)
  - [3.5 Notes on the trigger system](#35-notes-on-the-trigger-system)
- [4. Baseline inspection](#4-baseline-inspection)
  - [4.1 What it checks](#41-what-it-checks)
  - [4.2 Output](#42-output)
- [5. Installation and usage](#5-installation-and-usage)
  - [5.1 Clone the repository](#51-clone-the-repository)
  - [5.2 Install dependencies](#52-install-dependencies)
  - [5.3 Run the pipeline](#53-run-the-pipeline)
- [6. Signal preprocessing](#6-signal-preprocessing)
  - [6.1 Run preprocessing](#61-run-preprocessing)
  - [6.2 Preview a participant](#62-preview-a-participant)

---

## 1. Introduction

This project supports a psychophysiology experiment in which two physiological signals are recorded from each participant using a Biopac system:

- **EDA** (electrodermal activity, sometimes called skin conductance)
- **ECG** (electrocardiogram)

Each recording is roughly one hour long and is sampled at 2000 Hz. Alongside the two physiological signals, the recording also stores 8 binary "trigger" columns. These columns represent the 8 pins of a parallel port that the experiment software uses to mark which stimulus the participant is currently being shown. Different combinations of pins correspond to different experimental conditions.

The end goal of this project is to analyze the EDA and ECG signals condition by condition. Before that analysis can happen, the raw recordings need to be cleaned and the 8 trigger columns need to be turned into something meaningful that downstream code can work with. That cleaning and labelling step is what this repository handles.

## 2. Project layout and configuration

### 2.1 Project structure

```
.
├── config.yaml                      Pipeline parameters (paths, sampling rate, etc.)
├── run_segmentation.py              Step 1: raw .acq files to labelled parquet
├── inspect_baseline_duration.py     Step 2: check the baseline period per participant
├── run_preprocessing.py             Step 3: preprocess EDA, save recordings, and preview steps
└── src/
    ├── common/                      Used by more than one stage
    │   ├── file_utils.py            Finding, naming, reading and writing files
    │   ├── trial_boundaries.py      Finding where periods start and end
    │   ├── report_utils.py          Reading and writing the Excel report
    │   ├── baseline_plot_utils.py   Drawing the baseline timeline
    │   └── signal_plot_utils.py     Superimposing named signal steps
    ├── segmentation/                Used by the segmentation stage only
    │   ├── trigger_codebook.py      The two codebooks and their trigger masks
    │   ├── build_trigger_data.py    Turning 8 pin columns into one trigger column
    │   └── summarize_data.py        Read-only summaries for the reports
    └── preprocessing/               Signal processing
        └── signal_preprocessing.py  Validation, resampling, smoothing, and FIR filtering
```

Scripts at the top level are the ones you run. Everything under `src/` is imported by them, grouped by which stage uses it. Modules in `common/` are used by more than one stage, so they do not sit under any single one.

### 2.2 What each script does

**Entry points**

- **`run_segmentation.py`** reads every raw `.acq` recording, collapses the 8 pin columns into a single `trigger` column, labels the pre-experiment period as baseline, and writes one parquet file per participant. It also writes a cross-participant Excel report.
- **`inspect_baseline_duration.py`** reads the segmented parquet files and reports how much baseline each recording contains, both as a table and as a timeline plot. Run this after `run_segmentation.py`.
- **`run_preprocessing.py`** reads segmented recordings, applies the shared `PREPROCESSING` settings to EDA, and saves the processed recordings with their trigger labels and other channels. Use `--preview_for_participant` to process one participant and display and export graphs of each preprocessing step. See section 6 for usage.

**Modules in `src/common/`**

- **`file_utils.py`** finds `.acq` and segmented parquet files, extracts participant IDs from either kind of filename, and handles reading and writing segmented files. It also warns if a file's index does not look like sample positions, since every timing calculation depends on that.
- **`trial_boundaries.py`** finds the start and end of every contiguous block in the recording, whether that block is a trial, a baseline period, or an unknown pin combination. It also finds where the first trial begins, which is what the baseline label depends on.
- **`report_utils.py`** reads the cross-participant Excel report back into dataframes, adds a participant's rows to it, and writes it out again. It is what lets a run segment only the participants that are not in the report yet, without losing the rows of the ones that are.
- **`baseline_plot_utils.py`** converts a table of periods into timeline bars and draws one row per participant, splitting across several figures when there are too many to fit on one.
- **`signal_plot_utils.py`** draws preprocessing overlays and linked panels using each step's recording-time mapping, with legends and display-only zooms.

**Modules in `src/segmentation/`**

- **`trigger_codebook.py`** holds the two codebooks, one for odd and one for even participants, and turns each into a dictionary of boolean masks (the "trigger map"). It also provides the combined mask of every row that matched some trigger.
- **`build_trigger_data.py`** does the transformation: it builds the single `trigger` column, drops the 8 pin columns, and relabels the pre-experiment period as baseline. It returns the cleaned dataframe alongside a report of what happened.
- **`summarize_data.py`** turns the results of the above into the numbers that go in the reports: per-trigger trial counts and durations, how the recording splits between categories, and where the unknown pin combo periods were.

These modules all need the 8 pin columns or the trigger map, both of which only exist while a raw recording is being segmented, which is why they sit under `segmentation/` rather than in `common/`.

**`src/preprocessing/`**

`signal_preprocessing.py` provides validation, resampling, moving mean/median smoothing, and FIR filtering for the complete supplied signal. It also builds a processed recording with filtered EDA, trigger labels, and other channels on the new sampling grid. See [section 6](#6-signal-preprocessing) for usage.

### 2.3 Configuration

All pipeline parameters live in `config.yaml`:

```yaml
INPUT_DIR: 'input'                    # folder with raw .acq files
SEGMENTED_DIR: 'segmented_data'       # folder where cleaned parquet files go
PREPROCESSED_DIR: 'preprocessed_data' # folder where preprocessed parquet files go
OUTPUT_DIR: 'output'                  # folder for diagnostic tables and figures

SAMPLING_RATE: 2000                   # Hz

ignore_participants: ["222", "226"]   # exclude these participants from preprocessing
no_eda: ["138"]                      # exclude recordings without usable EDA

TRIGGER_COLS:                         # the 8 parallel port pin columns
  - OT_Only
  - OT_Type
  - Living_Word
  - Nonliving_Pseudoword
  - PM_Delayed
  - PM_Active
  - PM
  - Lure

PREPROCESSING:                       # settings used by run_preprocessing.py
    EDA_COLUMN: "EDA - EDA, Y, PPGED-R" # name of the EDA channel to process
    TARGET_SAMPLING_RATE: 1000        # Hz, for the initial resampling step
    RESAMPLING_METHOD: "linear"      # linear, padding (sample to the left), or cubic_spline
    SMOOTHING_WINDOW_SAMPLES: 100     # samples at the target rate (0.1 s at 1000 Hz)
    SMOOTHING_METHOD: "median"       # moving mean or median
    SMOOTHING_ALIGNMENT: "centered"  # centered or trailing window
    SMOOTHING_EDGE: "shrink"         # shrink the window or repeat endpoints with nearest
    FIR_FILTER_TYPE: "lowpass"       # lowpass or highpass
    FIR_CUTOFF_HZ: 1.0               # Hz, between 0 and half the target rate
    FIR_WINDOW: "hamming"            # hamming, hann, blackman, or boxcar
    FIR_COEFFICIENT_MODE: "optimized" # optimized estimate or fixed count
    FIR_NUM_TAPS: null               # fixed mode: odd integer of at least 3
    FIR_OPTIMIZED_FACTOR: 4.0        # multiplier for the optimized count
    FIR_SCALE: true                  # normalize gain
    FIR_DELAY_COMPENSATION: true     # remove the filter's group delay
    FIR_EDGE: "reflect"              # reflect, nearest, or zero

PREPROCESSING_CHARTS:                # display settings used only for participant previews
    ZOOM_WINDOWS_MIN: [[0.0, 0.5]]    # [start, end] pairs in recording minutes; [] for overview only

# These settings are currently unused.
EDA_DOWNSAMPLE: 100                   # target sampling rate (Hz)
SCR_DETECTION_THRESHOLD: 0.03         # SCR detection threshold (microsiemens)

ACQKNOWLEDGE_REFERENCE_DIR: 'Acqknowledge'  # local fixtures for optional tests
```

Run scripts from the repository root so configured relative paths resolve to the intended data folders. Keep `PREPROCESSED_DIR` separate from `SEGMENTED_DIR`; the preprocessing script rejects identical input and output directories.

`PREPROCESSING` controls EDA channel selection, resampling, smoothing, and FIR filtering, applied in that order. `SAMPLING_RATE` describes the input recordings; `PREPROCESSING.TARGET_SAMPLING_RATE` sets the processed rate and the rate used for smoothing and FIR settings. `EDA_DOWNSAMPLE` does not override it.

`FIR_COEFFICIENT_MODE: "optimized"` estimates the number of filter coefficients using `FIR_OPTIMIZED_FACTOR * TARGET_SAMPLING_RATE / FIR_CUTOFF_HZ`, rounded up to an odd count of at least 3. Use `"fixed"` with `FIR_NUM_TAPS` to set an odd count of at least 3 yourself. `FIR_SCALE` normalizes gain at zero frequency for lowpass or half the target rate for highpass, and `FIR_DELAY_COMPENSATION` removes the filter delay. `FIR_EDGE` controls endpoint padding: mirrored samples (`reflect`), repeated endpoints (`nearest`), or zeros (`zero`).

`run_preprocessing.py` skips IDs in either `ignore_participants` or `no_eda`, including when a preview is requested. Keep IDs as strings: `"112"` excludes all sessions of participant 112, while `"112_2"` excludes only that session. These exclusions and the `PREPROCESSING` settings do not affect segmentation or baseline inspection.

## 3. Data segmentation

### 3.1 Why a segmentation step is needed

The raw recording stores triggers across 8 parallel port pins, and each unique combination of pins represents one experimental condition (a "trigger"). The codebook that maps pin combinations to trigger IDs is different for odd and even participants, because the experiment was run in two counterbalanced versions (Version A and Version B). Some pin combinations in the recording did not match anything in the codebook (due to experimental hiccups). These were flagged as "unknown" pin combos.

The timeperiod in the recording before the first trial is considered to be the "baseline" period. This can vary across participants. Expanded on below.

### 3.2 The trigger column

The pipeline replaces the each combination of 8 binary columns that is equivalent of a condition with a single `trigger` column. Its values mean:

| Value | Meaning |
|-------|---------|
| `N` (positive) | The trigger ID of the trial active at that sample. Supplied by the researcher |
| `0`  | Baseline: everything recorded before the first trial |
| `-1` | Unknown pin combination, occurring after the first trial |
| `-2` | All 8 pins off, occurring after the first trial |

Baseline is defined by position rather than by pin state. Everything before the first recognised trial is baseline. For some participants, due to experimental hiccups the period before the first trial was just an unknown combination of pins (i.e., a combination that does not belong to a predefined condition). For these participants, this period of unknown pin combination before the first trial is considered "baseline"


### 3.3 Output

Each cleaned recording is saved as `clean_<participant_id>.parquet` in `SEGMENTED_DIR`, containing the original physiological signal columns plus the `trigger` column.

Parquet is used instead of CSV because it is much faster to read and write for multi-million-row recordings, and it preserves data types automatically. A 63-minute recording at 2000 Hz is around 30 to 60 MB as parquet versus several hundred MB as CSV.

A cross-participant `report.xlsx` is written alongside the parquet files, with four sheets:

| Sheet | Contents |
|-------|----------|
| `summary` | One row per participant: match rate, category percentages, and where the unknown pin combo periods were |
| `trigger_summary` | Per trigger, per participant: trial counts and durations |
| `unknown_pin_combos` | Which pin combinations failed to match, and how often |
| `after_baseline_relabelling` | The same recording counted again after the baseline label was applied |

The last two sheets are worth reading together. The `summary` sheet describes the trigger column as it was first built, and `after_baseline_relabelling` describes it as it was actually saved.

The report is also what the script uses to decide who still needs segmenting. A participant with a row in the `summary` sheet is skipped, so a run after adding one new recording only reads that one `.acq` file, and the rows of everyone already in the report are kept. To segment a participant again, delete their row from the `summary` sheet.

While running, the script prints a one-line summary per participant:

```
Participant 112: matched 95.2%, all pins off 3.1%, unknown pin combos 1.7% (42 periods)
```

### 3.4 Inspecting a single participant

To understand one recording without writing anything to disk, the helpers in `summarize_data.py` and `trial_boundaries.py` are useful. After loading a dataframe and building its trigger map:

```python
import yaml
import neurokit2 as nk
import pandas as pd

from src.common import file_utils
from src.segmentation import trigger_codebook

with open("config.yaml") as f:
    config = yaml.safe_load(f)

trigger_cols = config["TRIGGER_COLS"]
fs           = config["SAMPLING_RATE"]

# Pick one participant out of the input folder.
acq_files      = file_utils.get_acq_files(config["INPUT_DIR"])
path           = acq_files[0]
participant_id = file_utils.get_participant_id(path)

# Read the recording. Neurokit returns a tuple whose first element is the
# dataframe of raw signals.
df = pd.DataFrame(nk.read_acqknowledge(str(path))[0])

# The pin columns can arrive as strings or as floats with noise, so anything
# non-zero becomes 1.
df[trigger_cols] = (
    df[trigger_cols]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
    .ne(0)
    .astype(int)
)

# Odd and even participants use different codebooks.
participant_number = file_utils.get_participant_number(participant_id)
even        = participant_number % 2 == 0
trigger_map = (
    trigger_codebook.create_trigger_map_even(df)
    if even
    else trigger_codebook.create_trigger_map_odd(df)
)
```
Now that the trigger map is built, we can proceed with the summary.

```python
from src.common import trial_boundaries
from src.segmentation import summarize_data

# one row per trigger condition, with trial counts and durations
summary = summarize_data.summarize_triggers(trigger_map)

# prints a breakdown of matched / all pins off / unknown rows
summarize_data.summarize_data(df, trigger_cols, trigger_map)

# chronological event log of every trial in the session
boundaries = trial_boundaries.get_trial_boundaries(trigger_map)
```

These are read-only and do not change the dataframe.

To look at a recording that has already been segmented, load the parquet instead. Only the columns you need have to be read:

```python
from src.common import file_utils, trial_boundaries

segmented_files = file_utils.get_segmented_files(config["SEGMENTED_DIR"])
trigger         = file_utils.read_segmented_file(segmented_files[0], columns=["trigger"])["trigger"]

# where the baseline period sits
baseline_spans = trial_boundaries.get_run_boundaries(trigger == 0, fs=fs)

# where the first trial starts
first_trial_onset = trial_boundaries.get_first_trial_onset(trigger)
```

Note that `get_trial_boundaries` needs a trigger map and so only works on a raw recording, while the two functions above work on the segmented `trigger` column.

### 3.5 Notes on the trigger system

The experiment uses two versions of the trigger codebook:

- **Version A (odd participants)** uses trigger IDs 1, 2, 17, 18, 49, 50, 52, 56, 65, 66, 68, 72, 129, 130, 145, 146
- **Version B (even participants)** uses trigger IDs 1, 2, 17, 18, 33, 34, 36, 40, 81, 82, 84, 88, 129, 130, 145, 146

The pipeline picks the correct codebook based on whether the participant number is even or odd. Applying the wrong version causes most of the recording to fall into the unknown category, so a low match rate in the report is the first thing to check.

Note that participant **142** is a documented exception and uses the odd codebook despite having an even number.

## 4. Baseline inspection

Run `inspect_baseline_duration.py` after `run_segmentation.py` has written the parquet files.

### 4.1 What it checks

The baseline period is whatever was recorded before the paradigm started, so its length depends entirely on how long passed between starting the Biopac recording and starting the experiment. That gap varies from roughly one minute to over twenty across participants.


### 4.2 Output

Both go to `OUTPUT_DIR`:

- **`baseline_summary.csv`**, one row per participant, giving how many baseline blocks were found, how many minutes they total, and at what minute the baseline ends
- **`baseline_timeline.png`**, one horizontal bar per participant on a shared axis that runs the full length of the longest recording, so both the length of each baseline and its size relative to the whole session are visible at a glance

`n_baseline_blocks` should be 1 for every participant, since the relabelling writes a single contiguous stretch. Any other value means something unexpected happened during segmentation and is worth investigating.

Any participant whose recording somehow begins at the first trial is reported separately, since that participant has no baseline at all.

## 5. Installation and usage

### 5.1 Clone the repository

```bash
git clone https://github.com/ShekharNarayanan/eda_preprocessing.git
cd eda_preprocessing
```

### 5.2 Install dependencies

This project uses Python 3.12, selected by `.python-version`, and [uv](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
uv sync --locked
```

`uv sync --locked` creates the environment in `.venv` at the repository root and installs the versions recorded in `uv.lock`. Use `uv run` from this folder to run scripts with that environment. Virtual environments contain machine-specific paths and should be recreated after moving the project.

Main dependencies:

- `neurokit2` for reading Biopac `.acq` files
- `pandas` for dataframe handling
- `pyyaml` for loading the config file
- `pyarrow` for parquet output
- `openpyxl` for the Excel report
- `matplotlib` for the diagnostic plots
- `numpy` and `scipy` for sample grids, interpolation, and FIR filtering

### 5.3 Run the pipeline

Segment the raw recordings first, inspect their baselines, then preprocess the segmented EDA. Run all commands from the repository root.

**Step 1: segment the data**

Place the raw `.acq` files in the folder named in `config.yaml` under `INPUT_DIR`, then run:

```bash
uv run python -m run_segmentation
```

This loops through every `.acq` file that is not already in the report, works out whether the participant is odd or even, applies the correct codebook, builds the trigger column, adds the baseline label, and writes a parquet file per participant to `SEGMENTED_DIR` along with `report.xlsx`.

**Step 2: check the baselines**

```bash
uv run python -m inspect_baseline_duration
```

This reads the segmented parquet files and writes the baseline table and timeline to `OUTPUT_DIR`.

**Step 3: preprocess EDA**

```bash
uv run python -m run_preprocessing
```

This processes all eligible segmented recordings and saves them to `PREPROCESSED_DIR`. To process and preview one participant first, use the commands in [section 6](#6-signal-preprocessing).

## 6. Signal preprocessing

### 6.1 Run preprocessing

```powershell
uv run python -m run_preprocessing
```

The script reads `clean_<participant_id>.parquet` files from `SEGMENTED_DIR` and processes one recording at a time, skipping participants listed in `ignore_participants` or `no_eda`. Each input must contain the configured `PREPROCESSING.EDA_COLUMN` and a `trigger` column. EDA is resampled, smoothed, and FIR-filtered continuously across the complete recording, including baseline and trial boundaries. No anti-alias filter is applied before resampling.

Results are saved as `PREPROCESSED_DIR/clean_<participant_id>.parquet`, with the EDA column replaced by the filtered signal. The `trigger` column and other channels, including ECG, are retained on the processed grid using the original sample at or immediately before each output position. Trigger labels keep their meanings from [section 3.2](#32-the-trigger-column), though spans shorter than one output interval may disappear when reducing the sampling rate. Use `PREPROCESSING.TARGET_SAMPLING_RATE` when interpreting the processed sample index or calculating durations.

Running without preview arguments saves recordings without generating figures. Every eligible recording is processed on each run, replacing any existing output file for that participant.

### 6.2 Preview a participant

To process one participant and inspect the effect of each step:

```powershell
uv run python -m run_preprocessing --preview_for_participant 149
```

The participant ID must match a segmented filename exactly: `149` selects `clean_149.parquet`, and `112_2` selects `clean_112_2.parquet`. Preview mode also saves the preprocessed parquet file, replacing it if it already exists.

Two interactive figures show the original, resampled, smoothed, and FIR-filtered EDA: one overlay and one view with separate panels sharing the time axis. Legends identify the processing settings, time is shown in recording minutes, and the plot windows support zoom and pan.

The script exports overview PNGs and the zooms configured in `PREPROCESSING_CHARTS.ZOOM_WINDOWS_MIN` to `OUTPUT_DIR/preprocessing_charts/` before opening the figures. The default zoom is the first half-minute, `[[0.0, 0.5]]`; set it to `[]` to export only overviews. Override the configured zooms with `--zoom START_MIN END_MIN`, repeating the option for several spans:

```powershell
uv run python -m run_preprocessing --preview_for_participant 149 --zoom 0 0.5 --zoom 10 10.5
```

Zooms affect the displayed range only; preprocessing always uses the complete recording. `--zoom` is used only when `--preview_for_participant` is supplied. For this example, the exported files are:

| File | Contents |
|------|----------|
| `preprocessing_149.png` | Overview with all steps superimposed |
| `preprocessing_panels_149.png` | Overview with separate linked panels |
| `preprocessing_149_zoom_1.png`, `preprocessing_panels_149_zoom_1.png` | Views of minutes 0–0.5 |
| `preprocessing_149_zoom_2.png`, `preprocessing_panels_149_zoom_2.png` | Views of minutes 10–10.5 |

Close the plot windows when finished to let the command exit.
