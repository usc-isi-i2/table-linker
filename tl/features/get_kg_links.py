import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException
from tl.file_formats_validator import FFV


def get_kg_links(score_column, file_path=None, df=None, label_column='label', top_k=5):
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if score_column is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {}'.format('score_column'))

    if file_path:
        df = pd.read_csv(file_path, dtype=object)
    ffv = FFV()
    if not (ffv.is_candidates_file(df)):
        raise UnsupportTypeError("The input file is not a candidate file!")

    topk_df = df.groupby(['column', 'row']).apply(lambda x: x.sort_values([score_column], ascending=False)) \
        .reset_index(drop=True).drop_duplicates(subset='kg_id')

    final_list = []
    grouped_obj = topk_df.groupby(['row', 'column'])
    for cell in grouped_obj:
        cell[1]['kg_labels'] = cell[1]['kg_labels'].fillna('')
        cell[1]['kg_id'] = cell[1]['kg_id'].fillna('')
        _ = {}
        _['column'] = cell[0][1]
        _['row'] = cell[0][0]
        _['label'] = cell[1][label_column].unique()[0]
        _['kg_id'] = '|'.join(list(cell[1]['kg_id'])[:top_k])
        _['kg_label'] = '|'.join(list(cell[1]['kg_labels'])[:top_k])
        _['ranking_score'] = '|'.join([str(round(float(score), 2)) for score in list(cell[1][score_column])[:top_k]])
        final_list.append(_)

    odf = pd.DataFrame(final_list)
    return odf
