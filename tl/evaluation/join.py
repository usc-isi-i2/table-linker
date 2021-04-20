import pandas as pd


class Join(object):

    def join(self, df: pd.DataFrame, i_df: pd.DataFrame, ranking_score_column: str, extra_info=False):
        columns_to_wikify = list(df['column'].unique())
        output = []
        result_dict = self.create_result_dict(df, ranking_score_column, extra_info)

        i_cols = i_df.columns
        for i, row in i_df.iterrows():
            for column_to_wikify in columns_to_wikify:
                key = f"{column_to_wikify}_{i}"
                result = result_dict.get(key, None)
                if result:
                    for k in result:
                        c_name = i_cols[int(column_to_wikify)]
                        row[f"{c_name}_{k}"] = result[k]
            output.append(row)
        return pd.DataFrame(output)

    @staticmethod
    def create_result_dict(df: pd.DataFrame, ranking_score_column: str, extra_info=False):
        _ = {}
        for i, row in df.iterrows():
            key = f"{row['column']}_{row['row']}"
            if key not in _:
                _[key] = {
                    'kg_id': row['kg_id'],
                    'kg_label': row['kg_labels'],
                    'score': row[ranking_score_column]
                }
                if extra_info:
                    _[key]['kg_aliases'] = row['kg_aliases']
                    _[key]['kg_descriptions'] = row['kg_descriptions']

        return _
