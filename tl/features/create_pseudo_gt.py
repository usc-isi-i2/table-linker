import pandas as pd
from tl.exceptions import RequiredColumnMissingException
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
import sys


def create_pseudo_gt(df: pd.DataFrame, column_thresholds: str,
                     output_column: str):
    column_thresholds = [_.split(":") for _ in column_thresholds.split(",")]
    ffv = FFV()
    if ffv.is_candidates_file(df):
        for column, threshold in column_thresholds:
            if column not in df.columns:
                raise RequiredColumnMissingException(
                    "The input column {} does not exist"
                    " in given data.".format(column))

            if threshold=="median":
                grouped = df.groupby(by=["column", "row"])
                for _, gdf in grouped:
                    gdf.loc[((gdf[column]==gdf[column].max()) & 
                           (gdf[column].astype(float) >= 
                            gdf[column].astype(float).median())), 
                           output_column]=1
                    df.loc[gdf.index[gdf[output_column].astype(float)==1],
                           output_column]=1
            elif threshold=="mean":
                grouped = df.groupby(by=["column", "row"])
                for _, gdf in grouped:
                    gdf.loc[((gdf[column]==gdf[column].max()) & 
                           (gdf[column].astype(float) >= 
                            gdf[column].astype(float).mean())), 
                           output_column]=1
                    df.loc[gdf.index[gdf[output_column].astype(float)==1],
                           output_column]=1
            else:
                df.loc[(df[column].astype(float) >= float(threshold)),
                       output_column] = 1

        df[output_column] = df[output_column].fillna(-1)
        df =  df.astype({output_column: int})
        return df
    else:
        raise UnsupportTypeError("The input file is not a candidates file!")
