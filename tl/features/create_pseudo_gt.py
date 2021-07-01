import pandas as pd
from tl.exceptions import RequiredColumnMissingException
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError


def create_pseudo_gt(df: pd.DataFrame, column_thresholds: str,
                     output_column: str):
    column_thresholds = [(_.split(":")[0], float(_.split(":")[1]))
                             for _ in column_thresholds.split(",")]
    ffv = FFV()
    if ffv.is_candidates_file(df):
        for column, threshold in column_thresholds:
            if column not in df.columns:
                raise RequiredColumnMissingException(
                    "The input column {} does not exist"
                    " in given data.".format(column))

            df.loc[(df[column].astype(float) >= threshold), output_column] = 1

        df[output_column] = df[output_column].fillna(0)
        return df
    else:
        raise UnsupportTypeError("The input file is not a candidates file!")
