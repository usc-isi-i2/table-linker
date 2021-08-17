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
                 ignore_column: str = None):
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

    def process(self, column):
        output = []
        is_k_p_number = self.is_k_percentile_number()
        self.input_df[self.output_column] = 0
        for c, gdf in self.input_df.groupby(by=['column']):

            _gdf = gdf if self.ignore_column is None else gdf[gdf[self.ignore_column].astype(int) == 0]
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

            gdf.loc[gdf[column] >= _k_percentile, self.output_column] = 1
            output.append(gdf)
        return pd.concat(output)

    def is_k_percentile_number(self):
        try:
            float(self.k_percentile)
        except ValueError:
            return False
        return True
