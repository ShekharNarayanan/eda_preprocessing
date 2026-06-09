# EDA and ECG Preprocessing Pipeline

A Python pipeline for cleaning and preparing physiological data recorded during a psychophysiology experiment, so that downstream analysis of EDA and ECG signals can proceed on clean, well-labelled data.

## Table of contents

- [1. Introduction](#1-introduction)
- [2. Project layout and configuration](#2-project-layout-and-configuration)
  - [2.1 Project structure](#21-project-structure)
  - [2.2 What each module does](#22-what-each-module-does)
  - [2.3 Configuration](#23-configuration)
- [3. Data preparation](#3-data-preparation)
  - [3.1 Why a preparation step is needed](#31-why-a-preparation-step-is-needed)
  - [3.2 Output](#32-output)
  - [3.3 Inspecting a single participant](#33-inspecting-a-single-participant)
  - [3.4 Notes on the trigger system](#34-notes-on-the-trigger-system)
  - [3.5 Next steps](#35-next-steps)
- [4. Installation and usage](#4-installation-and-usage)
  - [4.1 Clone the repository](#41-clone-the-repository)
  - [4.2 Install dependencies](#42-install-dependencies)
  - [4.3 Run the pipeline](#43-run-the-pipeline)

---

## 1. Introduction

This project supports a psychophysiology experiment in which two physiological signals are recorded from each participant using a Biopac system:

- **EDA** (electrodermal activity, sometimes called skin conductance)
- **ECG** (electrocardiogram)

Each recording is roughly one hour long and is sampled at 2000 Hz, which means a single participant produces around 7.6 million rows of data. Alongside the two physiological signals, the recording also stores 8 binary "trigger" columns. These columns represent the 8 pins of a parallel port that the experiment software uses to mark which stimulus the participant is currently being shown. Different combinations of pins correspond to different experimental conditions.

The end goal of this project is to analyze the EDA and ECG signals condition by condition. Before that analysis can happen, the raw recordings need to be cleaned and the 8 trigger columns need to be turned into something meaningful that downstream code can work with. That cleaning and labelling step is what this repository handles.

## 2. Project layout and configuration

### 2.1 Project structure

```
.
├── config.yaml              Pipeline parameters (paths, sampling rate, etc.)
├── prepare_data.py          Main pipeline entry point
└── src/
    ├── io.py                File discovery and participant ID extraction
    ├── trigger_utils.py     Codebooks and trigger map construction
    ├── inspect_data.py      Read-only diagnostic summaries
    └── clean_data.py        Data transformation (8 cols to 1 trigger col)
```

### 2.2 What each module does

- **`io.py`** finds all `.acq` files in the input folder and extracts the participant ID from each filename.
- **`trigger_utils.py`** holds the two codebooks (odd and even) as plain Python dictionaries and provides one function that turns any codebook into a dictionary of boolean masks (the "trigger map").
- **`inspect_data.py`** has read-only helpers for understanding what is in a recording: per-trigger summaries, a breakdown of how many rows fall into each category, and a chronological trial event log.
- **`clean_data.py`** does the actual transformation: it builds the single `trigger` column, drops the 8 pin columns, and returns a cleaned dataframe plus a small report of what happened.

### 2.3 Configuration

All pipeline parameters live in `config.yaml`. The important ones:

```yaml
INPUT_DIR: 'input'             # folder with raw .acq files
PREPARED_DIR: 'prepared_data'  # folder where cleaned parquet files go
OUTPUT_DIR: 'output'           # folder for downstream analysis outputs

SAMPLING_RATE: 2000            # Hz

TRIGGER_COLS:                  # the 8 parallel port pin columns
  - OT_Only
  - OT_Type
  - Living_Word
  - Nonliving_Pseudoword
  - PM_Delayed
  - PM_Active
  - PM
  - Lure

EDA_LOWPASS_HZ: 1.0            # planned EDA filter cutoff (used in next step)
EDA_DOWNSAMPLE: 50             # planned EDA downsample target (Hz)
SCR_DETECTION_THRESHOLD: 0.03  # planned SCR detection threshold (microsiemens)
```

## 3. Data preparation

### 3.1 Why a preparation step is needed

The raw recording stores triggers across 8 parallel port pins, and each unique combination of pins represents one experimental condition (a "trigger"). The codebook that maps pin combinations to trigger IDs is different for odd and even participants, because the experiment was run in two counterbalanced versions (Version A and Version B). On top of that, when pins switch state during the recording there are brief moments where the pin combination does not match anything in the codebook. Those moments need to be flagged so they do not pollute downstream analysis.

This pipeline takes care of all of that and replaces the 8 binary columns with a single `trigger` column whose values mean:

- A trigger ID (1, 17, 145, etc.) when the participant is in that trial
- `0` during baseline (all 8 pins off)
- `-1` during an unknown pin combination (to be excluded from analysis)

### 3.2 Output

Each cleaned recording is saved as `clean_<participant_id>.parquet` in `PREPARED_DIR`. The file contains:

- The original physiological signal columns (EDA, ECG, etc.)
- A `trigger` column where each row is labelled `trigger_id`, `0`, or `-1` as described in section 3.1.

Parquet is used instead of CSV because it is much faster to read and write for multi-million-row recordings, and it preserves data types automatically. A 63-minute recording at 2000 Hz is around 30 to 60 MB as parquet versus several hundred MB as CSV.

After processing, the script prints a one-line summary per participant:

```
Participant 112: matched 95.2%, baseline 3.1%, unknown pin combos 1.7% (42 periods)
```

This tells you what fraction of the recording mapped to known trial conditions, was baseline, or fell into unknown pin combinations, plus how many distinct unknown periods were found.

### 3.3 Inspecting a single participant

If you want to understand a recording without writing anything to disk, the helpers in `inspect_data.py` are useful. After loading a dataframe and building its trigger map:

```python
from src import inspect_data

# one row per trigger condition, with trial counts and durations
summary = inspect_data.summarize_triggers(trigger_map)

# prints a breakdown of matched / baseline / unknown rows
inspect_data.summarize_data(df, trigger_cols, trigger_map)

# chronological event log of every trial in the session
boundaries = inspect_data.get_trial_boundaries(trigger_map)
```

These are read-only and do not change the dataframe.

### 3.4 Notes on the trigger system

The experiment uses two versions of the trigger codebook:

- **Version A (odd participants)** uses trigger IDs 1, 2, 17, 18, 49, 50, 52, 56, 65, 66, 68, 72, 129, 130, 145, 146
- **Version B (even participants)** uses trigger IDs 1, 2, 17, 18, 33, 34, 36, 40, 81, 82, 84, 88, 129, 130, 145, 146

The pipeline automatically picks the correct codebook from `trigger_utils.py` based on whether the participant number is even or odd.

### 3.5 Next steps

After running `prepare_data.py`, the cleaned parquet files in `PREPARED_DIR` are ready for the next stage: filtering the continuous EDA and ECG signals, epoching around trial onsets using the `trigger` column, and downsampling for analysis. That part of the pipeline is not yet implemented.

## 4. Installation and usage

### 4.1 Clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 4.2 Install dependencies

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

### 4.3 Run the pipeline

Place your raw `.acq` files in the folder named in `config.yaml` under `INPUT_DIR`, then run:

```bash
uv run python prepare_data.py
```

The script loops through every `.acq` file in the input folder, figures out whether the participant is odd or even based on the participant ID in the filename, applies the correct codebook, builds the clean dataset, and writes a parquet file per participant to `PREPARED_DIR`.