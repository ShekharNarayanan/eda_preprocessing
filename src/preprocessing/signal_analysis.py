"""
Derive phasic EDA and locate SCRs on a complete filtered signal.

BIOPAC documents median baseline removal and two-stage phasic thresholding in
https://www.biopac.com/wp-content/uploads/AcqKnowledge-Specialized.pdf (pp. 17–21).
The workflow's phasic method code, baseline window units, and exact crossing
and endpoint conventions still need independent AcqKnowledge calibration.
"""

from fractions import Fraction
from numbers import Real

import numpy as np
import pandas as pd

from src.common.signal_plot_utils import plot_analysis
from src.common.trial_boundaries import get_run_boundaries
from src.preprocessing.signal_preprocessing import (
    _validate_sampling_rate,
    smooth_signal,
    validate_signal,
)


SCR_DTYPES = {
    "onset": "int64",
    "peak": "int64",
    "end": "Int64",
    "amplitude_us": "float64",
    "phasic_peak_us": "float64",
    "status": "object",
    "rejection_reason": "object",
}


def _validate_parameter(value, name, minimum=0, maximum=None):
    """
    Check a finite numeric analysis setting, including its inclusive limits.
    """
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a finite number.")
    value = float(value)
    if not np.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        upper = f" and at most {maximum:g}" if maximum is not None else ""
        raise ValueError(f"{name} must be finite, at least {minimum:g}{upper}.")
    return value


def derive_phasic_signal(
    signal, fs=2000, *, method="median_baseline", baseline_window_s=5.0,
    baseline_alignment="centered", baseline_edge="shrink",
):
    """
    Subtract a moving median baseline from the complete filtered EDA signal.

    Parameters
    ----------
    signal : pandas.Series
        Filtered EDA in µS with contiguous nonnegative integer sample positions.
        Nonzero recording origins are preserved; missing values are invalid.
    fs : number
        Signal sampling rate in Hz (default 2000), after any resampling.
    method : {"median_baseline"}
        Explicit median baseline removal, without interpreting workflow enums
        or substituting NeuroKit's default decomposition.
    baseline_window_s : number
        Positive window duration in seconds (default 5). Its product with fs
        must be an exact positive integer number of samples; no rounding.
    baseline_alignment : {"centered", "trailing"}
        Window placement as for smooth_signal, including even-width centering.
    baseline_edge : {"shrink", "nearest"}
        Use available samples or repeat endpoints, as for smooth_signal.

    Returns
    -------
    baseline, phasic : pandas.Series
        Independent float64 signals in µS, with the input index and name.
        Phasic = filtered - baseline, retaining negative values. Empty inputs
        return empty signals; short inputs use the same configured edge rule.
    metadata : dict
        Active method, exact window in seconds and samples, and edge settings.
        A 5-second window is a calibration choice, not a verified decoding of
        smoothingWindowWidth=5. Independent waveform exports remain required.
    """
    signal = validate_signal(signal)
    fs = _validate_sampling_rate(fs, "fs")
    if method != "median_baseline":
        raise ValueError("method must be 'median_baseline'.")
    baseline_window_s = _validate_parameter(baseline_window_s, "baseline_window_s")
    window_samples = Fraction(str(baseline_window_s)) * Fraction(str(fs))
    if window_samples <= 0 or window_samples.denominator != 1:
        raise ValueError("baseline_window_s * fs must be a positive integer number of samples.")

    baseline = smooth_signal(
        signal, window_samples=int(window_samples), method="median",
        alignment=baseline_alignment, edge=baseline_edge,
    )
    phasic = signal - baseline
    return baseline, phasic, {
        "method": method,
        "baseline_window_s": baseline_window_s,
        "baseline_window_samples": int(window_samples),
        "baseline_alignment": baseline_alignment,
        "baseline_edge": baseline_edge,
    }


def detect_scrs(
    filtered, phasic, fs=2000, *, threshold_us=0.01, rejection_pct=10.0,
    reference_max_us=None,
):
    """
    Locate threshold-crossing SCR candidates and retain rejection decisions.

    Parameters
    ----------
    filtered, phasic : pandas.Series
        Finite EDA signals in µS on the same contiguous integer sample index.
        AcqKnowledge-filtered and phasic exports may be supplied directly,
        independently of Python preprocessing and baseline derivation.
    fs : number
        Signal sampling rate in Hz (default 2000).
    threshold_us : number
        Nonnegative phasic detection level H in µS (default 0.01). Onset is the
        first sample strictly above H following a value at or below H. End is
        the first sample at or below zero. Touching H alone does not start a
        response. Dips below H while still positive do not start another SCR.
    rejection_pct : number
        Percentage P from 0 to 100 (default 10). Reject complete candidates
        whose maximum phasic value is strictly below P% of the reference max.
        Equality is accepted; 0 disables relative rejection.
    reference_max_us : number or None
        Optional nonnegative maximum phasic value in µS from a wider analysis
        span. None uses all complete candidates in the supplied signal. A
        recording and an independently analyzed trial can have different maxima.

    Returns
    -------
    scrs : pandas.DataFrame
        One row per candidate, in sample order: onset, peak, nullable end,
        amplitude_us, phasic_peak_us, status, and rejection_reason. Peak is the
        first maximum FILTERED EDA sample in the inclusive onset/end interval;
        amplitude is filtered[peak] - filtered[onset], not the phasic maximum.
        Status is accepted or rejected. Reasons are relative_threshold,
        incomplete_start, incomplete_end, or both incomplete reasons joined
        by a semicolon. Accepted rows have an empty reason.
        A signal starting above H has an unobserved crossing and is rejected.
        A missing zero return has end = NA; its peak/amplitude describe only
        the observed portion. Incomplete candidates never set the default
        reference maximum. Flat, empty, and subthreshold signals return an
        empty table with this schema. Inputs are never changed.
    metadata : dict
        Sampling rate, thresholds, reference maximum and scope, crossing
        conventions, and accepted/rejected counts. No crossing interpolation
        is performed. Equality and incomplete-boundary conventions are explicit
        Python calibration choices pending independent event exports.
    """
    filtered = validate_signal(filtered)
    phasic = validate_signal(phasic)
    if not filtered.index.equals(phasic.index):
        raise ValueError("filtered and phasic must have identical sample indices.")
    fs = _validate_sampling_rate(fs, "fs")
    threshold_us = _validate_parameter(threshold_us, "threshold_us")
    rejection_pct = _validate_parameter(rejection_pct, "rejection_pct", maximum=100)
    if reference_max_us is not None:
        reference_max_us = _validate_parameter(reference_max_us, "reference_max_us")

    # Each positive excursion can contain at most one SCR, even when it dips
    # below H and crosses it again before returning to zero.
    spans = get_run_boundaries(phasic > 0, fs=fs)
    rows = []
    for span in spans.itertuples(index=False):
        excursion = phasic.loc[span.onset:span.offset]
        above_threshold = excursion > threshold_us
        if not above_threshold.any():
            continue
        onset = int(above_threshold.idxmax())
        has_end = span.offset < phasic.index[-1]
        observed_end = int(span.offset + 1) if has_end else int(span.offset)
        peak = int(filtered.loc[onset:observed_end].idxmax())
        reasons = []
        if onset == phasic.index[0]:
            reasons.append("incomplete_start")
        if not has_end:
            reasons.append("incomplete_end")
        rows.append({
            "onset": onset,
            "peak": peak,
            "end": observed_end if has_end else pd.NA,
            "amplitude_us": float(filtered.loc[peak] - filtered.loc[onset]),
            "phasic_peak_us": float(phasic.loc[onset:observed_end].max()),
            "status": "rejected" if reasons else "accepted",
            "rejection_reason": ";".join(reasons),
        })

    scrs = pd.DataFrame(rows, columns=SCR_DTYPES).astype(SCR_DTYPES)
    complete = scrs["rejection_reason"] == ""
    # BIOPAC's rejection threshold is based on PHASIC maxima. Filtered EDA
    # amplitudes are a separate measurement and must not control rejection.
    reference_scope = "supplied" if reference_max_us is not None else "complete_candidates"
    if reference_max_us is None:
        reference_max_us = float(scrs.loc[complete, "phasic_peak_us"].max()) if complete.any() else 0.0
    rejection_threshold_us = reference_max_us * rejection_pct / 100
    rejected = complete & (scrs["phasic_peak_us"] < rejection_threshold_us)
    scrs.loc[rejected, "status"] = "rejected"
    scrs.loc[rejected, "rejection_reason"] = "relative_threshold"
    return scrs, {
        "fs": fs,
        "threshold_us": threshold_us,
        "rejection_pct": rejection_pct,
        "reference_max_us": reference_max_us,
        "reference_scope": reference_scope,
        "rejection_threshold_us": rejection_threshold_us,
        "onset_rule": "previous <= H, current > H",
        "end_rule": "first sample <= 0 after onset",
        "candidate_count": len(scrs),
        "accepted_count": int((scrs["status"] == "accepted").sum()),
        "rejected_count": int((scrs["status"] == "rejected").sum()),
    }


def analyze_signal(
    signal, fs=2000, *, phasic_method="median_baseline", baseline_window_s=5.0,
    baseline_alignment="centered", baseline_edge="shrink", threshold_us=0.01,
    rejection_pct=10.0, reference_max_us=None, time_s=None,
):
    """
    Derive baseline/phasic EDA and detect SCRs, retaining the complete signal.

    Parameters
    ----------
    signal : pandas.Series
        Filtered EDA in µS, including AcqKnowledge-filtered reference input.
    fs : number
        Sampling rate of signal in Hz (default 2000).
    phasic_method, baseline_window_s, baseline_alignment, baseline_edge
        Explicit baseline settings passed to derive_phasic_signal.
    threshold_us, rejection_pct, reference_max_us
        Detection and rejection settings passed to detect_scrs.
    time_s : pandas.Series or None
        Exact recording seconds on signal's sample index, spaced at 1 / fs.
        Pass the preprocessing timeline after resampling to preserve its
        nonzero origin. None uses signal.index / fs. Times must be finite,
        nonnegative, and increasing; they never replace the sample index.

    Returns
    -------
    dict
        Independent filtered, baseline, and phasic Series under signals;
        timeline with time_s; scrs with detect_scrs columns plus onset_s,
        peak_s, end_s in exact recording seconds; and active metadata. Empty
        inputs retain every schema. No files or configuration are accessed.
    """
    filtered = validate_signal(signal)
    fs = _validate_sampling_rate(fs, "fs")
    if time_s is None:
        time_s = pd.Series(filtered.index.to_numpy(dtype=float) / fs, index=filtered.index)
    if not isinstance(time_s, pd.Series) or not time_s.index.equals(filtered.index):
        raise ValueError("time_s must be a pandas Series with identical sample indices to signal.")
    if (
        not pd.api.types.is_numeric_dtype(time_s.dtype)
        or pd.api.types.is_bool_dtype(time_s.dtype)
        or pd.api.types.is_complex_dtype(time_s.dtype)
    ):
        raise TypeError("time_s must contain real recording seconds.")
    times = time_s.to_numpy(dtype=float, na_value=np.nan, copy=True)
    if (
        not np.isfinite(times).all() or (times < 0).any()
        or (np.diff(times) <= 0).any()
        or not np.allclose(np.diff(times), 1 / fs, rtol=1e-7, atol=1e-10)
    ):
        raise ValueError("time_s must contain finite nonnegative recording seconds spaced at 1 / fs.")
    timeline = pd.DataFrame({"time_s": times}, index=filtered.index.copy())

    baseline, phasic, phasic_metadata = derive_phasic_signal(
        filtered, fs=fs, method=phasic_method, baseline_window_s=baseline_window_s,
        baseline_alignment=baseline_alignment, baseline_edge=baseline_edge,
    )
    scrs, scr_metadata = detect_scrs(
        filtered, phasic, fs=fs, threshold_us=threshold_us,
        rejection_pct=rejection_pct, reference_max_us=reference_max_us,
    )
    for event in ("onset", "peak", "end"):
        scrs[f"{event}_s"] = scrs[event].map(timeline["time_s"]).astype(float)
    return {
        "signals": {"filtered": filtered, "baseline": baseline, "phasic": phasic},
        "timeline": timeline,
        "scrs": scrs,
        "metadata": {"fs": fs, "input_samples": len(filtered), "phasic": phasic_metadata, "scr": scr_metadata},
    }
