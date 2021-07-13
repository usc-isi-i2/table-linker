import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException, UnsupportTypeError
from tl.file_formats_validator import FFV


def create_singleton_feature(output_column, file_path=None, df=None):
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if file_path:
        df = pd.read_csv(file_path, dtype=object)

    ffv = FFV()
    if not (ffv.is_candidates_file(df)):
        raise UnsupportTypeError("The input file is not a candidate file!")

    exact_match_count = df[df['method'] == 'exact-match'].groupby(['column', 'row'])[['kg_id']].count()

    exact_match_singleton = set(exact_match_count[exact_match_count['kg_id'] == 1].index)

    df[output_column] = df.apply(lambda x: is_singleton(x.column, x.row, exact_match_singleton, x.method), axis=1)
    return df


def is_singleton(column, row, exact_match_singleton, method):
    if ((column, row) in exact_match_singleton) and (method == 'exact-match'):
        return 1
    return 0
