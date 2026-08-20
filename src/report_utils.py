import os

import pandas as pd
from pathlib import Path

# The four sheets of the cross-participant report, in the order they are
# written. Both reading and writing work off this list, so a sheet only ever
# has to be named in one place.
REPORT_SHEETS = [
    "summary",
    "trigger_summary",
    "unknown_pin_combos",
    "after_baseline_relabelling",
]


def write_report(sheets, report_path):
    """
    Write the cross-participant report to an Excel file.

    Every sheet is sorted by participant ID and indexed by it, so the same
    participant lines up across sheets. Sheets with nothing in them are left
    out rather than written empty.

    Note that this rewrites the whole file. Anything already in it that is not
    passed in here is lost, which is why read_report exists: the usual pattern
    is to read what is already there, add the new participants to it, and pass
    the combined tables back in.

    Parameters
    ----------
    sheets      : dictionary of sheet name to a dataframe of its rows
    report_path : str or Path to write to

    Returns
    -------
    The Path the report was written to.
    """
    report_path = Path(report_path)

    # Nothing is written if every sheet is empty, because a workbook with no
    # sheets in it is not a valid Excel file.
    has_rows = any(
        table is not None and not table.empty for table in sheets.values()
    )
    if not has_rows:
        return report_path

    # The report is built under a temporary name and only put in place once it
    # is complete. Writing straight to the real file means that a failure
    # part way through leaves a half written file behind that cannot be read,
    # taking the record of every participant with it.
    temp_path = report_path.with_name(report_path.name + ".tmp")

    with pd.ExcelWriter(temp_path) as writer:
        for sheet_name in REPORT_SHEETS:
            table = sheets.get(sheet_name)

            if table is None or table.empty:
                continue

            table = table.copy()
            table["participant_id"] = table["participant_id"].astype(str)

            sorted_table = (
                table
                .sort_values("participant_id", key=lambda ids: ids.map(sort_key_for_id))
                .set_index("participant_id")
            )
            sorted_table.to_excel(writer, sheet_name=sheet_name, index=True)

    os.replace(temp_path, report_path)
    return report_path


def sort_key_for_id(participant_id):
    """
    Give a sorting key that puts participant IDs in numeric order and keeps a
    repeated session directly after the first session of that participant.

    Sorting the IDs as plain text would put '1000' before '999', and would
    separate '112' from '112_2'. This splits the ID into its number and its
    session instead.

    Parameters
    ----------
    participant_id : str, for example '112' or '112_2'

    Returns
    -------
    A tuple of (participant number, session number) to sort on.
    """
    parts = str(participant_id).split("_")

    try:
        participant_no = int(parts[0])
    except ValueError:
        # An ID that is not a number at all sorts to the end rather than
        # stopping the report from being written.
        return (float("inf"), 0)

    session_no = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    return (participant_no, session_no)


def read_report(report_path):
    """
    Read an existing cross-participant report back into dataframes.

    Each sheet comes back as a dataframe with participant_id as an ordinary
    column rather than the index, which is the same shape write_report expects,
    so what comes out of here can be added to and passed straight back in.

    If the file does not exist yet, empty dataframes are returned for every
    sheet, so the first run needs no special handling.

    Parameters
    ----------
    report_path : str or Path to read from

    Returns
    -------
    A dictionary of sheet name to dataframe, with one entry per sheet.
    """
    report_path = Path(report_path)

    if not report_path.exists():
        return {sheet_name: pd.DataFrame() for sheet_name in REPORT_SHEETS}

    # Reading with sheet_name=None gets every sheet in one pass. A report that
    # cannot be read is treated as though it were not there, so that a damaged
    # file means every participant is prepared again rather than the run
    # stopping before anything can be done about it.
    try:
        existing_sheets = pd.read_excel(report_path, sheet_name=None, index_col=0)
    except Exception as error:
        print(
            f"WARNING: {report_path.name} could not be read ({error}). "
            f"Treating it as if no report existed."
        )
        return {sheet_name: pd.DataFrame() for sheet_name in REPORT_SHEETS}

    sheets = {}
    for sheet_name in REPORT_SHEETS:
        table = existing_sheets.get(sheet_name)

        if table is None:
            sheets[sheet_name] = pd.DataFrame()
            continue

        # participant_id was the index on the way out, so it is put back as a
        # normal column here. Excel stores an ID like 112 as a number, so it is
        # made a string again to match the IDs taken from the file names.
        table = table.reset_index()
        table["participant_id"] = table["participant_id"].astype(str)
        sheets[sheet_name] = table

    return sheets


def get_prepared_participant_ids(sheets):
    """
    Return the participant IDs already present in the report.

    The summary sheet has exactly one row per participant, so it is the one
    that answers this. IDs are returned as strings, matching the form used
    everywhere else, so that '112' and '112_2' stay distinct.

    Parameters
    ----------
    sheets : the dictionary of sheets returned by read_report

    Returns
    -------
    A set of participant IDs as strings.
    """
    summary = sheets.get("summary")

    if summary is None or summary.empty:
        return set()

    return set(summary["participant_id"].astype(str))


def add_participant_rows(sheets, new_rows):
    """
    Add one participant's rows to the tables read from the report.

    If that participant already has rows in a sheet, they are dropped first,
    so preparing a participant again replaces their old numbers instead of
    leaving two sets behind.

    Parameters
    ----------
    sheets   : the dictionary of sheets returned by read_report
    new_rows : dictionary of sheet name to a dataframe of this participant's
               rows. A sheet can be left out if the participant has nothing
               to add to it.

    Returns
    -------
    A new dictionary of sheets with the rows added.
    """
    updated = {}

    for sheet_name in REPORT_SHEETS:
        existing = sheets.get(sheet_name, pd.DataFrame())
        new      = new_rows.get(sheet_name)

        if new is None or new.empty:
            updated[sheet_name] = existing
            continue

        if existing.empty:
            updated[sheet_name] = new.copy()
            continue

        # Drop any rows this participant already had in this sheet.
        participant_ids = set(new["participant_id"].astype(str))
        keep            = ~existing["participant_id"].astype(str).isin(participant_ids)

        updated[sheet_name] = pd.concat([existing[keep], new], ignore_index=True)

    return updated