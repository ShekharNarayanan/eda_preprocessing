import yaml
import neurokit2 as nk
import pandas as pd

from src.common import file_utils
from src.segmentation import trigger_codebook

with open("config.yaml") as f:
    config = yaml.safe_load(f)

segmented_files = file_utils.get_segmented_files(config["SEGMENTED_DIR"])
trigger         = file_utils.read_segmented_file(segmented_files[0], columns=["trigger"])["trigger"]

# where the baseline period sits
baseline_spans = trial_boundaries.get_run_boundaries(trigger == 0, fs=fs)

# where the first trial starts
first_trial_onset = trial_boundaries.get_first_trial_onset(trigger)