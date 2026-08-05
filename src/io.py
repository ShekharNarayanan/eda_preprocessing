import re
from pathlib import Path


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