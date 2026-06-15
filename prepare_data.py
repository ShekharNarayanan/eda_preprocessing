import yaml
import neurokit2 as nk
import pandas as pd
from pathlib import Path

import src.io as io
import src.trigger_utils as trigger_utils
import src.clean_data as clean_data
import src.inspect_data as inspect_data

# Load the config file from the same folder as this script.
root        = Path(__file__).parent
config_path = root / "config.yaml"

with open(config_path) as f:
    config = yaml.safe_load(f)

# Make sure the folder for cleaned data exists before we start writing to it.
prepared_dir = Path(config["PREPARED_DIR"])
prepared_dir.mkdir(parents=True, exist_ok=True)

# Find every .acq recording in the input folder.
acq_files = io.get_acq_files(config["INPUT_DIR"])

# Collectors for the cross-participant Excel report.
# summary_rows        : one row per participant
# unknown_combo_tables: one per-participant breakdown table, concatenated later
summary_rows            = []
unknown_combo_tables    = []
trigger_summary_tables  = []


# Process each participant one at a time.
for path in acq_files[:6]:

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
    # is even or odd.
    trigger_map = (
        trigger_utils.create_trigger_map_even(df)
        if even
        else trigger_utils.create_trigger_map_odd(df)
    )

    # get trigger summary
    trigger_summary = inspect_data.summarize_triggers(trigger_map, fs=config["SAMPLING_RATE"])
    trigger_summary.insert(0, 'participant_id', participant_id)
    trigger_summary_tables.append(trigger_summary)


    # Collapse the 8 pin columns into one 'trigger' column.
    clean_df, report, unknown_pin_combos = clean_data.build_clean_dataset(
        df           = df,
        trigger_cols = config["TRIGGER_COLS"],
        trigger_map  = trigger_map,
        fs           = config["SAMPLING_RATE"],
    )

    print(
        f"Participant {participant_id}: "
        f"matched {report['matched_pct']}%, "
        f"baseline {report['baseline_pct']}%, "
        f"unknown pin combos {report['unknown_pin_combo_pct']}% "
        f"({report['unknown_pin_combo_periods']} periods)"
    )

    # Collect the summary row for the report sheet.
    summary_rows.append({
        'participant_id':            participant_id,
        'version':                   'even' if even else 'odd',
        'total_duration_min':        report['total_duration_min'],
        'matched_pct':               report['matched_pct'],
        'baseline_pct':              report['baseline_pct'],
        'unknown_pin_combo_pct':     report['unknown_pin_combo_pct'],
        'unknown_pin_combo_periods': report['unknown_pin_combo_periods'],
    })

    # Collect the breakdown of unmatched pin combinations for this participant.
    breakdown = clean_data.get_unknown_pin_combos_breakdown(
        df, config["TRIGGER_COLS"], trigger_map, fs=config["SAMPLING_RATE"],
    )
    if not breakdown.empty:
        breakdown.insert(0, 'participant_id', participant_id)
        unknown_combo_tables.append(breakdown)

    # Save the cleaned dataframe as parquet.
    out_path = prepared_dir / f"clean_{participant_id}.parquet"
    clean_df.to_parquet(out_path)
    print(f"Saved -> {out_path}")


# After processing all participants, write the cross-participant Excel report.
report_path = prepared_dir / "report.xlsx"

# After processing all participants, write the cross-participant Excel report.
report_path = prepared_dir / "report.xlsx"
with pd.ExcelWriter(report_path) as writer:
    
    # 1. Summary sheet (Sorted from lowest to highest participant ID)
    pd.DataFrame(summary_rows).sort_values('participant_id').set_index('participant_id').to_excel(
        writer, sheet_name="summary", index=True
    )
    
    # 2. Trigger Summary sheet (Sorted)
    if trigger_summary_tables:
        pd.concat(trigger_summary_tables, ignore_index=True).sort_values('participant_id').set_index('participant_id').to_excel(
            writer, sheet_name="trigger_summary", index=True
        )
    
    # 3. Unknown Pin Combos sheet (Sorted)
    if unknown_combo_tables:
        pd.concat(unknown_combo_tables, ignore_index=True).sort_values('participant_id').set_index('participant_id').to_excel(
            writer, sheet_name="unknown_pin_combos", index=True
        )

print(f"\nReport saved -> {report_path}")



