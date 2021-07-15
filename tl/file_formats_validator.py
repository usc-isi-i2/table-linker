import pandas as pd


class FFV(object):
    def __init__(self, retrieval_score_col_name="retrieval_score"):
        self.canonical_columns = ['column', 'row']
        if not retrieval_score_col_name:
            retrieval_score_col_name = "retrieval_score"
        self.candidates_columns_only = ['kg_id', 'kg_labels', 'method', retrieval_score_col_name]
        self.candidates_columns = ['kg_id', 'kg_labels', 'method', retrieval_score_col_name] + self.canonical_columns

    def is_canonical_file(self, df=None, file_path=None):
        if file_path:
            df = pd.read_csv(file_path, dtype=object)
        if df is None:
            return False

        columns = df.columns

        if len(columns) >= 3 and all(c in columns for c in self.canonical_columns) and all(
                c not in columns for c in self.candidates_columns_only):
            return True
        return False

    def is_candidates_file(self, df=None, file_path=None):
        if file_path:
            df = pd.read_csv(file_path, dtype=object)

        if df is None:
            return False
        columns = df.columns

        return all(c in columns for c in self.candidates_columns)
