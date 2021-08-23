import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException, UnsupportTypeError
from tl.file_formats_validator import FFV


def get_kg_links(score_column, file_path=None, df=None, label_column='label', top_k=5, k_rows=False):
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if score_column is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {}'.format('score_column'))

    if file_path:
        df = pd.read_csv(file_path, dtype=object)
    df[score_column].fillna(0.0, inplace=True)
    df.fillna("", inplace=True)
    df = df.astype(dtype={score_column: "float64"})
    ffv = FFV()
    if not (ffv.is_candidates_file(df)):
        raise UnsupportTypeError("The input file is not a candidate file!")

    topk_df = df.groupby(['column', 'row']).apply(lambda x: x.sort_values([score_column], ascending=False)) \
        .reset_index(drop=True)

    is_gt_present = 'evaluation_label' in df.columns

    final_list = []
    grouped_obj = topk_df.groupby(['column', 'row'])
    for key, grouped in grouped_obj:
        grouped['rank'] = list(grouped[score_column].rank(method='first', ascending=False).astype(int))

        grouped.drop_duplicates(subset='kg_id', inplace=True)
        new_top_k = top_k
        gt_rank = -1
        if is_gt_present:
            gt_rank_values = grouped[grouped['evaluation_label'].astype(int) == 1]['rank'].values
            if len(gt_rank_values) > 0:
                gt_rank = gt_rank_values[0]
            if gt_rank > top_k:
                new_top_k -= 1

        if not (k_rows):
            _ = {}

            kg_ids = list(grouped['kg_id'])[:new_top_k]
            kg_labels = list(grouped['kg_labels'])[:new_top_k]
            kg_descriptions = list(grouped['kg_descriptions'])[:new_top_k]
            kg_aliases = list(grouped['kg_aliases'])[:new_top_k]
            scores = [str(score) for score in list(grouped[score_column])[:new_top_k]]
            if gt_rank > top_k:
                kg_ids.extend(list(grouped['kg_id'])[gt_rank])
                kg_labels.extend(list(grouped['kg_labels'])[gt_rank])
                kg_descriptions.extend(list(grouped['kg_descriptions'])[gt_rank])
                kg_aliases.extend(list(grouped['kg_aliases'])[gt_rank])
                scores.append(str(list(grouped[score_column])[gt_rank]))

            _['column'] = key[0]
            _['row'] = key[1]
            _['label'] = grouped[label_column].unique()[0]
            _['kg_id'] = '|'.join(kg_ids)
            _['kg_labels'] = '|'.join(kg_labels)
            _['kg_descriptions'] = '|'.join(kg_descriptions)
            _['kg_aliases'] = '|'.join(kg_aliases)
            _['ranking_score'] = '|'.join(scores)

            final_list.append(_)
        else:
            if gt_rank > top_k:
                topk_df_row = pd.concat([grouped.head(new_top_k), grouped[grouped['rank'] == gt_rank]])
            else:
                topk_df_row = grouped.head(new_top_k)
            final_list.extend(topk_df_row.to_dict(orient='records'))

    odf = pd.DataFrame(final_list)
    return odf
