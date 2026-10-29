"""
Resample and smooth one complete supplied EDA signal without selecting a crop.

AcqKnowledge's serialized option codes and endpoint behavior remain unverified.
Callers choose interpolation, smoothing, alignment, and edges explicitly; these
functions do not interpret workflow codes or load configuration or recordings.
"""

from fractions import Fraction
from numbers import Real

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline


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
