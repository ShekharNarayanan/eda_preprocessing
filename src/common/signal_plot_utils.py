"""
Plot named signal steps on their original recording timeline.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def build_preprocessing_steps(result):
    """
    Pair all EDA preprocessing steps with their exact recording-time grids.

    Parameters
    ----------
    result : dict
        Signals, timelines, and metadata returned by preprocess_signal.

    Returns
    -------
    dict
        Ordered descriptive labels mapped to (signal, time_s) Series pairs,
        suitable for plot_signal_steps and plot_preprocessing. Empty signals
        retain all four labelled steps. No signal data are copied or cropped.
    """
    signals = result["signals"]
    timeline = result["timeline"]
    metadata = result["metadata"]
    smoothing = metadata["smoothing"]
    fir = metadata["fir"]
    return {
        f"Original ({metadata['original_fs']:g} Hz)": (signals["raw"], result["raw_time_s"]),
        (
            f"Resampled ({metadata['processed_fs']:g} Hz; "
            f"{metadata['resampling']['method']})"
        ): (signals["resampled"], timeline["time_s"]),
        (
            f"Smoothed ({smoothing['method']}; {smoothing['window_samples']} samples; "
            f"{smoothing['alignment']}; {smoothing['edge']} edges)"
        ): (signals["smoothed"], timeline["time_s"]),
        (
            f"FIR ({fir['filter_type']}; {fir['cutoff_hz']:g} Hz; {fir['window']}; "
            f"{fir['num_taps']} taps, {fir['coefficient_mode']}; "
            f"gain {'normalized' if fir['scale'] else 'unscaled'}; "
            f"delay {'compensated' if fir['delay_compensation'] else 'retained'}; {fir['edge']} edges)"
        ): (signals["filtered"], timeline["time_s"]),
    }


def build_analysis_steps(result):
    """
    Pair baseline and phasic signals with their exact recording seconds.

    Parameters
    ----------
    result : dict
        Output of analyze_signal, including signals, timeline, and metadata.

    Returns
    -------
    dict
        Two labelled (signal, time_s) pairs for extending a preprocessing
        overlay. Labels include the active baseline settings. No samples are
        copied or cropped; empty results retain both labelled traces.
    """
    settings = result["metadata"]["phasic"]
    description = (
        f"median; {settings['baseline_window_s']:g} s, "
        f"{settings['baseline_window_samples']} samples; "
        f"{settings['baseline_alignment']}; {settings['baseline_edge']} edges"
    )
    time_s = result["timeline"]["time_s"]
    return {
        f"Estimated baseline ({description})": (result["signals"]["baseline"], time_s),
        f"Phasic (filtered − estimated baseline; {description})": (result["signals"]["phasic"], time_s),
    }


def _validate_steps(steps):
    """
    Validate signal/time pairs before creating any figure.
    """
    if not steps:
        raise ValueError("Provide at least one named signal step to plot.")

    for label, (signal, time_s) in steps.items():
        if not isinstance(signal, pd.Series) or not isinstance(time_s, pd.Series):
            raise TypeError(f"{label}: signal and time_s must be pandas Series.")
        if not signal.index.equals(time_s.index):
            raise ValueError(f"{label}: signal and time_s must have identical sample indices.")
        if not np.isfinite(time_s.to_numpy(dtype=float)).all():
            raise ValueError(f"{label}: time_s must contain finite recording times.")
        if not time_s.is_monotonic_increasing:
            raise ValueError(f"{label}: time_s must be in recording order.")


def _validate_time_range(time_range_min):
    """
    Check an optional display interval in recording minutes.
    """
    if time_range_min is not None:
        bounds = np.asarray(time_range_min, dtype=float)
        if bounds.shape != (2,) or not np.isfinite(bounds).all() or bounds[0] >= bounds[1]:
            raise ValueError("time_range_min must contain two finite, increasing recording minutes.")


def _draw_signal_steps(ax, steps, positions=None):
    """
    Draw aligned traces with consistent colours and styles across panels.
    """
    line_styles = ("-", "--", "-.", ":")
    colours = plt.get_cmap("tab10").colors
    if positions is None:
        positions = {label: position for position, label in enumerate(steps)}

    # Distinct colours and dash patterns keep coincident steps identifiable.
    for label, (signal, time_s) in steps.items():
        position = positions[label]
        ax.plot(
            time_s.to_numpy() / 60,
            signal.to_numpy(),
            label=label,
            color=colours[position % len(colours)],
            linestyle=line_styles[position % len(line_styles)],
            linewidth=1.5 if position == 0 else 1.0,
            alpha=0.75,
        )
    ax.set_ylabel("EDA (µS)")
    ax.grid(alpha=0.2)


def set_time_range(fig, time_range_min, rescale_y=True):
    """
    Set linked display limits in recording minutes without replacing trace data.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        A figure from plot_signal_steps, plot_preprocessing, or plot_analysis.
    time_range_min : pair of numbers
        Finite, increasing recording-minute limits. Interactive pan retains
        the complete signal, including samples outside the displayed span.
    rescale_y : bool
        Fit vertical limits to visible samples, so artifacts elsewhere in
        the recording do not flatten a zoom. False keeps the existing limits.

    Returns
    -------
    None
        Updates the figure in place without displaying or saving it.
    """
    _validate_time_range(time_range_min)
    if time_range_min is None:
        raise ValueError("Provide two recording-minute limits to set the view.")
    fig.axes[-1].set_xlim(time_range_min)
    if rescale_y:
        for ax in fig.axes:
            visible_limits = []
            for line in ax.lines:
                # Ignore annotations such as axhline, whose x values are axes fractions.
                if line.get_transform() != ax.transData:
                    continue
                time_min = line.get_xdata()
                values = line.get_ydata()
                start = np.searchsorted(time_min, time_range_min[0], side="left")
                stop = np.searchsorted(time_min, time_range_min[1], side="right")
                visible = values[start:stop]
                visible = visible[np.isfinite(visible)]
                if visible.size:
                    visible_limits.extend([visible.min(), visible.max()])
            if visible_limits:
                lower, upper = min(visible_limits), max(visible_limits)
                margin = (upper - lower) * 0.05 if upper > lower else max(abs(lower) * 0.05, 0.05)
                ax.set_ylim(lower - margin, upper + margin)


def plot_signal_steps(steps, title="EDA preprocessing", ylabel="EDA (µS)", *, time_range_min=None):
    """
    Superimpose all supplied signal steps with a labelled legend.

    Parameters
    ----------
    steps : dict
        Ordered mapping of legend label to (signal, time_s). Both values are
        pandas Series with identical sample indices and lengths for that step.
        time_s contains recording seconds, including any nonzero trial origin.
        Different steps may have different sample counts and sampling rates.
        Supply signals in their processing order and in the same units.
    title : str
        Figure title, normally identifying the participant and supplied span.
    ylabel : str
        Signal name and units for the shared vertical axis.
    time_range_min : pair of numbers or None
        Display limits in recording minutes. None shows the overview. Limits
        affect the view only; all supplied samples remain in the figure.

    Returns
    -------
    matplotlib.figure.Figure
        One axis with a trace per step and recording time in minutes. The
        figure supports interactive zoom and pan; this function does not save
        or display it, interpolate signals, or change input data. An empty
        mapping raises ValueError; empty signals produce labelled empty traces.
        Misaligned signal/time indices and nonfinite times raise ValueError.
    """
    _validate_steps(steps)
    _validate_time_range(time_range_min)
    fig, ax = plt.subplots(figsize=(14, 7))
    _draw_signal_steps(ax, steps)

    ax.set_title(title)
    ax.set_xlabel("Recording time (min)")
    ax.set_ylabel(ylabel)
    if time_range_min is not None:
        set_time_range(fig, time_range_min)
    # Keep the legend outside the data and avoid scanning millions of samples.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14))
    fig.tight_layout()
    return fig


def plot_preprocessing(
    steps, title="EDA preprocessing", *, reference=None, show_difference=False,
    time_range_min=None,
):
    """
    Show each preprocessing step on linked time axes.

    Parameters
    ----------
    steps : dict
        Ordered label to (signal, time_s) pairs, as for plot_signal_steps.
        The first step is raw EDA and the last is filtered EDA, in µS. Each
        step uses its own recording-time grid, including nonzero origins.
    title : str
        Figure title, normally identifying the participant.
    reference : pair of pandas.Series or None
        Optional (signal, time_s) for an independent filtered EDA reference
        in µS and recording seconds, drawn on the filtered panel. Its grid
        may differ from the Python grid.
    show_difference : bool
        Add filtered minus reference in µS. Requires a reference with finite
        values and strictly increasing times. Interpolate the reference onto
        filtered times only within their common span; never extrapolate. An
        empty reference or no overlap produces a labelled empty trace.
    time_range_min : pair of numbers or None
        Linked display limits in recording minutes; None shows the overview.
        Zooming never crops the data supplied to processing or plotting.

    Returns
    -------
    matplotlib.figure.Figure
        A panel per step and optionally a difference panel. Colours and
        styles match the separate superimposed view.
        All time axes are linked for interactive zoom and pan. This function
        does not display or save figures. Empty signals are valid; an empty
        mapping or invalid alignment raises before creating a figure.
    """
    _validate_steps(steps)
    _validate_time_range(time_range_min)
    if show_difference and reference is None:
        raise ValueError("A reference is required to show a difference trace.")
    if reference is not None:
        _validate_steps({"Reference": reference})
        reference_signal, reference_time_s = reference
        if show_difference:
            if not reference_time_s.is_unique:
                raise ValueError("Reference times must be strictly increasing for a difference trace.")
            if not np.isfinite(reference_signal.to_numpy(dtype=float)).all():
                raise ValueError("Reference values must be finite for a difference trace.")

    n_panels = len(steps) + bool(show_difference)
    fig, axes = plt.subplots(
        n_panels, 1, figsize=(14, 2.8 * n_panels), sharex=True, squeeze=False,
    )
    axes = axes[:, 0]
    positions = {label: position for position, label in enumerate(steps)}
    for ax, (label, pair) in zip(axes, steps.items()):
        _draw_signal_steps(ax, {label: pair}, positions)
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), borderaxespad=0, fontsize=9)

    labels = list(steps)
    # Compare any independent reference on the existing filtered panel.
    if reference is not None:
        positions["AcqKnowledge reference"] = len(steps)
        filtered_ax = axes[len(steps) - 1]
        _draw_signal_steps(filtered_ax, {"AcqKnowledge reference": reference}, positions)
        filtered_ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), borderaxespad=0, fontsize=9)

    if show_difference:
        filtered, filtered_time_s = steps[labels[-1]]
        mask = pd.Series(False, index=filtered.index)
        if not reference_time_s.empty:
            mask = (
                (filtered_time_s >= reference_time_s.iloc[0])
                & (filtered_time_s <= reference_time_s.iloc[-1])
            )
        difference_time_s = filtered_time_s.loc[mask]
        reference_values = (
            np.interp(difference_time_s, reference_time_s, reference_signal)
            if mask.any() else np.array([], dtype=float)
        )
        difference = filtered.loc[mask] - reference_values
        _draw_signal_steps(
            axes[-1], {"Filtered − reference (linear alignment)": (difference, difference_time_s)},
        )
        axes[-1].axhline(0, color="0.5", linewidth=0.7)
        axes[-1].set_ylabel("Difference (µS)")
        axes[-1].legend(loc="lower left", bbox_to_anchor=(0, 1.02), borderaxespad=0, fontsize=9)

    axes[-1].set_xlabel("Recording time (min)")
    if time_range_min is not None:
        set_time_range(fig, time_range_min)
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_analysis(result, title="EDA phasic derivation and SCR detection", *, time_range_min=None):
    """
    Show baseline removal and SCR decisions on linked filtered/phasic panels.

    Parameters
    ----------
    result : dict
        Output of analyze_signal. SCR onset/peak/end are integer positions on
        its signal index; timeline.time_s gives exact recording seconds.
        Accepted and rejected candidates retain separate event markers.
    title : str
        Figure title, normally identifying the participant or supplied trial.
    time_range_min : pair of numbers or None
        Display-only recording-minute limits. All samples remain available
        for interactive zoom and pan; None shows the complete supplied span.

    Returns
    -------
    matplotlib.figure.Figure
        Two linked panels with legends naming the baseline settings,
        detection/rejection thresholds, and onset/peak/end decisions.
        Incomplete responses show only observed event positions and are
        labelled with their rejection reason. Empty signals and event tables
        are valid. This function neither saves nor displays the figure.
    """
    time_s = result["timeline"]["time_s"]
    steps = {"Filtered EDA": (result["signals"]["filtered"], time_s)}
    steps.update(build_analysis_steps(result))
    _validate_steps(steps)
    _validate_time_range(time_range_min)
    scrs = result["scrs"]
    settings = result["metadata"]["scr"]
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    positions = {label: position for position, label in enumerate(steps)}
    labels = list(steps)
    _draw_signal_steps(axes[0], {label: steps[label] for label in labels[:2]}, positions)
    _draw_signal_steps(axes[1], {labels[-1]: steps[labels[-1]]}, positions)
    axes[1].set_ylabel("Phasic EDA (µS)")
    axes[1].axhline(0, color="0.5", linewidth=0.7)
    axes[1].axhline(
        settings["threshold_us"], color="tab:orange", linestyle="--", linewidth=0.8,
        label=f"Detection H = {settings['threshold_us']:g} µS (onset > H)",
    )
    axes[1].axhline(
        settings["rejection_threshold_us"], color="tab:red", linestyle=":", linewidth=0.8,
        label=(f"Rejection = {settings['rejection_pct']:g}% of phasic max "
               f"= {settings['rejection_threshold_us']:g} µS"),
    )

    # Vectorized marker groups preserve event positions without creating an
    # artist for every response. Peak markers use the FILTERED EDA maximum.
    for (status, reason), group in scrs.groupby(["status", "rejection_reason"], sort=False):
        description = "Accepted SCR" if status == "accepted" else f"Rejected ({reason.replace('_', ' ')})"
        colour = "tab:green" if status == "accepted" else "tab:red"
        for event, marker in (("onset", "o"), ("peak", "^"), ("end", "v")):
            samples = group[event].dropna().astype(int)
            if samples.empty:
                continue
            for ax, signal_name in zip(axes, ("filtered", "phasic")):
                ax.plot(
                    time_s.loc[samples].to_numpy() / 60,
                    result["signals"][signal_name].loc[samples].to_numpy(),
                    linestyle="none", marker=marker, markersize=5,
                    markerfacecolor="none" if status == "rejected" else colour,
                    markeredgecolor=colour, label=f"{description}: {event}",
                )

    for ax in axes:
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), fontsize=8, ncol=3)
    axes[-1].set_xlabel("Recording time (min)")
    if time_range_min is not None:
        set_time_range(fig, time_range_min)
    fig.suptitle(title)
    fig.tight_layout()
    return fig
