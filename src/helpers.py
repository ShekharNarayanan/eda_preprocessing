# -* file utils for the project *-
from convert_eprime.convert import text_to_csv
import pandas as pd

def eprime_txt_to_csv(text_file:str, csv_file:str, save_file:bool=False) -> pd.DataFrame:
    """"
    
    """
    with open(text_file, 'r') as fo:
        raw_data = fo.readlines()[:20]
        raw_data = [l.rstrip() for l in raw_data]
    
    return text_to_csv(text_file, csv_file, save_file=save_file)
    
def get_corrected_eprime_df(eprime_df:pd.DataFrame)-> tuple[pd.DataFrame, str]:
    """
    """
    # find relevant biopac column
    biopac_col = next((col for col in eprime_df.columns if 'biopac' in col.lower()), None)
    if biopac_col is None:
        raise ValueError(f"No biopac column found. Available columns: {list(eprime_df.columns)}")
    
    # take only rows where values in this column are not None
    nan_cols = eprime_df[biopac_col].isna()
    eprime_no_nan = eprime_df[~nan_cols]

    eprime_corrected = _rearrange_df_cols(first_col_choice=biopac_col,df=eprime_no_nan)
    eprime_corrected[f"{biopac_col}"] = eprime_corrected[f"{biopac_col}"].astype('int64')

    return eprime_corrected, biopac_col
    
def get_corrected_journal_df(journal_file_path:str,show_rows_from:int=1,biopac_col:str='') -> pd.DataFrame:
    """
    """
    # load file and rename Index column to the biopac column for consistency
    journal = pd.read_excel(journal_file_path,engine='xlrd',header=show_rows_from)
    journal = journal.rename(columns={'Index': f'{biopac_col}'})

    # remove nan rows in biopac_column
    nan_cols = journal[f"{biopac_col}"].isna()
    journal = journal[~nan_cols]

    # cast as int64 for ease of merging
    journal[f"{biopac_col}"] = journal[f"{biopac_col}"].astype('int64')

    journal_corrected = _rearrange_df_cols(first_col_choice=biopac_col,df=journal)
    
    
    return journal_corrected

def _rearrange_df_cols(first_col_choice,df):
    """
    """
    columns = [f'{first_col_choice}'] + [col for col in df.columns if col != f'{first_col_choice}']
    df = df.reindex(columns=columns)

    return df
    
def get_all_eprime_txt_files():
    pass