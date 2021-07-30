import pandas as pd
from tl.exceptions import RequiredColumnMissingException
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError
import numpy as np
import sys


def create_pseudo_gt(df: pd.DataFrame, column_thresholds: str,
                     output_column: str):
    column_thresholds = [_.split(":") for _ in column_thresholds.split(",")]
    ffv = FFV()
    if ffv.is_candidates_file(df):
        grouped = df.groupby(by=["column", "row"])
        for column, threshold in column_thresholds:
            top_cd_df = pd.concat([gdf.sort_values(by=[column], ascending=False).head(1) for _, gdf in grouped])
            if column not in df.columns:
                raise RequiredColumnMissingException(
                    "The input column {} does not exist"
                    " in given data.".format(column))

            if threshold=="median":
                for _, gdf in grouped:
                    column_median =  top_cd_df[top_cd_df["column"] == _[0]][column].astype(float).median()
                    # gdf.loc[((gdf[column].astype(float) == gdf[column].max()) & 
                    #        (gdf[column].astype(float) >= column_median)), 
                    #        output_column] = 1
                    gdf.loc[(gdf[column].astype(float) >= column_median), 
                            output_column] = 1
                    df.loc[gdf.index[gdf[output_column].astype(float) == 1],
                           output_column] = 1
            elif threshold=="mean":
                for _, gdf in grouped:
                    column_mean =  top_cd_df[top_cd_df["column"] == _[0]][column].astype(float).mean()
                    # gdf.loc[((gdf[column].astype(float) == gdf[column].max()) & 
                    #        (gdf[column].astype(float) >= column_mean)), 
                    #        output_column] = 1
                    gdf.loc[(gdf[column].astype(float) >= column_mean), 
                            output_column] = 1
                    df.loc[gdf.index[gdf[output_column].astype(float) == 1],
                           output_column] = 1
            elif "top" in threshold:
                method, perc = threshold.split("top")
                perc = float(perc)
                if method == "median":
                    for _, gdf in grouped:
                        num_rows = max(1, int(gdf.shape[0]*(perc/100.0)))
                        top_n = gdf.nlargest(n=num_rows, columns=[column],
                                             keep="first")
                        column_median =  df[df["column"] == _[0]][column].astype(float).median()
                        top_n.loc[(top_n[column].astype(float) >= column_median,
                                  output_column)] = 1
                        df.loc[top_n.index[top_n[output_column].astype(float) == 1],
                               output_column] = 1
                elif method=="mean":
                    for _, gdf in grouped:
                        num_rows = max(1, int(gdf.shape[0]*(perc/100.0)))
                        top_n = gdf.nlargest(n=num_rows, columns=[column],
                                             keep="first")
                        column_mean =  df[df["column"] == _[0]][column].astype(float).mean()
                        top_n.loc[(top_n[column].astype(float) >= column_mean,
                                  output_column)] = 1
                        df.loc[top_n.index[top_n[output_column].astype(float) == 1],
                               output_column] = 1
                else:
                    method = float(method)
                    for _, gdf in grouped:
                        num_rows = max(1, int(gdf.shape[0]*(perc/100.0)))
                        top_n = gdf.nlargest(n=num_rows, columns=[column],
                                     keep="first")
                        top_n.loc[(top_n[column].astype(float) >= method,
                                  output_column)] = 1
                        df.loc[top_n.index[top_n[output_column].astype(float) == 1],
                               output_column] = 1
            else:
                grouped = df.groupby(by=["column", "row"])
                for _, gdf in grouped:
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
