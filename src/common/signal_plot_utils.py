"""
Plot named signal steps on their original recording timeline.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_signal_steps(steps, title="EDA preprocessing", ylabel="EDA (µS)"):
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

    Returns
    -------
    matplotlib.figure.Figure
        One axis with a trace per step and recording time in minutes. The
        figure supports interactive zoom and pan; this function does not save
        or display it, interpolate signals, or change input data. An empty
        mapping raises ValueError; empty signals produce labelled empty traces.
        Misaligned signal/time indices and nonfinite times raise ValueError.
    """
    if not steps:
        raise ValueError("Provide at least one named signal step to plot.")

    # Check alignment before creating a figure, so errors leave no open window.
    for label, (signal, time_s) in steps.items():
        if not isinstance(signal, pd.Series) or not isinstance(time_s, pd.Series):
            raise TypeError(f"{label}: signal and time_s must be pandas Series.")
        if not signal.index.equals(time_s.index):
            raise ValueError(f"{label}: signal and time_s must have identical sample indices.")
        if not np.isfinite(time_s.to_numpy(dtype=float)).all():
            raise ValueError(f"{label}: time_s must contain finite recording times.")
        if not time_s.is_monotonic_increasing:
            raise ValueError(f"{label}: time_s must be in recording order.")

    fig, ax = plt.subplots(figsize=(14, 7))
    line_styles = ("-", "--", "-.", ":")
    colours = plt.get_cmap("tab10").colors

    # Distinct colours and dash patterns keep coincident steps identifiable.
    for position, (label, (signal, time_s)) in enumerate(steps.items()):
        ax.plot(
            time_s.to_numpy() / 60,
            signal.to_numpy(),
            label=label,
            color=colours[position % len(colours)],
            linestyle=line_styles[position % len(line_styles)],
            linewidth=1.5 if position == 0 else 1.0,
            alpha=0.75,
        )

    ax.set_title(title)
    ax.set_xlabel("Recording time (min)")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    # Keep the legend outside the data and avoid scanning millions of samples.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14))
    fig.tight_layout()
    return fig
