import pandas as pd
from tl.exceptions import RequiredColumnMissingException


def create_pseudo_gt(df: pd.DataFrame, singleton_column: str,
                     context_column: str, context_threshold: float,
                     output_column: str):
    if singleton_column not in df.columns:
        raise RequiredColumnMissingException(
            "The input column {} does not exist"
            " in given data.".format(singleton_column))

    if context_column not in df.columns:
        raise RequiredColumnMissingException(
            "The input column {} does not exist"
            " in given data.".format(context_column))

    df.loc[((df[singleton_column].astype(int) == 1) |
           (df[context_column].astype(float) >= context_threshold)),
           output_column] = 1
    df.loc[((df[singleton_column].astype(int) == 0) &
           (df[context_column].astype(float) < context_threshold)),
           output_column] = 0
    return df
