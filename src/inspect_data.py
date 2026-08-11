import pandas as pd
from trigger_utils import get_matched_mask
from trial_boundaries import get_trial_run_lengths




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
    This function splits every row into exactly one of three buckets:

        matched           : the row belongs to a known trigger condition
        all pins off      : all 8 pin columns are zero (no pin is active)
        unknown pin combo : some pins are on, but the combination does not
                            match any trigger in the codebook

    If unknown pin combos exist, their pin combinations are printed so
    you can investigate what they represent.
    """
    total = len(df)

    matched           = get_matched_mask(trigger_map)
    all_pins_off      = (df[trigger_cols] == 0).all(axis=1)
    unknown_pin_combo = ~matched & ~all_pins_off

    n_matched           = matched.sum()
    n_all_pins_off      = all_pins_off.sum()
    n_unknown_pin_combo = unknown_pin_combo.sum()

    def fmt(n):
        return f"{n:10,}  ({100*n/total:5.1f}%)  ~{n/(fs*60):5.2f} min"

    print(f"Total rows         : {total:,} (~{total/(fs*60):.2f} min @ {fs}Hz)")
    print("-" * 58)
    print(f"Matched            : {fmt(n_matched)}")
    print(f"All pins off       : {fmt(n_all_pins_off)}")
    print(f"Unknown pin combos : {fmt(n_unknown_pin_combo)}")
    print("-" * 58)
    assert n_matched + n_all_pins_off + n_unknown_pin_combo == total, "rows don't add up!"

    if n_unknown_pin_combo > 0:
        print("\nPer unknown pin combination:")
        top = df[unknown_pin_combo][trigger_cols].value_counts().reset_index()
        top['duration_min'] = (top['count'] / (fs * 60)).round(2)
        top['pct']          = (100 * top['count'] / total).round(1)
        top = top.drop(columns='count')
        print(top.to_string(index=False))




def summarize_unknown_spans(unknown_spans, fs=2000):
    """
    Turn one participant's table of unknown pin combo periods into a single
    row of summary numbers.
 
    The two timing numbers, first_onset_min and last_offset_min, bracket the
    part of the recording where unknown periods occur. If both are small the
    unknown periods sit at the start of the recording. If last_offset_min is
    close to the end of the recording they are spread throughout.
 
    Parameters
    ----------
    unknown_spans : the boundaries table for one participant, with one row
                    per unknown pin combo period
    fs            : sampling rate in Hz (default 2000)
 
    Returns
    -------
    A dictionary with one entry per summary number.
    """
    if unknown_spans.empty:
        return {
            "n_spans":           0,
            "first_onset_min":   None,
            "last_offset_min":   None,
            "total_unknown_min": 0.0,
            "longest_span_s":    0.0,
        }
 
    total_samples = unknown_spans["duration_samples"].sum()
 
    return {
        "n_spans":           len(unknown_spans),
        "first_onset_min":   round(unknown_spans["onset"].min()  / (fs * 60), 2),
        "last_offset_min":   round(unknown_spans["offset"].max() / (fs * 60), 2),
        "total_unknown_min": round(total_samples / (fs * 60), 2),
        "longest_span_s":    round(unknown_spans["duration_s"].max(), 2),
    }