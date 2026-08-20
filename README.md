# EDA and ECG Preprocessing Pipeline

A Python pipeline for cleaning and preparing physiological data recorded during a psychophysiology experiment, so that downstream analysis of EDA and ECG signals can proceed on clean, well-labelled data.

## Table of contents

- [1. Introduction](#1-introduction)
- [2. Project layout and configuration](#2-project-layout-and-configuration)
  - [2.1 Project structure](#21-project-structure)
  - [2.2 What each script does](#22-what-each-script-does)
  - [2.3 Configuration](#23-configuration)
- [3. Data preparation](#3-data-preparation)
  - [3.1 Why a preparation step is needed](#31-why-a-preparation-step-is-needed)
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
- [6. Next steps](#6-next-steps)

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
├── run_preparation.py               Step 1: raw .acq files to labelled parquet
├── inspect_baseline_duration.py     Step 2: check the baseline period per participant
└── src/
    ├── common/                      Used by more than one stage
    │   ├── file_utils.py            Finding, naming, reading and writing files
    │   ├── trial_boundaries.py      Finding where periods start and end
    │   ├── report_utils.py          Reading and writing the Excel report
    │   └── baseline_plot_utils.py   Drawing the baseline timeline
    ├── preparation/                 Used by the preparation stage only
    │   ├── trigger_codebook.py      The two codebooks and their trigger masks
    │   ├── build_trigger_data.py    Turning 8 pin columns into one trigger column
    │   └── summarize_data.py        Read-only summaries for the reports
    └── preprocessing/               Signal processing, not yet implemented
```

Scripts at the top level are the ones you run. Everything under `src/` is imported by them, grouped by which stage uses it. Modules in `common/` are used by more than one stage, so they do not sit under any single one.

### 2.2 What each script does

**Entry points**

- **`run_preparation.py`** reads every raw `.acq` recording, collapses the 8 pin columns into a single `trigger` column, labels the pre-experiment period as baseline, and writes one parquet file per participant. It also writes a cross-participant Excel report.
- **`inspect_baseline_duration.py`** reads the prepared parquet files and reports how much baseline each recording contains, both as a table and as a timeline plot. Run this after `run_preparation.py`.

**Modules in `src/common/`**

- **`file_utils.py`** finds `.acq` and prepared parquet files, extracts participant IDs from either kind of filename, and handles reading and writing prepared files. It also warns if a file's index does not look like sample positions, since every timing calculation depends on that.
- **`trial_boundaries.py`** finds the start and end of every contiguous block in the recording, whether that block is a trial, a baseline period, or an unknown pin combination. It also finds where the first trial begins, which is what the baseline label depends on.
- **`report_utils.py`** reads the cross-participant Excel report back into dataframes, adds a participant's rows to it, and writes it out again. It is what lets a run prepare only the participants that are not in the report yet, without losing the rows of the ones that are.
- **`baseline_plot_utils.py`** converts a table of periods into timeline bars and draws one row per participant, splitting across several figures when there are too many to fit on one.

**Modules in `src/preparation/`**

- **`trigger_codebook.py`** holds the two codebooks, one for odd and one for even participants, and turns each into a dictionary of boolean masks (the "trigger map"). It also provides the combined mask of every row that matched some trigger.
- **`build_trigger_data.py`** does the transformation: it builds the single `trigger` column, drops the 8 pin columns, and relabels the pre-experiment period as baseline. It returns the cleaned dataframe alongside a report of what happened.
- **`summarize_data.py`** turns the results of the above into the numbers that go in the reports: per-trigger trial counts and durations, how the recording splits between categories, and where the unknown pin combo periods were.

These modules all need the 8 pin columns or the trigger map, both of which only exist while a raw recording is being prepared, which is why they sit under `preparation/` rather than in `common/`.

**`src/preprocessing/`**

Empty for now. The filtering, epoching and downsampling steps described in [section 6](#6-next-steps) will go here.

### 2.3 Configuration

All pipeline parameters live in `config.yaml`:

```yaml
INPUT_DIR: 'input'                    # folder with raw .acq files
PREPARED_DIR: 'prepared_data'         # folder where cleaned parquet files go
OUTPUT_DIR: 'output'                  # folder for diagnostic tables and figures

SAMPLING_RATE: 2000                   # Hz

ignore_participants: ["222", "226"]
no_eda: ["138"]

TRIGGER_COLS:                         # the 8 parallel port pin columns
  - OT_Only
  - OT_Type
  - Living_Word
  - Nonliving_Pseudoword
  - PM_Delayed
  - PM_Active
  - PM
  - Lure

EDA_DOWNSAMPLE: 100                   # target sampling rate after downsampling (Hz)
SCR_DETECTION_THRESHOLD: 0.03         # microsiemens
```

`EDA_DOWNSAMPLE` and `SCR_DETECTION_THRESHOLD` are for the preprocessing stage and are not read by either of the scripts that exist so far. The same is true of `ignore_participants` and `no_eda`.

## 3. Data preparation

### 3.1 Why a preparation step is needed

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

Each cleaned recording is saved as `clean_<participant_id>.parquet` in `PREPARED_DIR`, containing the original physiological signal columns plus the `trigger` column.

Parquet is used instead of CSV because it is much faster to read and write for multi-million-row recordings, and it preserves data types automatically. A 63-minute recording at 2000 Hz is around 30 to 60 MB as parquet versus several hundred MB as CSV.

A cross-participant `report.xlsx` is written alongside the parquet files, with four sheets:

| Sheet | Contents |
|-------|----------|
| `summary` | One row per participant: match rate, category percentages, and where the unknown pin combo periods were |
| `trigger_summary` | Per trigger, per participant: trial counts and durations |
| `unknown_pin_combos` | Which pin combinations failed to match, and how often |
| `after_baseline_relabelling` | The same recording counted again after the baseline label was applied |

The last two sheets are worth reading together. The `summary` sheet describes the trigger column as it was first built, and `after_baseline_relabelling` describes it as it was actually saved.

The report is also what the script uses to decide who still needs preparing. A participant with a row in the `summary` sheet is skipped, so a run after adding one new recording only reads that one `.acq` file, and the rows of everyone already in the report are kept. To prepare a participant again, delete their row from the `summary` sheet.

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
from src.preparation import trigger_codebook

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
from src.preparation import summarize_data

# one row per trigger condition, with trial counts and durations
summary = summarize_data.summarize_triggers(trigger_map)

# prints a breakdown of matched / all pins off / unknown rows
summarize_data.summarize_data(df, trigger_cols, trigger_map)

# chronological event log of every trial in the session
boundaries = trial_boundaries.get_trial_boundaries(trigger_map)
```

These are read-only and do not change the dataframe.

To look at a recording that has already been prepared, load the parquet instead. Only the columns you need have to be read:

```python
from src.common import file_utils, trial_boundaries

prepared_files = file_utils.get_prepared_files(config["PREPARED_DIR"])
trigger        = file_utils.read_prepared_file(prepared_files[0], columns=["trigger"])["trigger"]

# where the baseline period sits
baseline_spans = trial_boundaries.get_run_boundaries(trigger == 0, fs=fs)

# where the first trial starts
first_trial_onset = trial_boundaries.get_first_trial_onset(trigger)
```

Note that `get_trial_boundaries` needs a trigger map and so only works on a raw recording, while the two functions above work on the prepared `trigger` column.

### 3.5 Notes on the trigger system

The experiment uses two versions of the trigger codebook:

- **Version A (odd participants)** uses trigger IDs 1, 2, 17, 18, 49, 50, 52, 56, 65, 66, 68, 72, 129, 130, 145, 146
- **Version B (even participants)** uses trigger IDs 1, 2, 17, 18, 33, 34, 36, 40, 81, 82, 84, 88, 129, 130, 145, 146

The pipeline picks the correct codebook based on whether the participant number is even or odd. Applying the wrong version causes most of the recording to fall into the unknown category, so a low match rate in the report is the first thing to check.

Note that participant **142** is a documented exception and uses the odd codebook despite having an even number.

## 4. Baseline inspection

Run `inspect_baseline_duration.py` after `run_preparation.py` has written the parquet files.

### 4.1 What it checks

The baseline period is whatever was recorded before the paradigm started, so its length depends entirely on how long passed between starting the Biopac recording and starting the experiment. That gap varies from roughly one minute to over twenty across participants.


### 4.2 Output

Both go to `OUTPUT_DIR`:

- **`baseline_summary.csv`**, one row per participant, giving how many baseline blocks were found, how many minutes they total, and at what minute the baseline ends
- **`baseline_timeline.png`**, one horizontal bar per participant on a shared axis that runs the full length of the longest recording, so both the length of each baseline and its size relative to the whole session are visible at a glance

`n_baseline_blocks` should be 1 for every participant, since the relabelling writes a single contiguous stretch. Any other value means something unexpected happened during preparation and is worth investigating.

Any participant whose recording somehow begins at the first trial is reported separately, since that participant has no baseline at all.

## 5. Installation and usage

### 5.1 Clone the repository

```bash
git clone https://github.com/ShekharNarayanan/eda_preprocessing.git
cd eda_preprocessing
```

### 5.2 Install dependencies

This project uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
uv venv
uv sync
```

Main dependencies:

- `neurokit2` for reading Biopac `.acq` files
- `pandas` for dataframe handling
- `pyyaml` for loading the config file
- `pyarrow` for parquet output
- `openpyxl` for the Excel report
- `matplotlib` for the diagnostic plots

### 5.3 Run the pipeline

The two scripts run in order. The second reads what the first wrote.

**Step 1: prepare the data**

Place the raw `.acq` files in the folder named in `config.yaml` under `INPUT_DIR`, then run:

```bash
.venv\Scripts\activate
python -m run_preparation
```

This loops through every `.acq` file that is not already in the report, works out whether the participant is odd or even, applies the correct codebook, builds the trigger column, adds the baseline label, and writes a parquet file per participant to `PREPARED_DIR` along with `report.xlsx`.

**Step 2: check the baselines**

```bash
python -m inspect_baseline_duration
```

This reads the prepared parquet files and writes the baseline table and timeline to `OUTPUT_DIR`.

## 6. Next steps

The prepared parquet files are ready for the signal processing stage, which is not yet implemented and will live in `src/preprocessing/`:

1. Filter the continuous EDA and ECG signals
2. Epoch around trial onsets using the `trigger` column and the boundaries tables
3. Downsample for analysis