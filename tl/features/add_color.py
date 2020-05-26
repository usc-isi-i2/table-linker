import pandas as pd
import typing
import random

from tl.utility.utility import Utility
from tl.exceptions import RequiredColumnMissingException
from tl.exceptions import RequiredInputParameterMissingException


class ColorRenderUnit:
    def __init__(self, df: pd.DataFrame, sort_by_gt: bool = False, gt_score_column: str = None, output_path: str = None):
        if not output_path:
            raise RequiredInputParameterMissingException("output path must be given.")

        self.df = df
        self._preprocess()
        if sort_by_gt:
            self.df = self.sort_by_gt(gt_score_column)
        self.writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        self.workbook = self.writer.book
        self.worksheet = self.workbook.add_worksheet('Sheet1')
        self._write_to_excel()

        self.parts = []
        for key, each_group in self.df.groupby(["column", "row"]):
            each_part_range = [each_group.index[0] + 1, each_group.index[-1] + 1]
            self.parts.append(each_part_range)

    def add_color_by_score(self, columns: typing.List[str], k: int):
        for each_column in columns:
            col_pos = self.df.columns.get_loc(each_column)
            for each_part in self.parts:
                each_format = self.workbook.add_format({'bg_color': self.get_random_color()})
                # Set the conditional format range.
                start_row, end_row = each_part
                start_col, end_col = col_pos, col_pos
                if each_column == "evaluation_label":
                    self.worksheet.conditional_format(start_row, start_col, end_row, end_col,
                                                      {'type': 'cell',
                                                       'criteria': '==',
                                                       'value': 1,
                                                       'format': each_format})
                elif each_column == "extra_information_score":
                    self.worksheet.conditional_format(start_row, start_col, end_row, end_col,
                                                      {'type': 'cell',
                                                       'criteria': '>',
                                                       'value': 0,
                                                       'format': each_format})
                else:
                    # Apply a conditional format to the cell range.
                    value_parts = self.df.iloc[start_row - 1: end_row, col_pos].fillna(0)
                    criteria_value = sorted(value_parts.tolist(), reverse=True)[k - 1]
                    self.worksheet.conditional_format(start_row, start_col, end_row, end_col,
                                                      {'type': 'cell',
                                                       'criteria': '>=',
                                                       'value': criteria_value,
                                                       'format': each_format})

    def _write_to_excel(self):
        header_format = self.workbook.add_format({'bold': True})
        url_columns = ["kg_id", "GT_kg_id"]
        self.worksheet.write_row(0, 0, self.df.columns.tolist(), header_format)
        for col_pos, each_column in enumerate(self.df.columns):
            if each_column in url_columns:
                # col_pos = self.df.columns.get_loc(each_column)
                row_pos = 0
                for each_cell in self.df[each_column]:
                    row_pos += 1
                    self.worksheet.write_url(row_pos, col_pos,
                                             'https://www.wikidata.org/wiki/{}'.format(each_cell),
                                             string=each_cell)
            else:
                self.worksheet.write_column(1, col_pos, self.df[each_column].fillna(0).tolist())

    def _preprocess(self):
        # sort the index by column and row for better view
        self.df = Utility.sort_by_col_and_row(self.df)
        # put sentence column at last position for better view
        if "sentence" in self.df.columns:
            all_cols = self.df.columns.tolist()
            all_cols.append(all_cols.pop(all_cols.index("sentence")))
            self.df = self.df[all_cols]

        for each_col in self.df.columns:
            self.df[each_col] = pd.to_numeric(self.df[each_col], errors='ignore')

    def sort_by_gt(self, gt_score_column):
        """
        The rows for each candidate are ordered descending by gt cosine,
        except that the first row is the ground truth candidate regardless of
        whether it didn't get the highest gt cosine score
        :return:
        """
        output_df = pd.DataFrame()

        for each_column in ["evaluation_label", gt_score_column]:
            if each_column not in self.df.columns:
                raise RequiredColumnMissingException("{} is missing in input data! Can't sort by ground truth.")

        for key, each_part in self.df.groupby(["column", "row"]):
            each_part = each_part.sort_values(by=["evaluation_label", gt_score_column], ascending=[False, False])
            output_df = output_df.append(each_part)
        output_df = output_df.reset_index().drop(columns=["index"])
        return output_df

    def add_border(self):
        border_format = self.workbook.add_format({'bottom': 2})
        for each_part in self.parts:
            self.worksheet.set_row(each_part[1], cell_format=border_format)

    def save_to_file(self):
        self.writer.save()

    @staticmethod
    def get_random_color():
        rand = lambda: random.randint(100, 255)
        return '#%02X%02X%02X' % (rand(), rand(), rand())
