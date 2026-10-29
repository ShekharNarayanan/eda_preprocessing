"""
Preprocess segmented recordings and save them with their trigger labels.

Run from the repository root, for example:
    uv run python -m run_preprocessing
    uv run python -m run_preprocessing --preview_for_participant 149

Selecting a participant enables graph previews and PNG exports for that recording.
The complete recording is processed continuously, without a selected-area crop.
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
    parser.add_argument(
        "--preview_for_participant", metavar="PARTICIPANT_ID",
        help="Process only this participant or session, preview the graphs, and export PNGs.",
    )
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
    chart_settings = config.get("PREPROCESSING_CHARTS", {})
    charts_enabled = args.preview_for_participant is not None
    zoom_windows_min = args.zoom if args.zoom is not None else chart_settings.get("ZOOM_WINDOWS_MIN", [])
    chart_dir = Path(config["OUTPUT_DIR"]) / "preprocessing_charts"
    preprocessed_dir = Path(config["PREPROCESSED_DIR"])
    if preprocessed_dir.resolve() == Path(config["SEGMENTED_DIR"]).resolve():
        raise ValueError("PREPROCESSED_DIR must differ from SEGMENTED_DIR to preserve input recordings.")

    paths = file_utils.get_segmented_files(config["SEGMENTED_DIR"])
    if args.preview_for_participant is not None:
        paths = [
            path for path in paths
            if file_utils.get_participant_id_from_parquet(path) == args.preview_for_participant
        ]
    if not paths:
        participant_label = (
            f" for participant {args.preview_for_participant}"
            if args.preview_for_participant is not None else ""
        )
        raise FileNotFoundError(
            f"No segmented recordings found{participant_label} "
            f"in {config['SEGMENTED_DIR']}. Run segmentation first."
        )

    # A base participant ID excludes all sessions; a suffixed ID excludes only that session.
    excluded_ids = {str(value) for value in config.get("ignore_participants", [])}
    excluded_ids.update(str(value) for value in config.get("no_eda", []))
    preprocessed_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(paths)} segmented recording(s). Charts {'enabled' if charts_enabled else 'disabled'}.")
    eda_column = settings["EDA_COLUMN"]
    for path in paths:
        participant_id = file_utils.get_participant_id_from_parquet(path)
        participant_number = str(file_utils.get_participant_number(participant_id))
        if participant_id in excluded_ids or participant_number in excluded_ids:
            print(f"Skipping participant {participant_id}: listed in ignore_participants or no_eda.")
            continue

        # Read the complete recording to retain trigger labels and the other channels.
        print(f"\nReading participant {participant_id}: {path}")
        df = file_utils.read_segmented_file(path)
        missing = [column for column in (eda_column, "trigger") if column not in df]
        if missing:
            raise ValueError(f"Participant {participant_id}: missing required columns: {missing}")
        if df.empty:
            raise ValueError(f"Participant {participant_id}: the supplied recording is empty.")

        print(f"Processing all {len(df):,} samples: {fs:g} Hz -> {target_fs:g} Hz")
        started = perf_counter()
        result = signal_preprocessing.preprocess_signal(
            df[eda_column], target_fs=target_fs, fs=fs,
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
        processed_df = signal_preprocessing.build_preprocessed_recording(df, result, eda_column)
        out_path = file_utils.save_segmented_file(processed_df, preprocessed_dir, participant_id)
        fir = result["metadata"]["fir"]
        print(
            f"Participant {participant_id}: {len(processed_df):,} processed samples; "
            f"FIR {fir['filter_type']} {fir['cutoff_hz']:g} Hz, {fir['window']}, "
            f"{fir['num_taps']} coefficients ({fir['coefficient_mode']}); "
            f"remaining delay {fir['remaining_delay_samples']} samples "
            f"({fir['remaining_delay_s']:g} s), {fir['edge']} edges; "
            f"{perf_counter() - started:.2f} s\nSaved -> {out_path}"
        )

        if not charts_enabled:
            del df, processed_df, result
            continue

        # Export both views and display-only zooms without processing the signal again.
        steps = signal_plot_utils.build_preprocessing_steps(result)
        chart_dir.mkdir(parents=True, exist_ok=True)
        views = [("", None)] + [
            (f"_zoom_{number}", window_min)
            for number, window_min in enumerate(zoom_windows_min, start=1)
        ]
        figures = []
        title = f"Participant {participant_id}: EDA preprocessing"
        for name, plotter in (
            ("preprocessing", signal_plot_utils.plot_signal_steps),
            ("preprocessing_panels", signal_plot_utils.plot_preprocessing),
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
                chart_path = chart_dir / f"{name}_{participant_id}{suffix}.png"
                fig.savefig(chart_path, dpi=200, bbox_inches="tight")
                print(f"Saved {len(steps)} preprocessing steps ({view_name}) -> {chart_path}")
            fig.axes[-1].set_xlim(overview_limits)
            for ax, limits in zip(fig.axes, overview_y_limits):
                ax.set_ylim(limits)
            figures.append(fig)

        # The selected participant is previewed after exporting all graph views.
        plt.show()
        for fig in figures:
            plt.close(fig)
        del df, processed_df, result, steps, figures, fig, ax
