import pandas as pd
import typing
import random

from tl.utility.utility import Utility
from tl.exceptions import RequiredColumnMissingException
from tl.exceptions import RequiredInputParameterMissingException


class ColorRenderUnit:
    def __init__(self, df: pd.DataFrame, sort_by_gt: bool = False, gt_score_column: str = None,
                 output_path: str = None):
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

    def add_color_by_score(self, columns: typing.List[str], k: int, use_all_columns: bool = False):
        color_formats = []
        # if use all columns, find all numeric columns
        if use_all_columns:
            columns = Utility.get_all_numeric_columns(self.df, skip_columns={"row", "column"})

        for i in range(len(columns)):
            each_column_color_range = []

            colors_ranges = ColorUtility.gradient_color([ColorUtility.get_random_color(), "#ffffff"], k)
            for each in colors_ranges[:k]:
                each_column_color_range.append(self.workbook.add_format({'bg_color': each}))
            color_formats.append(each_column_color_range)

        for each_column, each_color_format in zip(columns, color_formats):
            col_pos = self.df.columns.get_loc(each_column)
            for each_part in self.parts:
                # Set the conditional format range.
                start_row, end_row = each_part
                start_col, end_col = col_pos, col_pos
                unique_values = self.df[each_column].unique()
                if len(unique_values) <= 3 and 1 in unique_values:
                    self.worksheet.conditional_format(start_row, start_col, end_row, end_col,
                                                      {'type': 'cell',
                                                       'criteria': '==',
                                                       'value': 1,
                                                       'format': each_color_format[0]})
                elif each_column == "extra_information_score":
                    self.worksheet.conditional_format(start_row, start_col, end_row, end_col,
                                                      {'type': 'cell',
                                                       'criteria': '>',
                                                       'value': 0,
                                                       'format': each_color_format[0]})
                else:
                    # Apply a conditional format to the cell range.
                    value_parts = self.df.iloc[start_row - 1: end_row, col_pos].fillna(0)
                    criteria_values = sorted(value_parts.tolist(), reverse=True)[:k]
                    criteria_value_deduplicate = list(dict.fromkeys(criteria_values))
                    for i, each_criteria_val in enumerate(criteria_value_deduplicate):
                        self.worksheet.conditional_format(start_row, start_col, end_row, end_col,
                                                          {'type': 'cell',
                                                           'criteria': '>=',
                                                           'value': each_criteria_val,
                                                           'format': each_color_format[i]})

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
                    if isinstance(each_cell, str):
                        self.worksheet.write_url(row_pos, col_pos,
                                                 'https://www.wikidata.org/wiki/{}'.format(each_cell),
                                                 string=each_cell)
            else:
                self.worksheet.write_column(1, col_pos, self.df[each_column].fillna("").tolist())

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

    def sort_by_gt(self, gt_score_column: str):
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
        sorted_parts = sorted(self.parts, key=lambda x: x[0])
        for each_part in sorted_parts:
            self.worksheet.set_row(each_part[1], cell_format=border_format)

    def save_to_file(self):
        self.writer.save()


class ColorUtility:
    @staticmethod
    def get_random_color():
        rand = lambda: random.randint(80, 200)
        return '#%02X%02X%02X' % (rand(), rand(), rand())

    @staticmethod
    def RGB_to_Hex(rgb):
        RGB = rgb.split(',')
        color = '#'
        for i in RGB:
            num = int(i)
            color += str(hex(num))[-2:].replace('x', '0').upper()
        return color

    @staticmethod
    def RGB_list_to_Hex(RGB):
        color = '#'
        for i in RGB:
            num = int(i)
            color += str(hex(num))[-2:].replace('x', '0').upper()
        return color

    @staticmethod
    def Hex_to_RGB(hex):
        r = int(hex[1:3], 16)
        g = int(hex[3:5], 16)
        b = int(hex[5:7], 16)
        rgb = str(r) + ',' + str(g) + ',' + str(b)
        return rgb, [r, g, b]

    @staticmethod
    def gradient_color(color_list, color_sum=700):
        color_center_count = len(color_list)
        color_sub_count = int(color_sum / (color_center_count - 1))
        color_index_start = 0
        color_map = []
        for color_index_end in range(1, color_center_count):
            color_rgb_start = ColorUtility.Hex_to_RGB(color_list[color_index_start])[1]
            color_rgb_end = ColorUtility.Hex_to_RGB(color_list[color_index_end])[1]
            r_step = (color_rgb_end[0] - color_rgb_start[0]) / color_sub_count
            g_step = (color_rgb_end[1] - color_rgb_start[1]) / color_sub_count
            b_step = (color_rgb_end[2] - color_rgb_start[2]) / color_sub_count
            now_color = color_rgb_start
            color_map.append(ColorUtility.RGB_list_to_Hex(now_color))
            for color_index in range(1, color_sub_count):
                now_color = [now_color[0] + r_step, now_color[1] + g_step, now_color[2] + b_step]
                color_map.append(ColorUtility.RGB_list_to_Hex(now_color))
            color_index_start = color_index_end
        return color_map
