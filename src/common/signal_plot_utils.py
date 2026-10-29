"""
Plot named signal steps on their original recording timeline.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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
        A figure from plot_signal_steps or plot_preprocessing.
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
