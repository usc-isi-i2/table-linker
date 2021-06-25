import traceback
import argparse
import sys
import tl.exceptions
from tl.exceptions import UnsupportTypeError
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'Checks if for each candidate the ground truth was retrieved'
                ' and outputs those rows for which the ground truth was never'
                ' retrieved'
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin)
    parser.add_argument('--gt-file', type=str, dest='gt_file', required=True,
                        help="ground truth file to be compared against")


def run(**kwargs):
    try:
        import pandas as pd
        from tl.file_formats_validator import FFV
        import time

        ffv = FFV()

        df = pd.read_csv(kwargs["input_file"])
        gtdf = pd.read_csv(kwargs["gt_file"])
        required_cols = ["column", "row", "GT_kg_id", "GT_kg_label"]
        if not pd.Series(required_cols).isin(gtdf.columns).all():
            raise UnsupportTypeError("GT file does not have required columns")

        if ffv.is_candidates_file(df):
            start = time.time()
            grouped = df.groupby(by=["column", "row"])
            output = list()
            for i, gdf in grouped:
                if ((gtdf["column"] == i[0]) & (gtdf["row"] == i[1])).any():
                    id = gtdf.loc[((gtdf["column"] == i[0]) & (
                        gtdf["row"] == i[1]))]["GT_kg_id"].iloc[0]
                    lbl = gtdf.loc[((gtdf["column"] == i[0]) & (
                        gtdf["row"] == i[1]))]["GT_kg_label"].iloc[0]
                    if not (gdf["kg_id"] == id).any():
                        output.append(
                            [i[0], i[1], gdf["label"].iloc[0],
                             gdf["context"].iloc[0], id, lbl])
            result_df = pd.DataFrame(
                output, columns=["column", "row", "label", "context",
                                 "GT_kg_id", "GT_kg_label"])
            end = time.time()
            logger = Logger(kwargs["logfile"])
            logger.write_to_file(args={
                "command": "check-candidates",
                "time": end-start,
                "input_file": kwargs["input_file"]
            })
            result_df.to_csv(sys.stdout, index=False)
        else:
            raise UnsupportTypeError(
                "The input dataframe is not a candidates file")
    except Exception:
        message = 'Command: check-candidates\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
