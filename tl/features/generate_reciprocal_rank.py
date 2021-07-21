import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException, UnsupportTypeError
from tl.file_formats_validator import FFV


def generate_reciprocal_rank(score_column, output_column, file_path=None, df=None):
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if score_column is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {}'.format('score_column'))

    if file_path:
        df = pd.read_csv(file_path, dtype=object)

    df.fillna("", inplace=True)
    df = df.astype(dtype={score_column: "float64"})
    ffv = FFV()
    if not (ffv.is_candidates_file(df)):
        raise UnsupportTypeError("The input file is not a candidate file!")

    final_list = []
    grouped_obj = df.groupby(['row', 'column'])
    for cell in grouped_obj:
        reciprocal_rank = list(1 / cell[1][score_column].rank(method='first', ascending=False))
        cell[1][output_column] = reciprocal_rank

        final_list.append(cell[1])

    odf = pd.concat(final_list)
    return odf
