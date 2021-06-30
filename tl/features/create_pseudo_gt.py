import pandas as pd
from tl.exceptions import RequiredColumnMissingException


def create_pseudo_gt(df: pd.DataFrame, column_thresholds: list,
                     output_column: str):

    for column, threshold in column_thresholds:
        if column not in df.columns:
            raise RequiredColumnMissingException(
                "The input column {} does not exist"
                " in given data.".format(column))

        df.loc[(df[column].astype(float) >= threshold), output_column] = 1

    df[output_column] = df[output_column].fillna(0)
    return df
