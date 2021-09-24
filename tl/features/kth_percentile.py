import pandas as pd
import sys

from tl.exceptions import RequiredInputParameterMissingException


class KthPercentile(object):
    def __init__(self,
                 column,
                 df: pd.DataFrame = None,
                 input_file: str = None,
                 output_column: str = 'kth_percenter',
                 k_percentile: str = 'mean',
                 ignore_column: str = None,
                 minimum_cells: int = None):
        if df is None and input_file is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("input_file", "df"))

        if input_file is not None:
            self.input_df = pd.read_csv(input_file)
            self.input_df['kg_id'].fillna("", inplace=True)

        elif df is not None:
            self.input_df = df

        assert column in self.input_df.columns, f"The column: {column}, not found in the input file"
        if ignore_column is not None:
            assert ignore_column in self.input_df.columns, f"The column: {ignore_column}, not found in the input file"

        self.output_column = output_column
        self.k_percentile = k_percentile
        self.ignore_column = ignore_column
        self.minimum_cells = minimum_cells

    def process(self, column):
        output = []
        is_k_p_number = self.is_k_percentile_number()
        self.input_df[self.output_column] = 0
        for c, gdf in self.input_df.groupby(by=['column']):

            _gdf = gdf if self.ignore_column is None else gdf[gdf[self.ignore_column].astype(int) == 0]
            if len(_gdf[column].unique()) == 1:
                gdf.loc[gdf['ignore_candidate'] == 0, self.output_column] = 1
                output.append(gdf)
            else:
                _k_percentile = None
                if not is_k_p_number:
                    # kth percentile is either mean or median
                    _k_percentile = _gdf[column].mean() if self.k_percentile == 'mean' else _gdf[column].median()
                else:  # kth percentile is a number
                    _ = float(self.k_percentile)
                    _kth = 1.0 - _ if _ != 1.0 else _
                    assert 0.0 <= _kth <= 1.0, "--k-percentile should be a number between [0.0, 1.0]," \
                                               " or a string ∈ {mean, median}"
                    _k_percentile = float(_gdf[column].quantile(_kth))

                if float(_k_percentile) == 0.0:
                    gdf.loc[gdf[column].astype(float) > 0.0, self.output_column] = 1
                else:
                    gdf.loc[gdf.index[gdf[column].astype(float) >= _k_percentile], self.output_column] = 1
                output.append(self.add_more_cells(gdf, column, c))

        return pd.concat(output)

    def add_more_cells(self, output_df: pd.DataFrame, score_column: str, column) -> pd.DataFrame:
        if self.minimum_cells is None:
            return output_df

        # check to see if we have enough cells with candidates in kth_percenter
        kth_p_cells = output_df[output_df[self.output_column] == 1].groupby(by=['row'])
        if len(kth_p_cells) >= self.minimum_cells:
            return output_df

        cell_bucket = set()
        seen_labels = dict()

        for r, gdf in kth_p_cells:
            key = f"{column}_{r}"
            cell_bucket.add(key)
            label = gdf['label_clean'].to_list()[0]
            if label not in seen_labels:
                seen_labels[label] = key

        kth_percenter_df = output_df[output_df[self.output_column] == 1]
        nonkth_percenter_df = output_df[output_df[self.output_column] == 0]

        sorted_df = nonkth_percenter_df.sort_values(by=score_column, ascending=False)

        scores = []
        for column, row, label, context_score, kth_percenter in zip(sorted_df['column'], sorted_df['row'],
                                                                    sorted_df['label_clean'], sorted_df[score_column],
                                                                    sorted_df[self.output_column]):
            if len(cell_bucket) >= self.minimum_cells:
                break

            cell_bucket_key = f"{column}_{row}"

            if cell_bucket_key not in cell_bucket and \
                    (seen_labels.get(label) is None or cell_bucket_key == seen_labels[label]):
                scores.append(1)
                cell_bucket.add(cell_bucket_key)
                if label not in seen_labels:
                    seen_labels[label] = cell_bucket_key
            else:
                scores.append(0)
        scores_to_extend = [0] * (len(sorted_df) - len(scores))
        scores.extend(scores_to_extend)
        sorted_df[self.output_column] = scores
        assert len(output_df) == len(sorted_df) + len(kth_percenter_df), "You messed up!"
        return pd.concat([kth_percenter_df, sorted_df]).sort_values(by=['column', 'row'])

    def is_k_percentile_number(self):
        try:
            float(self.k_percentile)
        except ValueError:
            return False
        return True
