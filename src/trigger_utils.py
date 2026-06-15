def create_trigger_map_odd(df):
    
    # redefine masks with clean binary comparisons
    trig_145 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_146 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_129 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_130 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_49 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_50 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_52 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 1)
        & (df["Lure"] == 0)
    )
    trig_56 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 1)
    )
    trig_65 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_66 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_68 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 1)
        & (df["Lure"] == 0)
    )
    trig_72 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 0)
        & (df["Lure"] == 1)
    )
    trig_17 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_18 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_1 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_2 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )

    trigger_map = {
        145: trig_145,
        146: trig_146,
        129: trig_129,
        130: trig_130,
        49: trig_49,
        50: trig_50,
        52: trig_52,
        56: trig_56,
        65: trig_65,
        66: trig_66,
        68: trig_68,
        72: trig_72,
        17: trig_17,
        18: trig_18,
        1: trig_1,
        2: trig_2,
    }

    return trigger_map

def create_trigger_map_even(df):
    trig_129 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_130 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_145 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_146 = (
        (df["OT_Only"] == 1)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_33 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_34 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_36 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 1)
        & (df["Lure"] == 0)
    )
    trig_40 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 1)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 1)
    )
    trig_81 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_82 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_84 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 1)
        & (df["Lure"] == 0)
    )
    trig_88 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 1)
        & (df["PM"] == 0)
        & (df["Lure"] == 1)
    )
    trig_1 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_2 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 0)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_17 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 1)
        & (df["Nonliving_Pseudoword"] == 0)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )
    trig_18 = (
        (df["OT_Only"] == 0)
        & (df["OT_Type"] == 1)
        & (df["Living_Word"] == 0)
        & (df["Nonliving_Pseudoword"] == 1)
        & (df["PM_Delayed"] == 0)
        & (df["PM_Active"] == 0)
        & (df["PM"] == 0)
        & (df["Lure"] == 0)
    )

    trigger_map = {
        129: trig_129,
        130: trig_130,
        145: trig_145,
        146: trig_146,
        33: trig_33,
        34: trig_34,
        36: trig_36,
        40: trig_40,
        81: trig_81,
        82: trig_82,
        84: trig_84,
        88: trig_88,
        1: trig_1,
        2: trig_2,
        17: trig_17,
        18: trig_18,
    }

    return trigger_map

# import pandas as pd

# # The order of columns in this list matters.
# # It must match the order of the values in each codebook entry below.
# TRIGGER_COLS = [
#     "OT_Only",
#     "OT_Type",
#     "Living_Word",
#     "Nonliving_Pseudoword",
#     "PM_Delayed",
#     "PM_Active",
#     "PM",
#     "Lure",
# ]

# # Codebook for ODD participants (Version A).
# # Each entry is: trigger_id -> tuple of 8 pin values (0 or 1)
# # in the same order as TRIGGER_COLS above.
# #                OT_Only OT_Type Living Nonliving PM_Del PM_Act PM Lure
# CODEBOOK_ODD = {
#     145:        ( 1,      1,      1,     0,        0,     0,     0, 0),
#     146:        ( 1,      1,      0,     1,        0,     0,     0, 0),
#     129:        ( 1,      0,      1,     0,        0,     0,     0, 0),
#     130:        ( 1,      0,      0,     1,        0,     0,     0, 0),
#     49:         ( 0,      1,      1,     0,        1,     0,     0, 0),
#     50:         ( 0,      1,      0,     1,        1,     0,     0, 0),
#     52:         ( 0,      1,      0,     0,        1,     0,     1, 0),
#     56:         ( 0,      1,      0,     0,        1,     0,     0, 1),
#     65:         ( 0,      0,      1,     0,        0,     1,     0, 0),
#     66:         ( 0,      0,      0,     1,        0,     1,     0, 0),
#     68:         ( 0,      0,      0,     0,        0,     1,     1, 0),
#     72:         ( 0,      0,      0,     0,        0,     1,     0, 1),
#     17:         ( 0,      1,      1,     0,        0,     0,     0, 0),
#     18:         ( 0,      1,      0,     1,        0,     0,     0, 0),
#     1:          ( 0,      0,      1,     0,        0,     0,     0, 0),
#     2:          ( 0,      0,      0,     1,        0,     0,     0, 0),
# }

# # Codebook for EVEN participants (Version B).
# #                OT_Only OT_Type Living Nonliving PM_Del PM_Act PM Lure
# CODEBOOK_EVEN = {
#     129:        ( 1,      0,      1,     0,        0,     0,     0, 0),
#     130:        ( 1,      0,      0,     1,        0,     0,     0, 0),
#     145:        ( 1,      1,      1,     0,        0,     0,     0, 0),
#     146:        ( 1,      1,      0,     1,        0,     0,     0, 0),
#     33:         ( 0,      0,      1,     0,        1,     0,     0, 0),
#     34:         ( 0,      0,      0,     1,        1,     0,     0, 0),
#     36:         ( 0,      0,      0,     0,        1,     0,     1, 0),
#     40:         ( 0,      0,      0,     0,        1,     0,     0, 1),
#     81:         ( 0,      1,      1,     0,        0,     1,     0, 0),
#     82:         ( 0,      1,      0,     1,        0,     1,     0, 0),
#     84:         ( 0,      1,      0,     0,        0,     1,     1, 0),
#     88:         ( 0,      1,      0,     0,        0,     1,     0, 1),
#     1:          ( 0,      0,      1,     0,        0,     0,     0, 0),
#     2:          ( 0,      0,      0,     1,        0,     0,     0, 0),
#     17:         ( 0,      1,      1,     0,        0,     0,     0, 0),
#     18:         ( 0,      1,      0,     1,        0,     0,     0, 0),
# }


# def build_mask_for_one_trigger(df, pin_values, trigger_cols):
#     """
#     Build a True/False mask that is True for every row in df where the
#     8 pin columns exactly match the given pin values.

#     Walks through each of the 8 pin columns one at a time. For each
#     column, checks whether the value in df matches the expected pin
#     value (0 or 1) from the codebook. The final mask is True only for
#     rows where ALL 8 columns matched.

#     Parameters
#     ----------
#     df           : the dataframe with 8 binarized pin columns
#     pin_values   : tuple of 8 expected values (0 or 1), in the order
#                    of trigger_cols
#     trigger_cols : list of the 8 pin column names

#     Returns
#     -------
#     A pandas Series of booleans, one value per row in df.
#     """
#     # Start by assuming every row matches; we'll narrow it down.
#     mask = pd.Series(True, index=df.index)

#     # For each of the 8 columns, check whether the column equals the
#     # expected pin value at that position. If even one column doesn't
#     # match for a given row, that row's mask value becomes False.
#     for column_name, expected_value in zip(trigger_cols, pin_values):
#         column_matches = df[column_name] == expected_value
#         mask = mask & column_matches

#     return mask


# def create_trigger_map(df, codebook, trigger_cols=TRIGGER_COLS):
#     """
#     Given a codebook mapping trigger IDs to pin combinations, return
#     a dictionary mapping each trigger ID to a True/False mask showing
#     which rows in df belong to that trigger.

#     Parameters
#     ----------
#     df           : the dataframe with 8 binarized pin columns
#     codebook     : dictionary of trigger_id -> tuple of 8 pin values
#     trigger_cols : list of the 8 pin column names

#     Returns
#     -------
#     A dictionary mapping each trigger ID to its boolean mask.
#     """
#     trigger_map = {}

#     # Walk through each entry in the codebook and build its mask.
#     for trigger_id, pin_values in codebook.items():
#         mask = build_mask_for_one_trigger(df, pin_values, trigger_cols)
#         trigger_map[trigger_id] = mask

#     return trigger_map


# # Convenience wrappers so the main script doesn't need to know which
# # codebook constant to import.
# def create_trigger_map_odd(df):
#     return create_trigger_map(df, CODEBOOK_ODD)


# def create_trigger_map_even(df):
#     return create_trigger_map(df, CODEBOOK_EVEN)