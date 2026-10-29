"""
Export an overlay of every implemented EDA preprocessing step for one recording.

Run from the repository root, for example:
    uv run python -m preprocessing_charts --participant 149

The complete supplied recording is processed, without a selected-area crop.
Signal processing uses the shared PREPROCESSING settings in config.yaml.
Only the chart is saved; processed signals remain in memory.
Trial extraction and analysis runners remain separate work.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

import src.common.file_utils as file_utils
import src.common.signal_plot_utils as signal_plot_utils
import src.preprocessing.signal_preprocessing as signal_preprocessing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Participant ID, including any session suffix.")
    parser.add_argument("--no-show", action="store_true", help="Save the PNG without opening a plot window.")
    args = parser.parse_args()

    # Keep configured relative data paths relative to the working directory.
    config_path = Path(__file__).with_name("config.yaml")
    with config_path.open(encoding="utf-8") as source:
        config = yaml.safe_load(source)

    settings = config["PREPROCESSING"]
    fs = config["SAMPLING_RATE"]
    target_fs = settings["TARGET_SAMPLING_RATE"]
    output_dir = Path(config["OUTPUT_DIR"]) / "preprocessing_charts"
    participant_id = args.participant

    paths = [
        path for path in file_utils.get_segmented_files(config["SEGMENTED_DIR"])
        if file_utils.get_participant_id_from_parquet(path) == participant_id
    ]
    if not paths:
        raise FileNotFoundError(
            f"No segmented recording found for participant {participant_id} "
            f"in {config['SEGMENTED_DIR']}. Run segmentation first."
        )

    # Read only the physiological channel needed for this comparison.
    print(f"Reading EDA for participant {participant_id}: {paths[0]}")
    eda_column = settings["EDA_COLUMN"]
    raw_eda = file_utils.read_segmented_file(paths[0], columns=[eda_column])[eda_column]
    if raw_eda.empty:
        raise ValueError(f"Participant {participant_id}: the supplied EDA signal is empty.")

    print(f"Processing all {len(raw_eda):,} samples: {fs:g} Hz -> {target_fs:g} Hz")
    resampled, timeline = signal_preprocessing.resample_signal(
        raw_eda, target_fs=target_fs, fs=fs, method=settings["RESAMPLING_METHOD"],
    )
    smoothed = signal_preprocessing.smooth_signal(
        resampled,
        window_samples=settings["SMOOTHING_WINDOW_SAMPLES"],
        method=settings["SMOOTHING_METHOD"],
        alignment=settings["SMOOTHING_ALIGNMENT"],
        edge=settings["SMOOTHING_EDGE"],
    )

    # Add each future preprocessing result here with its recording-time Series.
    raw_time_s = pd.Series(raw_eda.index / fs, index=raw_eda.index)
    steps = {
        f"Original ({fs:g} Hz)": (raw_eda, raw_time_s),
        f"Resampled ({target_fs:g} Hz; {settings['RESAMPLING_METHOD']})": (
            resampled, timeline["time_s"],
        ),
        (
            f"Smoothed ({settings['SMOOTHING_METHOD']}; "
            f"{settings['SMOOTHING_WINDOW_SAMPLES']} samples; "
            f"{settings['SMOOTHING_ALIGNMENT']}; {settings['SMOOTHING_EDGE']} edges)"
        ): (smoothed, timeline["time_s"]),
    }
    fig = signal_plot_utils.plot_signal_steps(
        steps, title=f"Participant {participant_id}: EDA preprocessing steps",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"preprocessing_{participant_id}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"Saved {len(steps)} superimposed steps -> {path}")

    if not args.no_show:
        plt.show()
    plt.close(fig)
