import pandas as pd
import sys

from tl.exceptions import RequiredInputParameterMissingException


class KthPercentile(object):
    def __init__(self,
                 column,
                 df: pd.DataFrame = None,
                 input_file: str = None,
                 output_column: str = 'kth_percenter',
                 k_percentile: str = 'mean'):
        if df is None and input_file is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("input_file", "df"))

        if input_file is not None:
            self.input_df = pd.read_csv(input_file)
            self.input_df['kg_id'].fillna("", inplace=True)

        elif df is not None:
            self.input_df = df

        assert column in self.input_df.columns, f"The column: {column}, not found in the input file"

        self.output_column = output_column
        self.k_percentile = k_percentile

    def process(self, column):
        data = self.input_df.copy()

        _k_percentile = None
        if not self.is_k_percentile_number():
            # kth percentile is either mean or median
            _k_percentile = data[column].mean() if self.k_percentile == 'mean' else data[column].median()
        else:  # kth percentile is a number
            _kth = float(self.k_percentile)
            assert 0.0 <= _kth <= 1.0, "--k-percentile should be any number between [0.0, 1.0]," \
                                       " or a string ∈ {mean, median}"
            _k_percentile = float(data[column].quantile(_kth))

        data[self.output_column] = 0
        data.loc[data[column] >= _k_percentile, self.output_column] = 1
        return data

    def is_k_percentile_number(self):
        try:
            float(self.k_percentile)
        except ValueError:
            return False
        return True
