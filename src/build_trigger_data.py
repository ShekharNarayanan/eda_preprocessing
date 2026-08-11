import pandas as pd
from src.trigger_codebook import get_matched_mask
from src.trial_boundaries import get_run_boundaries

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
    all_pins_off = (df[trigger_cols] == 0).all(axis=1)
    return ~matched & ~all_pins_off


def build_trigger_column(df, trigger_cols, trigger_map):
    """
    Build a single integer column that summarises the trigger state at
    every sample of the recording.

    Each row gets one of three kinds of value:
        -1   : the pin combination at that row is not in the codebook
         0   : all pins off (none of the 8 pins are on)
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
    for rows where all pins are off, or -1 for rows with an unknown pin
    combination that should be excluded from downstream analysis.

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
                         percentages for matched, all pins off, and
                         unknown pin combo categories
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
    n_all_pins_off      = (trigger == 0).sum()
    n_unknown_pin_combo = (trigger == -1).sum()

    

    report = {
        "total_samples":              total,
        "total_duration_min":         round(total / (fs * 60), 2),
        "matched_samples":            int(n_matched),
        "matched_pct":                round(100 * n_matched / total, 1),
        "all_pins_off_samples":       int(n_all_pins_off),
        "all_pins_off_pct":           round(100 * n_all_pins_off / total, 1),
        "unknown_pin_combo_samples":  int(n_unknown_pin_combo),
        "unknown_pin_combo_pct":      round(100 * n_unknown_pin_combo / total, 1),
        "unknown_pin_combo_periods":  len(unknown_pin_combos),
    }

    return clean_df, report, unknown_pin_combos



