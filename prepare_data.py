import yaml
import neurokit2 as nk
import pandas as pd
from pathlib import Path

import src.io as io
import src.trigger_utils as trigger_utils
import src.clean_data as clean_data

# Load the config file from the same folder as this script.
# Config holds paths, sampling rate, trigger column names, and EDA/ECG
# parameters that will be used throughout the pipeline.
root        = Path(__file__).parent
config_path = root / "config.yaml"

with open(config_path) as f:
    config = yaml.safe_load(f)

# Make sure the folder for cleaned data exists before we start writing to it.
prepared_dir = Path(config["PREPARED_DIR"])
prepared_dir.mkdir(parents=True, exist_ok=True)

# Find every .acq recording in the input folder.
acq_files = io.get_acq_files(config["INPUT_DIR"])


# Process each participant one at a time.
for path in acq_files:

    # The participant ID is encoded in the filename. Even and odd IDs
    # belong to different experimental versions (A and B) with different
    # trigger codebooks, so we need to know which one we're dealing with.
    participant_id = io.get_participant_id(path)
    even           = participant_id % 2 == 0

    print(f"\nLoading participant {participant_id} ({'even' if even else 'odd'})...")

    # Read the Biopac .acq file. neurokit returns a tuple where the first
    # element is the raw signal dataframe (EDA, ECG, trigger pins, etc.).
    acq_file = nk.read_acqknowledge(str(path))
    df       = pd.DataFrame(acq_file[0])

    # The 8 parallel port pin columns can arrive as strings or floats with
    # noise. Convert them to clean 0/1 integers: anything non-zero becomes 1.
    df[config["TRIGGER_COLS"]] = (
        df[config["TRIGGER_COLS"]]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .ne(0)
        .astype(int)
    )

    # Pick the correct trigger codebook based on whether the participant
    # is even or odd. Each codebook maps a unique 8-pin combination to a
    # single trigger ID.
    trigger_map = (
        trigger_utils.create_trigger_map_even(df)
        if even
        else trigger_utils.create_trigger_map_odd(df)
    )

    # Collapse the 8 pin columns into one 'trigger' column where each row
    # is labelled with the active trigger ID, 0 for baseline, or -1 for
    # any pin combination not in the codebook (to be excluded later).
    clean_df, report, unknown_pin_combos = clean_data.build_clean_dataset(
        df           = df,
        trigger_cols = config["TRIGGER_COLS"],
        trigger_map  = trigger_map,
        fs           = config["SAMPLING_RATE"],
    )

    # Print a quick summary so we can immediately spot if a recording has
    # too many unknown pin combos or an unusual baseline ratio.
    print(
        f"Participant {participant_id}: "
        f"matched {report['matched_pct']}%, "
        f"baseline {report['baseline_pct']}%, "
        f"unknown pin combos {report['unknown_pin_combo_pct']}% "
        f"({report['unknown_pin_combo_periods']} periods)"
    )

    # Save the cleaned dataframe as parquet (much faster and smaller than
    # CSV for multi-million-row physiological data, and preserves dtypes).
    out_path = prepared_dir / f"clean_{participant_id}.parquet"
    clean_df.to_parquet(out_path)
    print(f"Saved -> {out_path}")