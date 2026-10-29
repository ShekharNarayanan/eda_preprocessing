import pandas as pd
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

def get_matched_mask(trigger_map):
    """
    Given all the trigger masks, return a single True/False series
    that is True for any row that belongs to at least one trigger condition,
    and False for every other row.
    """
    masks = list(trigger_map.values())
    return pd.concat(masks, axis=1).any(axis=1)