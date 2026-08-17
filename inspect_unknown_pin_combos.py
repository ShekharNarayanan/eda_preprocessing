import yaml
import pandas as pd
from pathlib import Path

import src.file_utils as file_utils
import src.trial_boundaries as trial_boundaries
import src.summarize_data as summarize_data
import src.diagnostic_plot_utils as diagnostic_plot_utils

# Load the config file from the same folder as this script.
root        = Path(__file__).parent
config_path = root / "config.yaml"

with open(config_path) as f:
    config = yaml.safe_load(f)

fs           = config["SAMPLING_RATE"]
prepared_dir = Path(config["PREPARED_DIR"])
output_dir   = Path(config["OUTPUT_DIR"])
output_dir.mkdir(parents=True, exist_ok=True)

# Unknown periods shorter than this are drawn at this width so that they stay
# visible on an hour long axis. It is defined once here so that the bars and
# the note printed under the plot always describe the same thing.
MIN_BAR_MIN = 0.1

# Find every prepared parquet file. They come back already in participant order.
parquet_files = file_utils.get_prepared_files(prepared_dir)

if not parquet_files:
    raise FileNotFoundError(f"No clean_*.parquet files found in {prepared_dir}")

# Collectors for the plot and the summary table.
bars_per_participant          = {}
summary_rows                  = []
recording_lengths_min         = []
participants_without_unknowns = []
gaps_to_first_trial_s         = {}


# Look at each participant one at a time.
for path in parquet_files:
    participant_id = file_utils.get_participant_id_from_parquet(path)
    print(f"Reading participant {participant_id}...")

    # Only the trigger column is needed here, so the much larger EDA and ECG
    # columns are never loaded into memory.
    trigger = file_utils.read_prepared_file(path, columns=["trigger"])["trigger"]

    recording_lengths_min.append(len(trigger) / (fs * 60))

    # Rows with an unknown pin combination are labelled -1 in the trigger
    # column. The same run detection used elsewhere finds each contiguous
    # block of them.
    unknown_mask  = trigger == -1
    unknown_spans = trial_boundaries.get_run_boundaries(unknown_mask, fs=fs)

    # Participants without any unknown periods have nothing to show here, so
    # they are left out of both the table and the plot. Their names are kept
    # so it stays clear that they were read and had none.
    if unknown_spans.empty:
        participants_without_unknowns.append(participant_id)
        continue

    bars_per_participant[participant_id] = diagnostic_plot_utils.get_span_bars(
        unknown_spans, fs=fs, min_bar_min=MIN_BAR_MIN,
    )

    # How long after the unknown period does the first real trial start?
    # This assumes the unknown period sits at the start of the recording and
    # finishes before any trial begins. That assumption is checked below
    # rather than trusted, because a participant who breaks it would give a
    # gap that looks like a number but does not mean anything.
    first_trial_onset = trial_boundaries.get_first_trial_onset(trigger)

    if first_trial_onset is None:
        print(f"  WARNING participant {participant_id}: no recognised trials found")
        gap_s = None
    else:
        spans_after_first_trial = (unknown_spans["onset"] > first_trial_onset).sum()
        if spans_after_first_trial > 0:
            print(
                f"  WARNING participant {participant_id}: {spans_after_first_trial} "
                f"unknown period(s) start after the first trial, so this recording "
                f"does not match the assumption that they only occur at the start"
            )

        # Only the unknown periods that finish before the first trial are part
        # of this gap. A participant can also have unknown periods later in the
        # recording, and measuring from one of those would give a large negative
        # number that says nothing about the start of the session.
        spans_before_first_trial = unknown_spans[
            unknown_spans["offset"] < first_trial_onset
        ]

        if spans_before_first_trial.empty:
            gap_s = None
        else:
            last_unknown_offset = spans_before_first_trial["offset"].max()
            gap_s               = round((first_trial_onset - last_unknown_offset) / fs, 2)
            gaps_to_first_trial_s[participant_id] = gap_s

    summary_row = {"participant_id": participant_id}
    summary_row.update(summarize_data.summarize_unknown_spans(unknown_spans, fs=fs))
    summary_row["gap_to_first_trial_s"] = gap_s
    summary_rows.append(summary_row)


# The x axis runs to the length of the longest recording so that every row
# shares one scale and positions can be compared between participants.
recording_length_min = max(recording_lengths_min)

if participants_without_unknowns:
    print(f"\nNo unknown pin combos found for: {', '.join(participants_without_unknowns)}")

if not summary_rows:
    raise SystemExit("No participant had any unknown pin combo periods, nothing to plot.")

summary_table = pd.DataFrame(summary_rows)
print("\nUnknown pin combo summary:")
print(summary_table.to_string(index=False))

table_path = output_dir / "unknown_pin_combo_summary.csv"
summary_table.to_csv(table_path, index=False)
print(f"\nTable saved -> {table_path}")

figures = diagnostic_plot_utils.plot_unknown_timeline(
    bars_per_participant,
    recording_length_min = recording_length_min,
    min_bar_min          = MIN_BAR_MIN,
)

for page_number, figure in enumerate(figures, start=1):
    if len(figures) == 1:
        figure_path = output_dir / "unknown_pin_combo_timeline.png"
    else:
        figure_path = output_dir / f"unknown_pin_combo_timeline_page{page_number}.png"

    figure.savefig(figure_path, dpi=150)
    print(f"Figure saved -> {figure_path}")

if gaps_to_first_trial_s:
    gap_figure = diagnostic_plot_utils.plot_gap_to_first_trial(gaps_to_first_trial_s)
    gap_path   = output_dir / "gap_to_first_trial.png"
    gap_figure.savefig(gap_path, dpi=150)
    print(f"Figure saved -> {gap_path}")

    unexpected = [pid for pid, gap in gaps_to_first_trial_s.items() if gap < 0]
    if unexpected:
        print(
            f"\nNOTE: unknown periods were found after the first trial for: "
            f"{', '.join(unexpected)}. Their gap values are not meaningful."
        )