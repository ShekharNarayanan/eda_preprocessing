"""
Resample, smooth, and FIR-filter a complete EDA signal without selecting a crop.

AcqKnowledge's serialized option codes and endpoint behavior remain unverified.
Callers choose interpolation, smoothing, alignment, and edges explicitly; these
functions do not interpret workflow codes or load configuration or recordings.
"""

from fractions import Fraction
from math import ceil
from numbers import Real

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.signal import firwin, oaconvolve

from src.common.signal_plot_utils import plot_preprocessing


def validate_signal(signal):
    """
    Check a signal's values and sample timeline and return a floating-point copy.

    Parameters
    ----------
    signal : pandas.Series
        Real numeric samples in their original units, with a contiguous,
        nonnegative integer sample index. A trial may start at a nonzero
        recording position. Missing and infinite values must be handled by
        the caller, rather than silently filled during preprocessing.

    Returns
    -------
    pandas.Series
        Independent float64 copy preserving the index and name. An empty
        signal is valid and returns an empty copy. Invalid inputs raise a
        descriptive TypeError or ValueError.
    """
    if not isinstance(signal, pd.Series):
        raise TypeError("signal must be a pandas Series with a sample index.")
    if (
        not pd.api.types.is_numeric_dtype(signal.dtype)
        or pd.api.types.is_bool_dtype(signal.dtype)
        or pd.api.types.is_complex_dtype(signal.dtype)
    ):
        raise TypeError("signal must contain real numeric samples.")

    index = signal.index
    if not pd.api.types.is_integer_dtype(index.dtype) or index.hasnans:
        raise ValueError("signal index must contain contiguous nonnegative integer samples.")
    if len(index):
        expected_index = pd.RangeIndex(int(index[0]), int(index[0]) + len(index))
        if index[0] < 0 or not index.equals(expected_index):
            raise ValueError("signal index must contain contiguous nonnegative integer samples.")

    values = signal.to_numpy(dtype=float, na_value=np.nan, copy=True)
    if not np.isfinite(values).all():
        raise ValueError("signal contains missing or infinite samples; handle them before preprocessing.")
    return pd.Series(values, index=index.copy(), name=signal.name)


def _validate_sampling_rate(value, name):
    """
    Return a positive finite sampling rate in Hz, rejecting nonnumeric values.
    """
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a positive finite sampling rate in Hz.")
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite sampling rate in Hz.")
    return value


def resample_signal(signal, target_fs, fs=2000, *, method):
    """
    Resample a complete signal on a fixed-rate grid anchored at its first sample.

    Parameters
    ----------
    signal : pandas.Series
        Finite real samples with a contiguous original sample index, as
        required by validate_signal. No selected-area crop is applied.
    target_fs : number
        Output sampling rate in Hz.
    fs : number
        Input sampling rate in Hz (default 2000).
    method : {"linear", "padding", "cubic_spline"}
        Explicit interpolation choice. Padding takes the original sample to
        the left; cubic_spline uses a natural spline (zero second derivative
        at both ends). No anti-alias filter is applied by this operation.

    Returns
    -------
    resampled : pandas.Series
        Values in the input units, preserving the signal name. At a changed
        rate the index is a contiguous output sample counter starting at 0;
        at the same rate the original index is preserved. Only grid points
        at or before the final input sample are included: for N > 0, length
        is floor((N - 1) * target_fs / fs) + 1. The final sample is not forced
        onto the grid and there is no extrapolation or endpoint stretching.
    timeline : pandas.DataFrame
        Same index as resampled, with source_sample (possibly fractional
        original recording position) and time_s (source_sample / fs).
        Thus output position j maps to signal.index[0] + j * fs / target_fs.
        Empty inputs return an empty signal and both timeline columns. A
        single sample returns one unchanged value for any rate and method.

    Notes
    -----
    This grid rule is explicit and tested, but has not yet been validated
    against an AcqKnowledge export. In particular, the workflow's stored
    interpolationMethod=1 is not interpreted as a verified method choice.
    """
    signal = validate_signal(signal)
    fs = _validate_sampling_rate(fs, "fs")
    target_fs = _validate_sampling_rate(target_fs, "target_fs")
    if method not in ("linear", "padding", "cubic_spline"):
        raise ValueError("method must be 'linear', 'padding', or 'cubic_spline'.")

    # Exact rate arithmetic prevents losing a grid endpoint through rounding.
    ratio = Fraction(str(target_fs)) / Fraction(str(fs))
    n_samples = (
        0 if signal.empty
        else (len(signal) - 1) * ratio.numerator // ratio.denominator + 1
    )
    output_index = signal.index.copy() if fs == target_fs else pd.RangeIndex(n_samples)
    source_offsets = np.arange(n_samples, dtype=float) * ratio.denominator / ratio.numerator
    source_samples = source_offsets + (int(signal.index[0]) if len(signal) else 0)
    timeline = pd.DataFrame(
        {"source_sample": source_samples, "time_s": source_samples / fs},
        index=output_index,
    )

    if signal.empty or fs == target_fs or len(signal) == 1:
        return pd.Series(signal.to_numpy(copy=True), index=output_index, name=signal.name), timeline

    # Interpolate over sample positions, never an endpoint-fitted linspace.
    values = signal.to_numpy()
    input_positions = np.arange(len(signal))
    if method == "linear":
        resampled = np.interp(source_offsets, input_positions, values)
    elif method == "padding":
        # High-precision decimal rates can overflow int64 during multiplication.
        max_integer = max((n_samples - 1) * ratio.denominator, ratio.numerator)
        position_dtype = np.int64 if max_integer <= np.iinfo(np.int64).max else object
        left_samples = np.arange(n_samples, dtype=position_dtype) * ratio.denominator // ratio.numerator
        resampled = values[left_samples.astype(np.intp)]
    else:
        spline = CubicSpline(input_positions, values, bc_type="natural", extrapolate=False)
        resampled = spline(source_offsets)

    return pd.Series(resampled, index=output_index, name=signal.name), timeline


def smooth_signal(signal, window_samples=100, *, method, alignment, edge):
    """
    Smooth all supplied samples with an explicit moving mean or median window.

    Parameters
    ----------
    signal : pandas.Series
        Finite real samples on a contiguous integer sample timeline. Values
        stay in the input units; the index and name are preserved.
    window_samples : int
        Exact number of samples in a full window (default 100, or 0.1 s at
        1000 Hz). Must be positive. Even widths are used without rounding.
    method : {"mean", "median"}
        Mean or sorted median. For an even number of values the median is
        the arithmetic mean of the central pair, rather than either rank.
    alignment : {"centered", "trailing"}
        Centered uses window_samples // 2 samples before the current sample
        and (window_samples - 1) // 2 after it. Width 100 therefore includes
        positions i - 50 through i + 49, inclusive. Trailing includes the
        current sample and window_samples - 1 preceding samples.
    edge : {"shrink", "nearest"}
        Shrink uses only available samples at each edge, recomputing the
        mean or median of that shorter window. Nearest repeats the first
        or last value to fill a complete window. Neither mode pads with zero.

    Returns
    -------
    pandas.Series
        Independent float64 result, with exactly the input index and length.
        Empty inputs return an empty copy. Windows longer than the signal
        follow the same edge rule. The input is never changed.

    Notes
    -----
    These conventions are explicit calibration choices. They do not establish
    the stored smoothingMethod=1 mapping or AcqKnowledge's even-width median
    and boundary behavior; those still require independent waveform exports.
    """
    signal = validate_signal(signal)
    if (
        isinstance(window_samples, (bool, np.bool_))
        or not isinstance(window_samples, (int, np.integer))
    ):
        raise TypeError("window_samples must be a positive integer number of samples.")
    if window_samples <= 0:
        raise ValueError("window_samples must be a positive integer number of samples.")
    if method not in ("mean", "median"):
        raise ValueError("method must be 'mean' or 'median'.")
    if alignment not in ("centered", "trailing"):
        raise ValueError("alignment must be 'centered' or 'trailing'.")
    if edge not in ("shrink", "nearest"):
        raise ValueError("edge must be 'shrink' or 'nearest'.")
    if signal.empty:
        return signal

    if edge == "shrink":
        windows = signal.rolling(window_samples, center=alignment == "centered", min_periods=1)
    else:
        # Fill edges explicitly so even-width median behavior stays visible.
        before = window_samples // 2 if alignment == "centered" else window_samples - 1
        after = window_samples - 1 - before
        padded = pd.Series(np.pad(signal.to_numpy(), (before, after), mode="edge"))
        windows = padded.rolling(window_samples, min_periods=window_samples)

    smoothed = windows.mean() if method == "mean" else windows.median()
    if edge == "nearest":
        smoothed = smoothed.iloc[window_samples - 1:]
    return pd.Series(smoothed.to_numpy(copy=True), index=signal.index.copy(), name=signal.name)


def design_fir_filter(
    cutoff_hz, fs=2000, *, filter_type="lowpass", window="hamming",
    coefficient_mode="optimized", num_taps=None, optimized_factor=4.0, scale=True,
):
    """
    Construct an odd-length, symmetric FIR filter using a windowed sinc.

    Parameters
    ----------
    cutoff_hz : number
        Half-amplitude (-6 dB) cutoff in Hz, strictly between 0 and fs / 2.
    fs : number
        Sampling rate of the signal to filter in Hz (default 2000).
    filter_type : {"lowpass", "highpass"}
        Frequencies to retain. Highpass uses spectral inversion.
    window : {"hamming", "hann", "blackman", "boxcar"}
        Symmetric coefficient window used by scipy.signal.firwin.
    coefficient_mode : {"optimized", "fixed"}
        Optimized estimates ceil(optimized_factor * fs / cutoff_hz), then
        increases an even result to odd, with a minimum of 3 coefficients.
        This explicit estimate is not a verified AcqKnowledge mode mapping.
    num_taps : int or None
        Coefficient count in fixed mode, an odd integer of at least 3. Ignored
        in optimized mode; the workflow's stored count of 39 is not assumed.
    optimized_factor : number
        Positive multiplier for the optimized estimate (default 4).
    scale : bool
        Normalize gain to unity at DC for lowpass or Nyquist for highpass.
        False retains the unnormalized windowed-sinc coefficients.

    Returns
    -------
    coefficients : pandas.Series
        Coefficients indexed by integer tap position, named coefficient.
    metadata : dict
        Active design settings, actual num_taps, and group_delay_samples.
        Odd lengths give an integer delay, avoiding fractional sample shifts.
        Counts are not shortened to fit a short supplied trial.
    """
    fs = _validate_sampling_rate(fs, "fs")
    if isinstance(cutoff_hz, (bool, np.bool_)) or not isinstance(cutoff_hz, Real):
        raise TypeError("cutoff_hz must be a finite frequency between 0 and fs / 2.")
    cutoff_hz = float(cutoff_hz)
    if not np.isfinite(cutoff_hz) or not 0 < cutoff_hz < fs / 2:
        raise ValueError("cutoff_hz must be a finite frequency between 0 and fs / 2.")
    if filter_type not in ("lowpass", "highpass"):
        raise ValueError("filter_type must be 'lowpass' or 'highpass'.")
    if window not in ("hamming", "hann", "blackman", "boxcar"):
        raise ValueError("window must be 'hamming', 'hann', 'blackman', or 'boxcar'.")
    if coefficient_mode not in ("optimized", "fixed"):
        raise ValueError("coefficient_mode must be 'optimized' or 'fixed'.")
    if not isinstance(scale, (bool, np.bool_)):
        raise TypeError("scale must be a boolean.")

    # Keep the effective count explicit rather than reading inactive workflow fields.
    if coefficient_mode == "optimized":
        if (
            isinstance(optimized_factor, (bool, np.bool_))
            or not isinstance(optimized_factor, Real)
            or not np.isfinite(optimized_factor)
            or optimized_factor <= 0
        ):
            raise ValueError("optimized_factor must be a positive finite number.")
        estimate = optimized_factor * fs / cutoff_hz
        if not np.isfinite(estimate):
            raise ValueError("The optimized FIR coefficient count is not finite.")
        num_taps = max(3, ceil(estimate))
        num_taps += (num_taps % 2 == 0)
    if isinstance(num_taps, (bool, np.bool_)) or not isinstance(num_taps, (int, np.integer)):
        raise TypeError("num_taps must be an odd integer of at least 3 in fixed mode.")
    if num_taps < 3 or num_taps % 2 == 0:
        raise ValueError("num_taps must be an odd integer of at least 3.")

    coefficients = pd.Series(
        firwin(num_taps, cutoff_hz, fs=fs, window=window, pass_zero=filter_type, scale=scale),
        index=pd.RangeIndex(num_taps, name="tap"),
        name="coefficient",
    )
    metadata = {
        "fs": fs,
        "filter_type": filter_type,
        "cutoff_hz": cutoff_hz,
        "window": window,
        "coefficient_mode": coefficient_mode,
        "optimized_factor": optimized_factor if coefficient_mode == "optimized" else None,
        "num_taps": int(num_taps),
        "scale": bool(scale),
        "group_delay_samples": (num_taps - 1) // 2,
    }
    return coefficients, metadata


def filter_signal(
    signal, cutoff_hz, fs=2000, *, filter_type="lowpass", window="hamming",
    coefficient_mode="optimized", num_taps=None, optimized_factor=4.0,
    scale=True, delay_compensation=True, edge="reflect",
):
    """
    Apply one FIR pass with explicit padding and integer delay compensation.

    Parameters
    ----------
    signal : pandas.Series
        Finite real samples with a contiguous integer sample index. Filter
        the complete supplied signal in its input units. A trial can start
        at a nonzero recording position; the index and name are preserved.
    cutoff_hz, fs, filter_type, window, coefficient_mode, num_taps, optimized_factor, scale
        Filter design arguments described by design_fir_filter. Use the
        resampled rate as fs when filtering a resampled signal.
    delay_compensation : bool
        True centers the symmetric kernel, removing its group delay in one
        pass. False applies a causal convolution, retaining the group delay
        on the unchanged sample grid. No forward/backward filtering is used.
    edge : {"reflect", "nearest", "zero"}
        Reflect mirrors samples without repeating the endpoint. Nearest
        repeats the endpoint; zero pads with zeros. Reflection repeats as
        needed for short signals; a single sample reflects as a constant.

    Returns
    -------
    filtered : pandas.Series
        Independent float64 result with the same sample index and length.
        Empty inputs return an empty copy, after validating the settings.
    metadata : dict
        Design settings and coefficients, padding on both sides in samples,
        and remaining delay in samples and seconds. Padding uses only the
        supplied signal, so filtering a trial can differ from slicing a
        continuously filtered recording. FFT convolution introduces normal
        floating-point roundoff. AcqKnowledge parity remains unverified.
    """
    signal = validate_signal(signal)
    coefficients, metadata = design_fir_filter(
        cutoff_hz, fs=fs, filter_type=filter_type, window=window,
        coefficient_mode=coefficient_mode, num_taps=num_taps,
        optimized_factor=optimized_factor, scale=scale,
    )
    if not isinstance(delay_compensation, (bool, np.bool_)):
        raise TypeError("delay_compensation must be a boolean.")
    if edge not in ("reflect", "nearest", "zero"):
        raise ValueError("edge must be 'reflect', 'nearest', or 'zero'.")

    # Center one pass to remove delay without squaring the magnitude response.
    delay_samples = metadata["group_delay_samples"]
    before = delay_samples if delay_compensation else len(coefficients) - 1
    after = delay_samples if delay_compensation else 0
    remaining_delay_samples = 0 if delay_compensation else delay_samples
    metadata.update({
        "coefficients": coefficients,
        "delay_compensation": bool(delay_compensation),
        "edge": edge,
        "padding_before_samples": before,
        "padding_after_samples": after,
        "remaining_delay_samples": remaining_delay_samples,
        "remaining_delay_s": remaining_delay_samples / metadata["fs"],
    })
    if signal.empty:
        return signal, metadata

    padding_mode = {"reflect": "reflect", "nearest": "edge", "zero": "constant"}[edge]
    padded = np.pad(signal.to_numpy(), (before, after), mode=padding_mode)
    filtered = oaconvolve(padded, coefficients.to_numpy(), mode="valid")
    return pd.Series(filtered, index=signal.index.copy(), name=signal.name), metadata


def preprocess_signal(
    signal, target_fs, fs=2000, *, resampling_method="linear",
    smoothing_window_samples=100, smoothing_method="median",
    smoothing_alignment="centered", smoothing_edge="shrink",
    fir_cutoff_hz=1.0, fir_filter_type="lowpass", fir_window="hamming",
    fir_coefficient_mode="optimized", fir_num_taps=None, fir_optimized_factor=4.0,
    fir_scale=True, fir_delay_compensation=True, fir_edge="reflect",
):
    """
    Resample, smooth, and FIR-filter a complete signal, retaining every step.

    Parameters
    ----------
    signal : pandas.Series
        EDA in microsiemens, with contiguous original recording sample indices.
    target_fs : number
        Sampling rate in Hz for resampling, smoothing, and FIR filtering.
    fs : number
        Original sampling rate in Hz (default 2000).
    resampling_method, smoothing_window_samples, smoothing_method, smoothing_alignment, smoothing_edge
        Arguments for resample_signal and smooth_signal. Window width is in
        samples at target_fs. No anti-alias filter precedes resampling.
    fir_cutoff_hz, fir_filter_type, fir_window, fir_coefficient_mode, fir_num_taps, fir_optimized_factor
        Filter design arguments for filter_signal, evaluated at target_fs.
    fir_scale, fir_delay_compensation, fir_edge
        Gain normalization, delay, and endpoint choices for filter_signal.

    Returns
    -------
    dict
        signals contains independent raw, resampled, smoothed, and filtered
        Series. raw_time_s gives original recording seconds. timeline maps
        all three processed signals to source_sample and time_s, including
        nonzero origins. metadata records sampling rates, sample counts,
        resampling and smoothing settings, and full FIR metadata. Empty
        inputs retain every signal and timeline schema. No crop is applied,
        and neither files nor configuration are read or written here.
    """
    raw = validate_signal(signal)
    fs = _validate_sampling_rate(fs, "fs")
    target_fs = _validate_sampling_rate(target_fs, "target_fs")
    resampled, timeline = resample_signal(raw, target_fs, fs=fs, method=resampling_method)
    smoothed = smooth_signal(
        resampled, window_samples=smoothing_window_samples, method=smoothing_method,
        alignment=smoothing_alignment, edge=smoothing_edge,
    )
    filtered, fir_metadata = filter_signal(
        smoothed, fir_cutoff_hz, fs=target_fs, filter_type=fir_filter_type,
        window=fir_window, coefficient_mode=fir_coefficient_mode,
        num_taps=fir_num_taps, optimized_factor=fir_optimized_factor,
        scale=fir_scale, delay_compensation=fir_delay_compensation, edge=fir_edge,
    )
    return {
        "signals": {"raw": raw, "resampled": resampled, "smoothed": smoothed, "filtered": filtered},
        "raw_time_s": pd.Series(raw.index.to_numpy(dtype=float) / fs, index=raw.index),
        "timeline": timeline,
        "metadata": {
            "original_fs": fs,
            "processed_fs": target_fs,
            "input_samples": len(raw),
            "output_samples": len(filtered),
            "resampling": {"method": resampling_method},
            "smoothing": {
                "window_samples": smoothing_window_samples,
                "method": smoothing_method,
                "alignment": smoothing_alignment,
                "edge": smoothing_edge,
            },
            "fir": fir_metadata,
        },
    }


def build_preprocessed_recording(df, result, eda_column):
    """
    Replace EDA with its filtered signal and retain segmentation on the new grid.

    Parameters
    ----------
    df : pandas.DataFrame
        Original segmented recording, with eda_column, trigger, and contiguous
        integer sample positions. Other recorded columns are retained.
    result : dict
        Output of preprocess_signal for df[eda_column]. Its timeline defines
        the processed grid; filtering is continuous across trigger boundaries.
    eda_column : str
        Name of the physiological column to replace with filtered EDA.

    Returns
    -------
    pandas.DataFrame
        Independent recording on the processed integer sample index. Trigger
        labels and other channels use the original sample at or immediately
        before each processed position, without interpolation or filtering.
        Labels 0, -1, -2, and positive IDs keep their experimental meanings.
        At a lower rate, spans shorter than one output interval may disappear.
        Attributes record the sampling rates in Hz and original starting sample.
        Empty inputs retain all columns and return an empty recording.
    """
    missing = [column for column in (eda_column, "trigger") if column not in df]
    if missing:
        raise ValueError(f"Segmented recording is missing required columns: {missing}")

    metadata = result["metadata"]
    filtered = result["signals"]["filtered"]

    # Reuse exact resampling arithmetic so labels are never blended or rounded
    # to a different condition, including at fractional source positions.
    source_samples, _ = resample_signal(
        pd.Series(df.index.to_numpy(), index=df.index),
        target_fs=metadata["processed_fs"], fs=metadata["original_fs"],
        method="padding",
    )
    processed_df = df.loc[source_samples.to_numpy(dtype=int)].copy()
    processed_df.index = filtered.index.copy()
    processed_df[eda_column] = filtered
    processed_df.attrs.update({
        "sampling_rate_hz": metadata["processed_fs"],
        "source_sampling_rate_hz": metadata["original_fs"],
        "source_start_sample": int(df.index[0]) if len(df) else None,
    })
    return processed_df
