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
    Extract the participant number from the file name.

    The filename is expected to contain a numeric participant ID,
    for example: '10122025_POP_ECG_EDA_112.acq' -> 112.
    The last number found in the filename is used as the participant ID.

    Parameters
    ----------
    path : str or Path

    Returns
    -------
    participant_id : int
    """
    numbers = re.findall(r"\d+", Path(path).stem)
    if not numbers:
        raise ValueError(f"Could not extract a participant ID from: {path}")
    return int(numbers[-1])