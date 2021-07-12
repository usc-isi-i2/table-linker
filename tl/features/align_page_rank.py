import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException


def align_page_rank(input_file=None, df=None):
    if input_file is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("input_file", "df"))
    if input_file:
        df = pd.read_csv(input_file, dtype=object)
    assert 'pagerank' in df, 'There\'s no page rank column in the table!'

    results = list()
    for ((col, row), group) in df.groupby(['column', 'row']):
        exact_match_df = group[group['method'] == 'exact-match'].copy()
        exact_match_df['aligned_pagerank'] = exact_match_df['pagerank'].astype(float)
        results.append(exact_match_df)

        fuzzy_match_df = group[group['method'] == 'fuzzy-augmented'].copy()
        fuzzy_match_df['aligned_pagerank'] = 0
        results.append(fuzzy_match_df)
    return pd.concat(results)
