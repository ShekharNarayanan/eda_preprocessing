import pandas as pd
from src.inspect_data import get_matched_mask, get_run_boundaries


def get_unknown_pin_combo_mask(df, trigger_cols, trigger_map):
    """
    Return a True/False series that is True for every row whose pin
    combination is not in the codebook and not all-zero. These are the
    anomalous rows to be excluded from downstream analysis.

    Parameters
    ----------
    df           : the full dataframe with the 8 binarized pin columns
    trigger_cols : the list of 8 pin column names
    trigger_map  : dictionary of trigger ID to boolean mask

    Returns
    -------
    A pandas Series of booleans, indexed the same as df.
    """
    matched  = get_matched_mask(trigger_map)
    baseline = (df[trigger_cols] == 0).all(axis=1)
    return ~matched & ~baseline


def build_trigger_column(df, trigger_cols, trigger_map):
    """
    Build a single integer column that summarises the trigger state at
    every sample of the recording.

    Each row gets one of three kinds of value:
        -1   : the pin combination at that row is not in the codebook
         0   : baseline (all 8 pins are off)
         N   : the trigger ID of the trial active at that row

    Parameters
    ----------
    df           : the full dataframe with the 8 binarized pin columns
    trigger_cols : the list of 8 pin column names
    trigger_map  : dictionary of trigger ID to boolean mask

    Returns
    -------
    A pandas Series of integers, indexed the same as df.
    """
    trigger = pd.Series(0, index=df.index, dtype=int)

    # assign trigger IDs to matched rows
    for trig_id, mask in trigger_map.items():
        trigger.loc[mask] = trig_id

    # label remaining non-zero pin rows as unknown pin combinations
    unknown_pin_combo = get_unknown_pin_combo_mask(df, trigger_cols, trigger_map)
    trigger.loc[unknown_pin_combo] = -1

    return trigger


def build_clean_dataset(df, trigger_cols, trigger_map, fs=2000):
    """
    Take the raw dataframe with 8 trigger pin columns and produce an
    analysis-ready dataframe with one trigger column instead.

    The 8 pin columns are dropped. A new 'trigger' column is added where
    each sample is labelled with the trigger ID of the active trial, 0
    for baseline rows, or -1 for rows with an unknown pin combination
    that should be excluded from downstream analysis.

    Parameters
    ----------
    df           : the full dataframe with the 8 binarized pin columns
                   and any other signal columns (EDA, ECG, etc.)
    trigger_cols : the list of 8 pin column names
    trigger_map  : dictionary of trigger ID to boolean mask
    fs           : sampling rate in Hz (default 2000)

    Returns
    -------
    clean_df           : original signal columns plus a single 'trigger' column
    report             : dictionary with sample counts, durations, and
                         percentages for matched, baseline, and unknown
                         pin combo categories
    unknown_pin_combos : table of unknown-pin-combo periods with onset,
                         offset, and duration, useful for logging or
                         inspection
    """
    total = len(df)

    trigger            = build_trigger_column(df, trigger_cols, trigger_map)
    unknown_pin_combo  = get_unknown_pin_combo_mask(df, trigger_cols, trigger_map)
    unknown_pin_combos = get_run_boundaries(unknown_pin_combo, fs)

    clean_df = df.drop(columns=trigger_cols).copy()
    clean_df["trigger"] = trigger

    n_matched           = (trigger > 0).sum()
    n_baseline          = (trigger == 0).sum()
    n_unknown_pin_combo = (trigger == -1).sum()

    

    report = {
        "total_samples":              total,
        "total_duration_min":         round(total / (fs * 60), 2),
        "matched_samples":            int(n_matched),
        "matched_pct":                round(100 * n_matched / total, 1),
        "baseline_samples":           int(n_baseline),
        "baseline_pct":               round(100 * n_baseline / total, 1),
        "unknown_pin_combo_samples":  int(n_unknown_pin_combo),
        "unknown_pin_combo_pct":      round(100 * n_unknown_pin_combo / total, 1),
        "unknown_pin_combo_periods":  len(unknown_pin_combos),
    }

    return clean_df, report, unknown_pin_combos

def get_unknown_pin_combos_breakdown(df, trigger_cols, trigger_map, fs=2000):
    """
    Return a table summarising which pin combinations did not match any
    trigger in the codebook. Each row of the returned table is one unique
    unmatched combination, with the 8 pin values and statistics about
    how often it occurred.

    Parameters
    ----------
    df           : the full dataframe with the 8 binarized pin columns
    trigger_cols : the list of 8 pin column names
    trigger_map  : dictionary of trigger ID to boolean mask
    fs           : sampling rate in Hz (default 2000)

    Returns
    -------
    A table with one row per unique unmatched pin combination, columns:
        - the 8 pin column values (0 or 1)
        - count        : how many samples had this combination
        - duration_min : how many minutes of recording it accounted for
        - pct          : percentage of the total recording
    """
    total = len(df)
    unknown_pin_combo = get_unknown_pin_combo_mask(df, trigger_cols, trigger_map)

    if unknown_pin_combo.sum() == 0:
        return pd.DataFrame(columns=trigger_cols + ['count', 'duration_min', 'pct'])

    breakdown = df[unknown_pin_combo][trigger_cols].value_counts().reset_index()
    breakdown['duration_min'] = (breakdown['count'] / (fs * 60)).round(2)
    breakdown['pct']          = (100 * breakdown['count'] / total).round(1)

    return breakdown

def get_unknown_spans_minutes(unknown_pin_combos, fs=2000):
    """
    Convert the onset and offset sample indices of each unknown pin combo
    period into start and end times in minutes.

    Each unknown pin combo period is treated the same way as a trial: a
    contiguous block with a start and an end. This returns two lists, one
    of start times and one of end times, in the order the periods occur in
    the recording. Intended for human reading in the summary report.

    Parameters
    ----------
    unknown_pin_combos : the boundaries table returned by build_clean_dataset,
                         with one row per unknown pin combo period
    fs                 : sampling rate in Hz (default 2000)

    Returns
    -------
    start_min : list of period start times in minutes
    end_min   : list of period end times in minutes
    """
    if unknown_pin_combos.empty:
        return [], []

    start_min = (unknown_pin_combos["onset"]  / (fs * 60)).round(1).tolist()
    end_min   = (unknown_pin_combos["offset"] / (fs * 60)).round(1).tolist()
    return start_min, end_min