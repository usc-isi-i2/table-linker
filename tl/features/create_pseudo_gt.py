import pandas as pd
from tl.exceptions import RequiredColumnMissingException
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
import numpy as np
import sys


def create_pseudo_gt(df: pd.DataFrame, column_thresholds: str,
                     output_column: str, filter: str):
    column_thresholds = [_.split(":") for _ in column_thresholds.split(",")]

    if filter:
        col, val = filter.split(":")
        val =  float(val)
        if col not in df.columns:
            raise RequiredColumnMissingException("The input column {} does not" 
                                                 " exist in given data.".format(col))
    ffv = FFV()
    if ffv.is_candidates_file(df):
        grouped = df.groupby(by=["column", "row"])
        for column, threshold in column_thresholds:
            if column not in df.columns:
                raise RequiredColumnMissingException(
                    "The input column {} does not exist"
                    " in given data.".format(column))

            top_cd_df = pd.concat([gdf.sort_values(by=[column], ascending=False).head(1) for _, gdf in grouped])
            if filter:
                top_cd_df = top_cd_df[top_cd_df[col] > val]
            if threshold=="median":
                for _, gdf in top_cd_df.groupby(by=["column"]):
                    gdf.loc[(gdf[column].astype(float) >= gdf[column].astype(float).median()), 
                            output_column] = 1
                    df.loc[gdf.index[gdf[output_column].astype(float) == 1],
                           output_column] = 1
            elif threshold=="mean":
                for _, gdf in top_cd_df.groupby(by=["column"]):
                    gdf.loc[(gdf[column].astype(float) >= gdf[column].astype(float).mean()), 
                            output_column] = 1
                    df.loc[gdf.index[gdf[output_column].astype(float) == 1],
                           output_column] = 1
            elif "top" in threshold:
                method, perc = threshold.split("top")
                perc = float(perc)
                if method == "median":
                    for _, gdf in top_cd_df.groupby(by=["column"]):
                        gdf = gdf[gdf[column].astype(float) >= gdf[column].astype(float).median()]
                        num_rows = max(1, int(gdf.shape[0]*(perc/100.0)))
                        gdf = gdf.nlargest(n=num_rows, columns=[column], keep="first")
                        gdf[output_column] = 1
                        df.loc[gdf.index[gdf[output_column].astype(float) == 1],
                            output_column] = 1
                elif method=="mean":
                    for _, gdf in top_cd_df.groupby(by=["column"]):
                        gdf = gdf[gdf[column].astype(float) >= gdf[column].astype(float).mean()]
                        num_rows = max(1, int(gdf.shape[0]*(perc/100.0)))
                        gdf = gdf.nlargest(n=num_rows, columns=[column], keep="first")
                        gdf[output_column] = 1
                        df.loc[gdf.index[gdf[output_column].astype(float) == 1],
                            output_column] = 1
            else:
                for _, gdf in top_cd_df.groupby(by=["column"]):
                    gdf.loc[(gdf[column].astype(float) >= float(threshold)), 
                            output_column] = 1
                    df.loc[gdf.index[gdf[output_column].astype(float) == 1],
                           output_column] = 1
        # If too few candidate rows in pseudo gt
        if np.sum(df[output_column] == 1) < 5:
            df.loc[(df["singleton"] == 1), output_column] = 1
        if np.sum(df[output_column] == 1) < 5:
            for _, gdf in df.groupby(by=["column", "row"]):
                gdf.loc[(gdf["pgr_rts"] == gdf["pgr_rts"].max()),
                        output_column]=1
                df.loc[gdf.index[gdf[output_column].astype(float)==1],
                       output_column]=1
        df[output_column] = df[output_column].fillna(-1)
        df =  df.astype({output_column: int})
        return df
    else:
        raise UnsupportTypeError("The input file is not a candidates file!")
