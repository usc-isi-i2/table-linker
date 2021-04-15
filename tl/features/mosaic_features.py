import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException, UnsupportTypeError
from tl.file_formats_validator import FFV
import sys


def mosaic_features(label_column, num_char, num_tokens, file_path=None, df=None):
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if file_path:
        df = pd.read_csv(file_path, dtype=object)

    ffv = FFV()
    if not (ffv.is_candidates_file(df)):
        raise UnsupportTypeError("The input file is not a candidate file!")

    if not(num_char) and not(num_tokens):
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("num_char", "num_tokens"))

    if num_char:
        df['num_char'] = df[label_column].apply(lambda label: len(label) if not(pd.isna(label)) else 0)
    
    if num_tokens:
        df['num_tokens'] = df[label_column].apply(lambda label: len(label.split()) if not(pd.isna(label)) else 0)

    return df