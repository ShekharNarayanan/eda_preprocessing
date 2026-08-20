import yaml
import neurokit2 as nk
import pandas as pd
from pathlib import Path

import src.common.file_utils as file_utils
import src.preparation.trigger_codebook as trigger_codebook
import src.preparation.build_trigger_data as build_trigger_data
import src.preparation.summarize_data as summarize_data
import src.common.report_utils as report_utils

# Load the config file from the same folder as this script.
root        = Path(__file__).parent
config_path = root / "config.yaml"

with open(config_path) as f:
    config = yaml.safe_load(f)

# Make sure the folder for cleaned data exists before we start writing to it.
prepared_dir = Path(config["PREPARED_DIR"])
prepared_dir.mkdir(parents=True, exist_ok=True)

report_path = prepared_dir / "report.xlsx"

# Find every .acq recording in the input folder.
print("Found all .acq files in the input folder")
acq_files = file_utils.get_acq_files(config["INPUT_DIR"])

# Read whatever the report already holds. On a first run this comes back as
# empty tables. Everything collected below is added to these, so a run that
# only prepares one new participant keeps the rows of all the earlier ones.
print("Checking if there is already a report present ")
sheets       = report_utils.read_report(report_path)
prepared_ids = report_utils.get_prepared_participant_ids(sheets)
if prepared_ids:
    print("report present.")
else:
    print("report not present. preparing all participants.")
# A participant already in the report has been prepared before, so their
# recording is not read again. Delete their row from the report to force them
# to be prepared afresh.
files_to_prepare = [p for p in acq_files
                    if file_utils.get_participant_id(p) not in prepared_ids]

if not files_to_prepare:
    print(f"All {len(acq_files)} participants are already in the report, nothing to do.")
    raise SystemExit

new_participant_ids = [file_utils.get_participant_id(p) for p in files_to_prepare]
print(f"Preparing data for new participant: "
      f"{', '.join(new_participant_ids)}")


# Process each participant one at a time.
for path in files_to_prepare:
    # The participant ID is encoded in the filename. Even and odd IDs
    # belong to different experimental versions (A and B) with different
    # trigger codebooks, so we need to know which one we're dealing with.
    participant_id     = file_utils.get_participant_id(path)
    participant_number = file_utils.get_participant_number(participant_id)

    even = False if participant_number == 142 else participant_number % 2 == 0  # participant 142 has odd trigger mapping

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
        trigger_codebook.create_trigger_map_even(df)
        if even
        else trigger_codebook.create_trigger_map_odd(df)
    )

    # One row per trigger, with trial counts and durations.
    trigger_summary = summarize_data.summarize_triggers(trigger_map, fs=config["SAMPLING_RATE"])
    trigger_summary.insert(0, "participant_id", participant_id)

    # Collapse the 8 pin columns into one 'trigger' column.
    clean_df, report, unknown_pin_combos = build_trigger_data.build_clean_dataset(
        df           = df,
        trigger_cols = config["TRIGGER_COLS"],
        trigger_map  = trigger_map,
        fs           = config["SAMPLING_RATE"],
    )

    # Relabel the time before the first trial as baseline.
    clean_df["trigger"] = build_trigger_data.add_baseline_label(clean_df["trigger"])

    # Count the labels again after the relabelling, so the report describes
    # the data both as it was built and as it is actually saved.
    baseline_report = summarize_data.summarize_baseline_labels(
        clean_df["trigger"], fs=config["SAMPLING_RATE"]
    )
    baseline_report["participant_id"] = participant_id
    baseline_row = pd.DataFrame([baseline_report])

    print(
        f"Participant {participant_id}: "
        f"matched {report['matched_pct']}%, "
        f"all pins off {report['all_pins_off_pct']}%, "
        f"unknown pin combos {report['unknown_pin_combo_pct']}% "
        f"({report['unknown_pin_combo_periods']} periods)"
    )

    unknown_start_min, unknown_end_min = summarize_data.get_unknown_spans_minutes(
        unknown_pin_combos, fs=config["SAMPLING_RATE"]
    )

    summary_row = pd.DataFrame([{
        "participant_id":            participant_id,
        "version":                   "even" if even else "odd",
        "total_duration_min":        report["total_duration_min"],
        "matched_pct":               report["matched_pct"],
        "all_pins_off_pct":          report["all_pins_off_pct"],
        "unknown_pin_combo_pct":     report["unknown_pin_combo_pct"],
        "unknown_pin_combo_periods": report["unknown_pin_combo_periods"],
        "unknown_start_min":         unknown_start_min,
        "unknown_end_min":           unknown_end_min,
    }])

    # Which pin combinations failed to match anything in the codebook.
    breakdown = summarize_data.get_unknown_pin_combos_breakdown(
        df, config["TRIGGER_COLS"], trigger_map, fs=config["SAMPLING_RATE"],
    )
    if not breakdown.empty:
        breakdown.insert(0, "participant_id", participant_id)

    # Add this participant's rows to what the report already holds.
    sheets = report_utils.add_participant_rows(sheets, {
        "summary":                    summary_row,
        "trigger_summary":            trigger_summary,
        "unknown_pin_combos":         breakdown,
        "after_baseline_relabelling": baseline_row,
    })

    # Save the cleaned dataframe as parquet.
    out_path = file_utils.save_prepared_file(clean_df, prepared_dir, participant_id)
    print(f"Saved -> {out_path}")


# Write the report back out, containing both the participants that were
# already in it and any that were prepared just now.
report_utils.write_report(sheets, report_path)
print(f"\nReport saved -> {report_path}")