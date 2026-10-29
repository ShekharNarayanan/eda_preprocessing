"""
Derive phasic EDA and save SCR candidates from preprocessed recordings.

Run from the repository root, for example:
    uv run python -m run_analysis
    uv run python -m run_analysis --preview_for_participant 149

Selecting a participant enables an interactive overlay and PNG exports for that recording.
The complete recording is analyzed without a selected-area crop. Baseline and
phasic waveforms remain in memory; accepted and rejected SCRs are saved as CSV.
"""

import argparse
from pathlib import Path
from time import perf_counter

import matplotlib.pyplot as plt
import yaml

import src.common.file_utils as file_utils
import src.common.signal_plot_utils as signal_plot_utils
import src.preprocessing.signal_analysis as signal_analysis
import src.preprocessing.signal_preprocessing as signal_preprocessing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview_for_participant", metavar="PARTICIPANT_ID",
        help="Analyze only this participant or session, preview the overlay, and export PNGs.",
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

    preprocessing_settings = config["PREPROCESSING"]
    analysis_settings = config["ANALYSIS"]
    chart_settings = config.get("ANALYSIS_CHARTS", {})
    charts_enabled = args.preview_for_participant is not None
    zoom_windows_min = args.zoom if args.zoom is not None else chart_settings.get("ZOOM_WINDOWS_MIN", [])
    analysis_dir = Path(config["OUTPUT_DIR"]) / "analysis"
    chart_dir = Path(config["OUTPUT_DIR"]) / "analysis_charts"
    paths = file_utils.get_segmented_files(config["PREPROCESSED_DIR"])
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
            f"No preprocessed recordings found{participant_label} "
            f"in {config['PREPROCESSED_DIR']}. Run preprocessing first."
        )

    # A base participant ID excludes all sessions; a suffixed ID excludes only that session.
    excluded_ids = {str(value) for value in config.get("ignore_participants", [])}
    excluded_ids.update(str(value) for value in config.get("no_eda", []))
    analysis_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(paths)} preprocessed recording(s). Charts {'enabled' if charts_enabled else 'disabled'}.")
    eda_column = preprocessing_settings["EDA_COLUMN"]
    for path in paths:
        participant_id = file_utils.get_participant_id_from_parquet(path)
        participant_number = str(file_utils.get_participant_number(participant_id))
        if participant_id in excluded_ids or participant_number in excluded_ids:
            print(f"Skipping participant {participant_id}: listed in ignore_participants or no_eda.")
            continue

        # SCR detection needs only filtered EDA. The parquet attributes preserve
        # the processed rate and source origin without loading ECG or triggers.
        print(f"\nReading participant {participant_id}: {path}")
        df = file_utils.read_segmented_file(path, columns=[eda_column])
        if df.empty:
            raise ValueError(f"Participant {participant_id}: the supplied recording is empty.")
        fs = df.attrs.get("sampling_rate_hz", preprocessing_settings["TARGET_SAMPLING_RATE"])
        time_s = df.index.to_series().astype(float) / fs
        source_start_sample = df.attrs.get("source_start_sample")
        if source_start_sample is not None:
            source_fs = df.attrs["source_sampling_rate_hz"]
            time_s = (df.index.to_series() - df.index[0]) / fs + source_start_sample / source_fs

        print(f"Analyzing all {len(df):,} samples at {fs:g} Hz")
        started = perf_counter()
        result = signal_analysis.analyze_signal(
            df[eda_column], fs=fs, time_s=time_s,
            phasic_method=analysis_settings["PHASIC_METHOD"],
            baseline_window_s=analysis_settings["PHASIC_BASELINE_WINDOW_S"],
            baseline_alignment=analysis_settings["PHASIC_BASELINE_ALIGNMENT"],
            baseline_edge=analysis_settings["PHASIC_BASELINE_EDGE"],
            threshold_us=analysis_settings["SCR_THRESHOLD_US"],
            rejection_pct=analysis_settings["SCR_REJECTION_PCT"],
        )
        scrs = result["scrs"].copy()
        scrs.insert(0, "participant_id", participant_id)
        out_path = analysis_dir / f"scr_{participant_id}.csv"
        scrs.to_csv(out_path, index=False)
        detection = result["metadata"]["scr"]
        print(
            f"Participant {participant_id}: {detection['candidate_count']} SCR candidates, "
            f"{detection['accepted_count']} accepted, {detection['rejected_count']} rejected; "
            f"phasic threshold {detection['threshold_us']:g} µS, "
            f"relative rejection {detection['rejection_pct']:g}% "
            f"({detection['rejection_threshold_us']:g} µS); "
            f"{perf_counter() - started:.2f} s\nSaved -> {out_path}"
        )
        if not charts_enabled:
            del df, result, scrs, time_s
            continue

        steps = {f"Analysis input (saved filtered EDA; {fs:g} Hz)": (result["signals"]["filtered"], time_s)}
        # Reconstruct earlier processing traces for inspection only. Analysis
        # always uses the saved filtered input, even if settings have changed.
        source_path = Path(config["SEGMENTED_DIR"]) / path.name
        try:
            source_df = file_utils.read_segmented_file(source_path, columns=[eda_column])
        except (OSError, ValueError) as error:
            print(f"WARNING: Cannot preview earlier preprocessing steps for {participant_id}: {error}")
        else:
            preview = signal_preprocessing.preprocess_signal(
                source_df[eda_column], target_fs=fs,
                fs=df.attrs.get("source_sampling_rate_hz", config["SAMPLING_RATE"]),
                resampling_method=preprocessing_settings["RESAMPLING_METHOD"],
                smoothing_window_samples=preprocessing_settings["SMOOTHING_WINDOW_SAMPLES"],
                smoothing_method=preprocessing_settings["SMOOTHING_METHOD"],
                smoothing_alignment=preprocessing_settings["SMOOTHING_ALIGNMENT"],
                smoothing_edge=preprocessing_settings["SMOOTHING_EDGE"],
                fir_filter_type=preprocessing_settings["FIR_FILTER_TYPE"],
                fir_cutoff_hz=preprocessing_settings["FIR_CUTOFF_HZ"],
                fir_window=preprocessing_settings["FIR_WINDOW"],
                fir_coefficient_mode=preprocessing_settings["FIR_COEFFICIENT_MODE"],
                fir_num_taps=preprocessing_settings["FIR_NUM_TAPS"],
                fir_optimized_factor=preprocessing_settings["FIR_OPTIMIZED_FACTOR"],
                fir_scale=preprocessing_settings["FIR_SCALE"],
                fir_delay_compensation=preprocessing_settings["FIR_DELAY_COMPENSATION"],
                fir_edge=preprocessing_settings["FIR_EDGE"],
            )
            steps = {
                **{f"Current preprocessing preview: {label}": pair
                   for label, pair in signal_plot_utils.build_preprocessing_steps(preview).items()},
                **steps,
            }
            del source_df, preview
        steps.update(signal_plot_utils.build_analysis_steps(result))

        # Export the complete overlay and display-only zooms before displaying.
        chart_dir.mkdir(parents=True, exist_ok=True)
        views = [("", None)] + [
            (f"_zoom_{number}", window_min)
            for number, window_min in enumerate(zoom_windows_min, start=1)
        ]
        title = f"Participant {participant_id}: EDA analysis"
        fig = signal_plot_utils.plot_signal_steps(steps, title=title)
        ax = fig.axes[0]
        overview_limits = ax.get_xlim()
        overview_y_limits = ax.get_ylim()
        for suffix, window_min in views:
            if window_min is None:
                view_name = "overview"
                ax.set_xlim(overview_limits)
            else:
                signal_plot_utils.set_time_range(fig, window_min)
                view_name = f"{window_min[0]:g}-{window_min[1]:g} min"
            chart_path = chart_dir / f"analysis_{participant_id}{suffix}.png"
            fig.savefig(chart_path, dpi=200, bbox_inches="tight")
            print(f"Saved analysis ({view_name}) -> {chart_path}")
        ax.set_xlim(overview_limits)
        ax.set_ylim(overview_y_limits)

        plt.show()
        plt.close(fig)
        del df, result, scrs, time_s, steps, fig, ax
