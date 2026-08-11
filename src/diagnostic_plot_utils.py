import matplotlib.pyplot as plt


def get_span_bars(spans, fs=2000, min_bar_min=0.1):
    """
    Convert one participant's periods into the (start, width) pairs that
    matplotlib needs to draw horizontal bars on a timeline.

    Both numbers are in minutes. Very short periods are widened to
    min_bar_min so that they stay visible on an hour long axis. This means
    the width of a short bar is not a faithful picture of its duration, so
    exact durations should be read from the summary table rather than from
    the plot.

    Parameters
    ----------
    spans       : a boundaries table for one participant, with one row per
                  period and columns onset and duration_samples
    fs          : sampling rate in Hz (default 2000)
    min_bar_min : smallest bar width to draw, in minutes

    Returns
    -------
    A list of (start_min, width_min) pairs, one per period.
    """
    bars = []

    for row in spans.itertuples():
        start_min = row.onset / (fs * 60)
        width_min = row.duration_samples / (fs * 60)

        if width_min < min_bar_min:
            width_min = min_bar_min

        bars.append((start_min, width_min))

    return bars


def plot_unknown_timeline(bars_per_participant, recording_length_min,
                          participants_per_figure=25, min_bar_min=0.1,
                          bar_colour="#D85A30"):
    """
    Draw one horizontal timeline row per participant showing when unknown
    pin combo periods happened and roughly how long they lasted.

    Every row uses the same x axis so that positions can be compared across
    participants. If there are more participants than participants_per_figure
    they are split across several figures, which keeps each figure a readable
    height instead of producing one very tall image.

    Parameters
    ----------
    bars_per_participant    : dictionary of participant ID to the list of
                              (start_min, width_min) pairs for that participant
    recording_length_min    : how long the x axis should be, in minutes
    participants_per_figure : how many rows to draw on one figure
    min_bar_min             : the bar width floor that was used when the bars
                              were built. It is only used for the note printed
                              under the axis, so pass the same value that was
                              given to get_span_bars, otherwise the note will
                              not describe what was actually drawn.
    bar_colour              : colour of the bars

    Returns
    -------
    A list of matplotlib figures, one per page of participants.
    """
    participant_ids = list(bars_per_participant.keys())
    figures         = []

    # Split the participants into pages so that no single figure gets too tall.
    for page_start in range(0, len(participant_ids), participants_per_figure):
        page_ids = participant_ids[page_start:page_start + participants_per_figure]

        # The height of the figure grows with the number of rows on this page.
        fig_height = 1.5 + 0.3 * len(page_ids)
        fig, ax    = plt.subplots(figsize=(11, fig_height))

        # Rows are drawn from the top down, so the first participant on the
        # page gets the highest y position.
        for row_number, participant_id in enumerate(page_ids):
            bars       = bars_per_participant[participant_id]
            y_position = len(page_ids) - row_number - 1

            if not bars:
                ax.text(recording_length_min / 2, y_position, "no unknown spans",
                        ha="center", va="center", fontsize=8, color="grey")
                continue

            ax.broken_barh(bars, (y_position - 0.35, 0.7),
                           facecolors=bar_colour, edgecolors="none")

        ax.set_yticks(range(len(page_ids)))
        ax.set_yticklabels(list(reversed(page_ids)), fontsize=9)
        ax.set_ylim(-0.7, len(page_ids) - 0.3)

        ax.set_xlim(0, recording_length_min)
        ax.set_xlabel("minutes into recording")
        ax.grid(axis="x", linestyle=":", linewidth=0.5, alpha=0.6)
        ax.set_axisbelow(True)

        page_number = page_start // participants_per_figure + 1
        total_pages = (len(participant_ids) - 1) // participants_per_figure + 1

        title = "Unknown pin combo periods"
        if total_pages > 1:
            title = f"{title} (page {page_number} of {total_pages})"
        ax.set_title(title, fontsize=11, loc="left")

        # The note sits below the axis label. Space for it is reserved as a
        # fraction of the figure height, because the figure height changes with
        # the number of participants and a fixed fraction would either overlap
        # the label on tall figures or leave a large gap on short ones.
        note_height  = 0.3
        note_fraction = note_height / fig_height

        fig.tight_layout(rect=[0, note_fraction, 1, 1])

        note = f"bars narrower than {min_bar_min} min are drawn at that width"
        fig.text(0.01, note_fraction / 3, note, fontsize=7, color="grey")

        figures.append(fig)

    return figures


def plot_gap_to_first_trial(gaps_per_participant, bar_colour="#3D7A99",
                            negative_colour="#D85A30"):
    """
    Draw one horizontal bar per participant showing how much time passed
    between the end of the last unknown pin combo period and the start of
    the first recognised trial.

    Participants are sorted by gap length rather than by ID, so the shortest
    and longest gaps sit together at the ends of the plot.

    This assumes the unknown period sits at the start of the recording and
    finishes before any trial begins. A negative gap means that assumption
    did not hold for that participant, because an unknown period was found
    after the first trial. Those bars are drawn in a different colour so
    they are not read as ordinary short gaps.

    Parameters
    ----------
    gaps_per_participant : dictionary of participant ID to gap in seconds
    bar_colour           : colour for positive gaps
    negative_colour      : colour for negative gaps, which mean an unknown
                           period was found after the first trial

    Returns
    -------
    A single matplotlib figure.
    """
    sorted_items    = sorted(gaps_per_participant.items(), key=lambda item: item[1])
    participant_ids = [participant_id for participant_id, gap in sorted_items]
    gaps_s          = [gap for participant_id, gap in sorted_items]

    colours = []
    for gap in gaps_s:
        colours.append(negative_colour if gap < 0 else bar_colour)

    fig_height = 1.5 + 0.3 * len(participant_ids)
    fig, ax    = plt.subplots(figsize=(9, fig_height))

    y_positions = range(len(participant_ids))
    ax.barh(y_positions, gaps_s, color=colours, height=0.7)

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(participant_ids, fontsize=9)
    ax.set_ylim(-0.7, len(participant_ids) - 0.3)

    ax.axvline(0, color="grey", linewidth=0.8)
    ax.set_xlabel("seconds between end of unknown period and first trial")
    ax.grid(axis="x", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    ax.set_title("Gap from unknown pin combo period to first trial",
                 fontsize=11, loc="left")

    # Space for the note is reserved as a fraction of the figure height, so it
    # never lands on top of the axis label however tall the figure gets.
    has_note      = any(gap < 0 for gap in gaps_s)
    note_height   = 0.3 if has_note else 0.0
    note_fraction = note_height / fig_height

    fig.tight_layout(rect=[0, note_fraction, 1, 1])

    if has_note:
        note = "bars left of zero mean unknown periods were found after the first trial"
        fig.text(0.01, note_fraction / 3, note, fontsize=7, color="grey")

    return fig