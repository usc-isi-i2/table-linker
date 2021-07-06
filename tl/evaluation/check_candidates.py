import pandas as pd
from tl.file_formats_validator import FFV
from tl.exceptions import UnsupportTypeError


def check_candidates(df: pd.DataFrame):
    ffv = FFV()
    if ffv.is_candidates_file(df):
        required_cols = ["GT_kg_id", "GT_kg_label", "evaluation_label"]
        if not pd.Series(required_cols).isin(df.columns).all():
            raise UnsupportTypeError(
                "Input file does not have required columns. "
                "Run ground-truth-labeler with ground truth.")

        df = df[df['evaluation_label'] != 0]

        grouped = df.groupby(by=["column", "row"])
        output = []
        columns = ["column", "row", "label", "context", "GT_kg_id",
                   "GT_kg_label"]
        if "GT_kg_description" in df.columns:
            columns.append("GT_kg_description")

        for i, gdf in grouped:
            if 1 not in gdf["evaluation_label"].values:
                _ = [i[0], i[1], gdf["label"].iloc[0], gdf["context"].iloc[0],
                     gdf["GT_kg_id"].iloc[0], gdf["GT_kg_label"].iloc[0]]
                if "GT_kg_description" in gdf.columns:
                    _.append(gdf["GT_kg_description"].iloc[0])
                output.append(_)
        return pd.DataFrame(output, columns=columns)
    else:
        raise UnsupportTypeError("Input file is not a candidates file!")
