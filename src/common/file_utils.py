import re
from pathlib import Path
import pandas as pd


def get_acq_files(input_dir):
    """
    Return all .acq files found in the given folder.

    Parameters
    ----------
    input_dir : str or Path
        Path to the folder containing .acq files

    Returns
    -------
    list of Path objects, one per .acq file found
    """
    return sorted(list(Path(input_dir).glob("*.acq")))


def get_participant_id(path):
    """
    Extract the participant identifier from the file name.

    The identifier is the part of the filename after 'EDA_', which may be
    a plain number like '112' or a number with a session suffix like
    '112_2'. It is returned as a string so both forms are preserved.

    For example:
        '10122025_POP_ECG_EDA_112.acq'   -> '112'
        '10122025_POP_ECG_EDA_112_2.acq' -> '112_2'

    Parameters
    ----------
    path : str or Path

    Returns
    -------
    participant_id : str
    """
    match = re.search(r"EDA_(.+)", Path(path).stem)
    if not match:
        raise ValueError(f"Could not extract a participant ID from: {path}")
    return match.group(1)


def get_participant_id_from_parquet(path):
    """
    Extract the participant identifier from a prepared parquet file name.

    These files are named 'clean_<participant_id>.parquet', so the
    identifier is whatever follows the 'clean_' prefix.

    For example:
        'clean_112.parquet'   -> '112'
        'clean_112_2.parquet' -> '112_2'

    Parameters
    ----------
    path : str or Path

    Returns
    -------
    participant_id : str
    """
    stem = Path(path).stem
    if not stem.startswith("clean_"):
        raise ValueError(f"Not a prepared parquet file name: {path}")
    return stem.replace("clean_", "", 1)


def get_sort_key(participant_id):
    """
    Give a sorting key that puts participants in numeric order and keeps a
    repeated session directly after the first session of that participant.

    For example '112' sorts before '112_2', and both sort before '113'.

    Parameters
    ----------
    participant_id : str, for example '112' or '112_2'

    Returns
    -------
    A tuple of (participant number, session number) to sort on.
    """
    parts          = participant_id.split("_")
    participant_no = int(parts[0])
    session_no     = int(parts[1]) if len(parts) > 1 else 1
    return (participant_no, session_no)


def get_participant_number(participant_id):
    """
    Return just the numeric part of a participant identifier, dropping any
    session suffix.

    This is what the even and odd codebook choice is based on, since both
    sessions of one participant use the same codebook.

    For example '112' and '112_2' both return 112.

    Parameters
    ----------
    participant_id : str

    Returns
    -------
    participant number as an integer
    """
    return int(participant_id.split("_")[0])


def get_prepared_files(prepared_dir):
    """
    Return all prepared parquet files found in the given folder, in
    participant order.

    These are the files written by prepare_data.py, named using the
    'clean_<participant_id>.parquet' pattern.

    Parameters
    ----------
    prepared_dir : str or Path
        Path to the folder containing the prepared parquet files

    Returns
    -------
    list of Path objects, one per prepared file found
    """
    prepared_files = list(Path(prepared_dir).glob("clean_*.parquet"))

    def sort_key_for_file(path):
        participant_id = get_participant_id_from_parquet(path)
        return get_sort_key(participant_id)

    return sorted(prepared_files, key=sort_key_for_file)


def read_prepared_file(path, columns=None):
    """
    Read a prepared parquet file back into a dataframe.

    Passing a list of column names reads only those columns, which matters
    for these recordings: reading just the trigger column avoids loading
    millions of rows of EDA and ECG that are not needed for a check.

    The index is checked on the way out, because everything downstream
    treats it as whole sample positions.

    Parameters
    ----------
    path    : str or Path to the parquet file
    columns : list of column names to read, or None to read all of them

    Returns
    -------
    A dataframe with the requested columns.
    """
    df = pd.read_parquet(path, columns=columns)
    warn_if_index_is_not_samples(df, path)
    return df


def save_prepared_file(clean_df, prepared_dir, participant_id):
    """
    Write one participant's cleaned dataframe to the prepared folder.

    The naming pattern 'clean_<participant_id>.parquet' is defined here and
    read back by get_participant_id_from_parquet, so the two stay together.

    Parameters
    ----------
    clean_df       : the cleaned dataframe to save
    prepared_dir   : str or Path to the folder to write into
    participant_id : str, used to build the file name

    Returns
    -------
    The Path the file was written to.
    """
    out_path = Path(prepared_dir) / f"clean_{participant_id}.parquet"
    clean_df.to_parquet(out_path)
    return out_path


def warn_if_index_is_not_samples(df, path):
    """
    Check that the index looks like whole sample positions counting up one
    at a time, which is what every duration and timing calculation assumes.

    If the index turns out to be something else, such as time in seconds,
    durations and onset times computed from it would be wrong. This prints
    a warning rather than stopping, so a check can still be run and the
    problem is visible.

    Parameters
    ----------
    df   : the dataframe that was just read
    path : the file it came from, used in the warning message
    """
    index = df.index

    is_whole_numbers  = pd.api.types.is_integer_dtype(index)
    first_step_is_one = len(index) > 1 and (index[1] - index[0]) == 1

    if not (is_whole_numbers and first_step_is_one):
        print(
            f"WARNING: the index of {Path(path).name} does not look like sample "
            f"positions (first values: {list(index[:3])}). "
            f"Timings computed from it may be wrong."
        )