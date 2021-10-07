import pandas as pd
from typing import List
from tl.exceptions import RequiredInputParameterMissingException

EQUAL_SIM = 'equal_sim'
BEST_STR_SIMILARITY = 'best_str_similarity'
BEST_LABEL_STR_SIMILARITY = 'best_label_str_similarity'


class PickHCCandidates(object):
    def __init__(self, string_sim_label_cols: List[str],
                 string_sim_alias_cols: List[str],
                 df: pd.DataFrame = None,
                 input_file: str = None,
                 desired_cell_factor: float = 0.25,
                 maximum_cells: int = 100,
                 minimum_cells: int = 10,
                 str_sim_threshold: float = 0.9,
                 str_sim_threshold_backup: float = 0.8,
                 output_column_name: str = 'ignore_candidate'):
        """
        Initializes the PickHCCanddidates class with the following parameters.
        Args:
            string_sim_cols: list of string similarity columns
            df: input dataframe...
            input_file: ...or a file path
            desired_cell_factor: fraction of total cells to be considered to be marked as high confidence
            maximum_cells: maximum cells to be considered
            minimum_cells: minimum cells to be considered
            str_sim_threshold: string similarity threshold
            str_sim_threshold_backup: a backup string similarity threshold in case we do not find enough cells with the
            fist string similarity threshold
        """
        if df is None and input_file is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("input_file", "df"))

        if input_file is not None:
            self.input_df = pd.read_csv(input_file)
            self.input_df['kg_id'].fillna("", inplace=True)

        elif df is not None:
            self.input_df = df

        assert all(
            c in self.input_df.columns for c in
            string_sim_label_cols), f"one or more provided string similarity columns: " \
                                    f"{','.join(string_sim_label_cols)} not found in the file"

        assert all(
            c in self.input_df.columns for c in
            string_sim_alias_cols), f"one or more provided string similarity columns: " \
                                    f"{','.join(string_sim_alias_cols)} not found in the file"

        self.desired_cell_factor = desired_cell_factor
        self.maximum_cells = maximum_cells
        self.minimum_cells = minimum_cells
        self.string_sim_label_cols = string_sim_label_cols
        self.string_sim_alias_cols = string_sim_alias_cols
        self.str_sim_threshold = str_sim_threshold
        self.str_sim_threshold_backup = str_sim_threshold_backup
        self.output_column_name = output_column_name

    def max_string_similarity(self):
        best_str_sims = []
        best_str_label_sims = []

        data = self.input_df.copy()

        string_sim_cols = self.string_sim_alias_cols + self.string_sim_label_cols

        for str_sim_tup in zip(*[data[c] for c in string_sim_cols]):
            best_str_sims.append(max(str_sim_tup))

        for str_sim_tup in zip(*[data[c] for c in self.string_sim_label_cols]):
            best_str_label_sims.append(max(str_sim_tup))

        data[BEST_STR_SIMILARITY] = best_str_sims
        data[BEST_LABEL_STR_SIMILARITY] = best_str_label_sims
        self.input_df = data

    def calculate_equal_sim(self):
        # calculates the number of candidates for each cell,
        # which have the best string similarity equal to the max string similarity
        """
        if a cell has candidates c1,c2 and c3 and all have best_sim(ci) = 1.0, then equal_sim(ci) = 3
        """
        data = self.input_df.copy()
        grouped_col = data.groupby(by=['column'])
        vc_dict = {}
        cell_count_dict = {}
        for column, gpc in grouped_col:
            if column not in cell_count_dict:
                cell_count_dict[column] = {}

            grouped_row = gpc.groupby(by=['row'])

            num_cells = len(grouped_row)
            cell_count_dict[column]['total_cells'] = num_cells
            desired_cells = num_cells * self.desired_cell_factor
            smc_cells = min(max(desired_cells, self.minimum_cells), self.maximum_cells)
            cell_count_dict[column]['smc_cells'] = smc_cells

            for row, gpr in grouped_row:
                vc_df = gpr[BEST_STR_SIMILARITY].value_counts().reset_index(name='bts_count')
                for bss, count in zip(vc_df['index'], vc_df['bts_count']):
                    vc_dict[f'{column}_{row}_{bss}'] = count

        val_counts = []
        for c, r, bss in zip(data['column'], data['row'], data[BEST_STR_SIMILARITY]):
            key = f"{c}_{r}_{bss}"
            val_counts.append(vc_dict.get(key))
        data[EQUAL_SIM] = val_counts

        data.sort_values(by=['column', BEST_STR_SIMILARITY, EQUAL_SIM],
                         ascending=[True, False, True],
                         inplace=True)

        self.cell_count_dict = cell_count_dict
        self.input_df = data

    def process(self):
        self.max_string_similarity()
        self.calculate_equal_sim()

        data = self.input_df
        data.reset_index(drop=True, inplace=True)
        data[self.output_column_name] = 1
        cell_bucket_list = []
        for column, gdf in data.groupby(['column']):
            cell_bucket = {}
            seen_label = dict()
            threshold = self.str_sim_threshold
            is_bucket_full = False

            for row, label, kg_id, str_sim, equal_sim in zip(gdf['row'], gdf['label_clean'], gdf['kg_id'],
                                                             gdf[BEST_STR_SIMILARITY], gdf[EQUAL_SIM]):

                if len(cell_bucket) >= self.cell_count_dict[column]['smc_cells'] or \
                        str_sim < self.str_sim_threshold_backup:
                    is_bucket_full = True

                if len(cell_bucket) < self.cell_count_dict[column]['smc_cells'] and str_sim < threshold:
                    threshold = self.str_sim_threshold_backup

                cell_bucket_key = f"{column}_{row}"

                if str_sim >= threshold and \
                        (seen_label.get(label) is None or cell_bucket_key == seen_label[label]):
                    if not is_bucket_full:
                        if cell_bucket_key not in cell_bucket:
                            cell_bucket[cell_bucket_key] = {
                                'qnodes': set(),
                                'best_str_match': str_sim
                            }

                        if label not in seen_label:
                            seen_label[label] = cell_bucket_key

                    if cell_bucket_key in cell_bucket and str_sim >= cell_bucket[cell_bucket_key]['best_str_match']:
                        cell_bucket[cell_bucket_key]['qnodes'].add(kg_id)

            cell_bucket_list.append(cell_bucket)

        for cell_bucket in cell_bucket_list:
            for key, cell_bucket_content in cell_bucket.items():
                _ = key.split('_')
                column = int(_[0])
                row = int(_[1])
                qnodes = cell_bucket_content['qnodes']

                for kg_id in qnodes:
                    data.loc[(data['column'] == column) & (data['row'] == row) & (
                            data['kg_id'] == kg_id), self.output_column_name] = 0
        return data
