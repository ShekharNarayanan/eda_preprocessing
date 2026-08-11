import pandas as pd

def get_trial_run_lengths(mask):
    """
    Given a True/False series marking which samples belong to a trigger,
    find each separate block of True values and return how many samples
    each block contains.

    For example, if the mask looks like:
        [F, F, T, T, T, F, F, T, T, F]
    this returns [3, 2] : one block of 3 samples and one block of 2.

    Each block corresponds to one trial of that trigger condition.
    """
    trial_started = mask & ~mask.shift(1, fill_value=False)
    trial_id      = trial_started.cumsum()
    trial_lengths = mask.groupby(trial_id).sum()
    return trial_lengths



def get_run_boundaries(mask, fs=2000):
    """
    Given a True/False series, find each consecutive block of True values
    and return their start index, end index, and duration.

    This is a generic helper used to detect both trial periods (when a
    trigger is active) and unknown pin combination periods.

    Parameters
    ----------
    mask : True/False series over the recording timeline
    fs   : the number of samples recorded per second (default 2000)

    Returns
    -------
    A table with one row per block showing:
        onset            : sample index where the block starts
        offset           : sample index where the block ends
        duration_samples : how many samples the block contained
        duration_s       : how many seconds the block lasted
    """
    if mask.sum() == 0:
        return pd.DataFrame(columns=["onset", "offset", "duration_samples", "duration_s"])

    block_started = mask & ~mask.shift(1,  fill_value=False)
    block_ended   = mask & ~mask.shift(-1, fill_value=False)
    onsets  = mask.index[block_started]
    offsets = mask.index[block_ended]
    lengths = offsets - onsets + 1

    return pd.DataFrame({
        "onset":            onsets,
        "offset":           offsets,
        "duration_samples": lengths,
        "duration_s":       (lengths / fs).round(3),
    })


def get_trial_boundaries(trigger_map, fs=2000):
    """
    For each trigger, find the exact start and end of every individual trial
    in the recording and return them as a single table sorted by time.

    This gives you a row-per-trial event log of the entire session, which
    is the starting point for epoching the EDA signal later.

    Returns
    -------
    A table with one row per trial showing:
        trigger          : which condition this trial belongs to
        onset            : the sample index where the trial starts
        offset           : the sample index where the trial ends
        duration_samples : how many samples the trial lasted
        duration_s       : how many seconds the trial lasted
    """
    all_boundaries = []
    for trig_id, mask in trigger_map.items():
        b = get_run_boundaries(mask, fs)
        if b.empty:
            continue
        b["trigger"] = trig_id
        all_boundaries.append(b)

    if not all_boundaries:
        return pd.DataFrame(columns=["trigger", "onset", "offset",
                                     "duration_samples", "duration_s"])

    result = pd.concat(all_boundaries).sort_values("onset").reset_index(drop=True)
    return result[["trigger", "onset", "offset", "duration_samples", "duration_s"]]
