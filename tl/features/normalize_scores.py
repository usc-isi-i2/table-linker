import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException


def normalize_scores(column='retrieval_score', output_column=None, weights=None, file_path=None, df=None):
    """
    normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval method for all input cells in a column

    Args:
        column: column name which has the retrieval scores. Default is retrieval_score
        output_column: the output column name where the normalized scores will be stored. Default is input column name appended with the suffix _normalized
        weights: a comma separated string of the format <retrieval_method_1:<weight_1>, <retrieval_method_2:<weight_2>,...> specifying the weights for each retrieval method. By default, all retrieval method weights are set to 1.0
        file_path: input file path
        df: or input dataframe

    Returns:

    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if output_column is None:
        output_column = '{}_normalized'.format(column)

    method_weights = {}
    if weights is not None:
        m_ws = weights.split(',')
        for m_w in m_ws:
            _ = m_w.split(':')

            method_weights[_[0]] = float(_[1])

    if file_path:
        df = pd.read_csv(file_path, dtype=object)

    df[column] = df[column].map(lambda x: float(x))

    grouped_df = df.groupby(by=['column', 'method'])

    o_df = list()
    for i, gdf in grouped_df:
        max_score = gdf[column].max()
        # TODO find a better way to do this without having to make a copy
        fdf = gdf.copy(deep=True)
        fdf[output_column] = gdf[column].map(lambda x: (x / max_score) * method_weights.get(i[1], 1.0))
        o_df.append(fdf)

    return pd.concat(o_df)
