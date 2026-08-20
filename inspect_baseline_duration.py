import yaml
import pandas as pd
from pathlib import Path

import src.common.file_utils as file_utils
import src.common.trial_boundaries as trial_boundaries
import src.common.baseline_plot_utils as baseline_plot_utils

# Load the config file from the same folder as this script.
root        = Path(__file__).parent
config_path = root / "config.yaml"

with open(config_path) as f:
    config = yaml.safe_load(f)

fs           = config["SAMPLING_RATE"]
prepared_dir = Path(config["PREPARED_DIR"])
output_dir   = Path(config["OUTPUT_DIR"])
output_dir.mkdir(parents=True, exist_ok=True)

# Periods shorter than this are drawn at this width so that they stay visible
# on an hour long axis. It is defined once here so that the bars and the note
# printed under the plot always describe the same thing.
MIN_BAR_MIN = 0.1

# Find every prepared parquet file. They come back already in participant order.
parquet_files = file_utils.get_prepared_files(prepared_dir)

if not parquet_files:
    raise FileNotFoundError(f"No clean_*.parquet files found in {prepared_dir}")

# Collectors for the plot and the summary table.
bars_per_participant          = {}
summary_rows                  = []
recording_lengths_min         = []
participants_without_baseline = []


# Look at each participant one at a time.
for path in parquet_files:
    participant_id = file_utils.get_participant_id_from_parquet(path)
    print(f"Reading participant {participant_id}...")

    # Only the trigger column is needed here, so the much larger EDA and ECG
    # columns are never loaded into memory.
    trigger = file_utils.read_prepared_file(path, columns=["trigger"])["trigger"]

    recording_lengths_min.append(len(trigger) / (fs * 60))

    # Everything recorded before the first trial is labelled 0, so that is the
    # baseline period. It is found with the same run detection used elsewhere,
    # which also catches the case of a recording somehow having more than one
    # such block.
    baseline_mask  = trigger == 0
    baseline_spans = trial_boundaries.get_run_boundaries(baseline_mask, fs=fs)

    if baseline_spans.empty:
        print(
            f"  WARNING participant {participant_id}: no baseline period, the "
            f"recording starts at the first trial"
        )
        participants_without_baseline.append(participant_id)
        bars_per_participant[participant_id] = []
        continue

    bars_per_participant[participant_id] = baseline_plot_utils.get_span_bars(
        baseline_spans, fs=fs, min_bar_min=MIN_BAR_MIN,
    )

    baseline_samples = baseline_spans["duration_samples"].sum()

    summary_rows.append({
        "participant_id":        participant_id,
        "n_baseline_blocks":     len(baseline_spans),
        "baseline_duration_min": round(baseline_samples / (fs * 60), 2),
        "baseline_ends_min":     round(baseline_spans["offset"].max() / (fs * 60), 2),
    })


# The x axis runs to the length of the longest recording so that every row
# shares one scale and both position and length can be compared between
# participants.
recording_length_min = max(recording_lengths_min)

if participants_without_baseline:
    print(
        f"\nNo baseline period found for: "
        f"{', '.join(participants_without_baseline)}"
    )

if not summary_rows:
    raise SystemExit("No participant had a baseline period, nothing to plot.")

summary_table = pd.DataFrame(summary_rows)
print("\nBaseline summary:")
print(summary_table.to_string(index=False))

table_path = output_dir / "baseline_summary.csv"
summary_table.to_csv(table_path, index=False)
print(f"\nTable saved -> {table_path}")

figures = baseline_plot_utils.plot_span_timeline(
    bars_per_participant,
    recording_length_min = recording_length_min,
    title                = "Baseline period, before the first trial",
    empty_text           = "no baseline",
    min_bar_min          = MIN_BAR_MIN,
)

for page_number, figure in enumerate(figures, start=1):
    if len(figures) == 1:
        figure_path = output_dir / "baseline_timeline.png"
    else:
        figure_path = output_dir / f"baseline_timeline_page{page_number}.png"

    figure.savefig(figure_path, dpi=150)
    print(f"Figure saved -> {figure_path}")