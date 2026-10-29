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
from time import perf_counter

import matplotlib.pyplot as plt
import yaml

import src.common.file_utils as file_utils
import src.common.signal_plot_utils as signal_plot_utils
import src.preprocessing.signal_preprocessing as signal_preprocessing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, help="Participant ID, including any session suffix.")
    parser.add_argument("--no-show", action="store_true", help="Save the PNG without opening a plot window.")
    parser.add_argument(
        "--zoom", nargs=2, type=float, action="append", metavar=("START_MIN", "END_MIN"),
        help="Export a display-only zoom in recording minutes; repeat for several spans. Overrides config zooms.",
    )
    args = parser.parse_args()

    # Keep configured relative data paths relative to the working directory.
    config_path = Path(__file__).with_name("config.yaml")
    with config_path.open(encoding="utf-8") as source:
        config = yaml.safe_load(source)

    settings = config["PREPROCESSING"]
    fs = config["SAMPLING_RATE"]
    target_fs = settings["TARGET_SAMPLING_RATE"]
    zoom_windows_min = (
        args.zoom if args.zoom is not None
        else config["PREPROCESSING_CHARTS"]["ZOOM_WINDOWS_MIN"]
    )
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
    started = perf_counter()
    result = signal_preprocessing.preprocess_signal(
        raw_eda, target_fs=target_fs, fs=fs,
        resampling_method=settings["RESAMPLING_METHOD"],
        smoothing_window_samples=settings["SMOOTHING_WINDOW_SAMPLES"],
        smoothing_method=settings["SMOOTHING_METHOD"],
        smoothing_alignment=settings["SMOOTHING_ALIGNMENT"],
        smoothing_edge=settings["SMOOTHING_EDGE"],
        fir_filter_type=settings["FIR_FILTER_TYPE"],
        fir_cutoff_hz=settings["FIR_CUTOFF_HZ"],
        fir_window=settings["FIR_WINDOW"],
        fir_coefficient_mode=settings["FIR_COEFFICIENT_MODE"],
        fir_num_taps=settings["FIR_NUM_TAPS"],
        fir_optimized_factor=settings["FIR_OPTIMIZED_FACTOR"],
        fir_scale=settings["FIR_SCALE"],
        fir_delay_compensation=settings["FIR_DELAY_COMPENSATION"],
        fir_edge=settings["FIR_EDGE"],
    )
    signals = result["signals"]
    timeline = result["timeline"]
    fir = result["metadata"]["fir"]
    print(
        f"Participant {participant_id}: {len(signals['filtered']):,} processed samples; "
        f"FIR {fir['filter_type']} {fir['cutoff_hz']:g} Hz, {fir['window']}, "
        f"{fir['num_taps']} coefficients ({fir['coefficient_mode']}); "
        f"remaining delay {fir['remaining_delay_samples']} samples "
        f"({fir['remaining_delay_s']:g} s), {fir['edge']} edges; "
        f"{perf_counter() - started:.2f} s"
    )

    # Retain every earlier trace, each on its own exact recording-time grid.
    steps = {
        f"Original ({fs:g} Hz)": (signals["raw"], result["raw_time_s"]),
        f"Resampled ({target_fs:g} Hz; {settings['RESAMPLING_METHOD']})": (
            signals["resampled"], timeline["time_s"],
        ),
        (
            f"Smoothed ({settings['SMOOTHING_METHOD']}; "
            f"{settings['SMOOTHING_WINDOW_SAMPLES']} samples; "
            f"{settings['SMOOTHING_ALIGNMENT']}; {settings['SMOOTHING_EDGE']} edges)"
        ): (signals["smoothed"], timeline["time_s"]),
        (
            f"FIR ({fir['filter_type']}; {fir['cutoff_hz']:g} Hz; {fir['window']}; "
            f"{fir['num_taps']} taps, {fir['coefficient_mode']}; "
            f"gain {'normalized' if fir['scale'] else 'unscaled'}; "
            f"delay {'compensated' if fir['delay_compensation'] else 'retained'}; {fir['edge']} edges)"
        ): (signals["filtered"], timeline["time_s"]),
    }
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export the full overlay and linked panels, then change display limits only.
    views = [("", None)] + [
        (f"_zoom_{number}", window_min)
        for number, window_min in enumerate(zoom_windows_min, start=1)
    ]
    figures = []
    title = f"Participant {participant_id}: EDA preprocessing"
    for name, plotter in (
        ("preprocessing", signal_plot_utils.plot_signal_steps),
        ("preprocessing_panels", signal_preprocessing.plot_preprocessing),
    ):
        fig = plotter(steps, title=title)
        overview_limits = fig.axes[-1].get_xlim()
        overview_y_limits = [ax.get_ylim() for ax in fig.axes]
        for suffix, window_min in views:
            # Reuse plotted traces so zoom exports do not duplicate large arrays.
            if window_min is None:
                view_name = "overview"
                fig.axes[-1].set_xlim(overview_limits)
            else:
                signal_plot_utils.set_time_range(fig, window_min)
                view_name = f"{window_min[0]:g}-{window_min[1]:g} min"
            path = output_dir / f"{name}_{participant_id}{suffix}.png"
            fig.savefig(path, dpi=200, bbox_inches="tight")
            print(f"Saved {len(steps)} preprocessing steps ({view_name}) -> {path}")
        fig.axes[-1].set_xlim(overview_limits)
        for ax, limits in zip(fig.axes, overview_y_limits):
            ax.set_ylim(limits)
        if args.no_show:
            plt.close(fig)
        else:
            figures.append(fig)

    # Matplotlib's shared axes provide interactive zoom/pan without reprocessing.
    if not args.no_show:
        plt.show()
    for fig in figures:
        plt.close(fig)
