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


def get_matched_mask(trigger_map):
    """
    Given all the trigger masks, return a single True/False series
    that is True for any row that belongs to at least one trigger condition,
    and False for every other row.
    """
    masks = list(trigger_map.values())
    return pd.concat(masks, axis=1).any(axis=1)


def summarize_triggers(trigger_map, fs=2000):
    """
    For each trigger condition, count how many samples and trials exist
    in the data and compute how long each trial lasted on average.

    A 'trial' is a consecutive block of samples belonging to the same
    trigger : i.e. one stimulus presentation. This function counts how
    many such blocks exist per trigger and summarises their durations.

    Parameters
    ----------
    trigger_map : a dictionary where each key is a trigger number (e.g. 145)
                  and each value is a True/False series marking which rows
                  in the dataframe belong to that trigger
    fs          : the number of samples recorded per second (default 2000)

    Returns
    -------
    A table with one row per trigger showing:
        - how many samples and seconds of data exist in total
        - how many individual trials were found
        - the average, shortest, and longest trial duration in seconds
    """
    rows = []

    for trig_id, mask in trigger_map.items():
        total_samples = mask.sum()
        if total_samples == 0:
            rows.append({"trigger": trig_id, "total_samples": 0,
                         "total_duration_s": 0.0, "n_trials": 0,
                         "mean_duration_s": 0.0, "min_duration_s": 0.0,
                         "max_duration_s": 0.0})
            continue

        trial_lengths = get_trial_run_lengths(mask)

        rows.append({
            "trigger":          trig_id,
            "total_samples":    total_samples,
            "total_duration_s": round(total_samples / fs, 2),
            "n_trials":         len(trial_lengths),
            "mean_duration_s":  round(trial_lengths.mean() / fs, 3),
            "min_duration_s":   round(trial_lengths.min()  / fs, 3),
            "max_duration_s":   round(trial_lengths.max()  / fs, 3),
        })

    return pd.DataFrame(rows).sort_values("trigger").reset_index(drop=True)


def summarize_data(df, trigger_cols, trigger_map, fs=2000):
    """
    Give an overview of what every row in the recording actually contains.

    At 2000 Hz, most rows in the dataframe are not stimulus events :
    they are either silent (all pins off) or carry some pin combination
    that does not match any of the 16 known triggers. This function
    splits every row into exactly one of three buckets:

        matched   : the row belongs to a known trigger condition
        baseline  : all 8 pin columns are zero (no signal at all)
        unknown   : some pins are on, but the combination does not match
                    any trigger in the codebook

    If unknown rows exist, their pin combinations are printed so you can
    investigate what they represent.

    Parameters
    ----------
    df           : the full dataframe with the 8 binarized pin columns
    trigger_cols : the list of 8 column names representing the parallel port pins
    trigger_map  : a dictionary where each key is a trigger number and each
                   value is a True/False series marking which rows belong to it
    fs           : the number of samples recorded per second (default 2000)
    """
    total = len(df)

    matched  = get_matched_mask(trigger_map)
    baseline = (df[trigger_cols] == 0).all(axis=1)
    unknown  = ~matched & ~baseline

    n_matched  = matched.sum()
    n_baseline = baseline.sum()
    n_unknown  = unknown.sum()

    def fmt(n):
        return f"{n:10,}  ({100*n/total:5.1f}%)  ~{n/(fs*60):5.2f} min"

    print(f"Total rows      : {total:,} (~{total/(fs*60):.2f} min @ {fs}Hz)")
    print("-" * 55)
    print(f"Matched         : {fmt(n_matched)}")
    print(f"Baseline (zeros): {fmt(n_baseline)}")
    print(f"Unknown combos  : {fmt(n_unknown)}")
    print("-" * 55)
    assert n_matched + n_baseline + n_unknown == total, "rows don't add up!"

    if n_unknown > 0:
        print("\nPer unknown combination:")
        top = df[unknown][trigger_cols].value_counts().reset_index()
        top['duration_min'] = (top['count'] / (fs * 60)).round(2)
        top['pct']          = (100 * top['count'] / total).round(1)
        top = top.drop(columns='count')
        print(top.to_string(index=False))



def get_trial_boundaries(trigger_map, fs=2000):
    """
    For each trigger, find the exact start and end of every individual trial
    in the recording and return them as a single table sorted by time.

    This gives you a row-per-trial event log of the entire session, which
    is the starting point for epoching the EDA signal later.

    Parameters
    ----------
    trigger_map : a dictionary where each key is a trigger number and each
                  value is a True/False series marking which rows belong to it
    fs          : the number of samples recorded per second (default 2000)

    Returns
    -------
    A table with one row per trial showing:
        trigger          — which condition this trial belongs to
        onset            — the sample index where the trial starts
        offset           — the sample index where the trial ends
        duration_samples — how many samples the trial lasted
        duration_s       — how many seconds the trial lasted
    """
    rows = []

    for trig_id, mask in trigger_map.items():
        if mask.sum() == 0:
            continue

        trial_started = mask & ~mask.shift(1,  fill_value=False)
        trial_ended   = mask & ~mask.shift(-1, fill_value=False)
        onsets  = mask.index[trial_started]
        offsets = mask.index[trial_ended]
        lengths = offsets - onsets + 1

        for onset, offset, length in zip(onsets, offsets, lengths):
            rows.append({
                "trigger":          trig_id,
                "onset":            onset,
                "offset":           offset,
                "duration_samples": length,
                "duration_s":       round(length / fs, 3),
            })

    return pd.DataFrame(rows).sort_values("onset").reset_index(drop=True)