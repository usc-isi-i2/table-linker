import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException
from tl.file_formats_validator import FFV
import sys


def create_singleton_feature(output_column, file_path=None, df=None):
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if file_path:
        df = pd.read_csv(file_path, dtype=object)

    ffv = FFV()
    if not (ffv.is_candidates_file(df)):
        raise UnsupportTypeError("The input file is not a candidate file!")

    exact_match_count = df[df['method'] == 'exact-match'].groupby(['column','row'])[['kg_id']].count()
    exact_match_singleton = list(exact_match_count[exact_match_count['kg_id'] == 1].index)
    singleton_feat = []
    for i,row in df.iterrows():
        col_num,row_num = row['column'],row['row']
        if ((col_num,row_num) in exact_match_singleton) and (row['method'] == 'exact-match'):
            singleton_feat.append(1)
        else:
            singleton_feat.append(0)
    df[output_column] = singleton_feat
    return df