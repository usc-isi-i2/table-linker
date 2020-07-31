import pandas as pd
import typing
import seaborn as sns
import copy
import matplotlib.pyplot as plt

from tl.exceptions import RequiredColumnMissingException, ZeroScoreError
from tl.evaluation.evaluation import metrics
from tl.utility.utility import Utility
from pyecharts import options as opts
from pyecharts.charts import Bar, Grid
from collections import defaultdict


class FigurePlotterUnit:
    def __init__(self, **kwargs):
        """
        :param columns: the target score columns
        :param k: the target top-k values for candidates
        :param df: input dataframe
        :param output_path: output path, if given, will save this figure as a png image
        :param add_wrong_candidates: bool, control whether to add wrong candidates on output ground truth analysis
        :return:
        """
        self.df = pd.read_csv(kwargs['input_file'], dtype=object)
        if kwargs["use_all_columns"]:
            self.columns = Utility.get_all_numeric_columns(self.df)
        else:
            self.columns = kwargs["column"]
        for each_column in self.columns:
            if each_column not in self.df.columns:
                raise RequiredColumnMissingException("Column {} does not exist in input data.".format(each_column))

        self.k = kwargs["k"]
        self.output_path = kwargs["output_uri"]

        self.add_wrong_candidates = kwargs["add_wrong_candidates"]
        self.wrong_candidates_score_column = kwargs["wrong_candidates_score_column"]
        input_file_name = kwargs['input_file'].name.split("/")[-1].rsplit(".")[0]
        if not kwargs.get("title"):
            self.title = "Scores Analysis of {}".format(input_file_name)
        else:
            self.title = kwargs["title"]

    def plot_bar_figure(self, output_score_table=False):
        """
        Call metric function to evaluate the results and plot it as a figure for visualization
        """
        results = dict()
        i = 0
        max_score = metrics(column=self.columns[0], df=self.df, k=len(self.df), tag="")["recall"].iloc[0]
        if max_score == 0:
            raise ZeroScoreError("The max accuracy of this dataset is zero, unable to plot the figure!")
        for each_column in self.columns:
            metric_result = metrics(column=each_column, df=self.df, k=self.k, tag="")
            for _, each_row in metric_result.iterrows():
                accuracy = each_row["recall"]
                each_res = {"k": each_row["k"],
                            "column": each_column,
                            "accuracy": accuracy,
                            "normalized_accuracy": accuracy / max_score
                            }
                results[i] = each_res
                i += 1
        plot_df = pd.DataFrame.from_dict(results, orient="index")
        # save the data if needed
        if output_score_table:
            plot_df.to_csv(self.output_path + "_score.csv", index=False)

        # score analysis figure
        figure_object = self.plot_figure(plot_df, max_score)
        self.save_to_disk(figure_object, self.output_path)
        # ground truth analysis figure
        self.plot_ground_truth_analysis(self.columns, self.title, self.output_path,
                                        self.df, self.add_wrong_candidates,
                                        self.wrong_candidates_score_column)

    @staticmethod
    def plot_figure(plot_df: pd.DataFrame, max_score: float):
        unique_columns = len(plot_df['column'].unique())
        fig_y_size = 10
        if unique_columns > 5:
            fig_y_size += (unique_columns - 5) // 2
        fig_dims = (15, fig_y_size)
        # set figure size and font scale
        plt.subplots(figsize=fig_dims)
        sns.set(font_scale=1.1)
        # some red colors
        color_palette = ["#7C1209", "#F32918", "#F37F18", "#F3CB18", "#E6F314"]

        # plot horizontal bar chart
        ax = sns.barplot(y="column", x="accuracy", hue="k", data=plot_df, palette=color_palette)

        ax.set(xlim=(0, 1))
        y_start = -0.5
        count_columns = len(plot_df['column'].unique())
        y_end = count_columns - 0.5

        # add max value line and text
        plt.plot([max_score, max_score], [y_start, y_end], linewidth=2, color="r")
        ax.text(max_score - 0.018, count_columns / 2, "max score line {:.2f}".format(max_score), fontsize=20, rotation=90,
                color="#FF0000")

        # add title
        ax.set_title('Score Analysis', fontsize=25)

        # add normalized score text
        prev_part = None
        dist_each_bar = 1 / (len(plot_df['k'].unique()) + 1)
        current_pos = -2 * dist_each_bar + 0.05
        # value_font_size = min(20 - , 10)
        for _, each_row in plot_df.iterrows():
            if prev_part != each_row["column"]:
                current_pos += dist_each_bar
                prev_part = each_row["column"]
            ax.text(0.1, current_pos,
                    "{:.2f} : {:.2f}".format(each_row["accuracy"], each_row["normalized_accuracy"]),
                    fontsize=15, color="#1EC2FF")
            current_pos += dist_each_bar
        return ax

    @staticmethod
    def save_to_disk(figure_object, output_path: str) -> None:
        figure_object.get_figure().savefig(output_path + ".png", bbox_inches='tight')

    @staticmethod
    def plot_ground_truth_analysis(all_score_columns: typing.List[str],
                                   title: str, output_path: str,
                                   df: pd.DataFrame,
                                   add_wrong_candidates: bool = False,
                                   wrong_candidates_score_column: str = None,
                                   ) -> None:
        """
        use pyechart to plot html interactive figure
        """
        df_processed = copy.deepcopy(df)
        for each_col in df_processed.columns:
            df_processed[each_col] = pd.to_numeric(df_processed[each_col], errors='ignore')

        xaxis_labels = []
        memo = defaultdict(list)

        groupby_res = df_processed[df_processed["evaluation_label"] == 1].groupby(["column", "row"])
        for key, each_group in reversed(tuple(groupby_res)):
            if add_wrong_candidates:
                df_wrong_examples = df_processed[(df_processed["column"] == key[0]) &
                                                 (df_processed["row"] == key[1]) &
                                                 (df_processed["evaluation_label"] == -1)] \
                                        .sort_values(by=[wrong_candidates_score_column], ascending=False).iloc[:3, :]
                # add wrong candidate information
                for _, each_row in df_wrong_examples.iterrows():
                    longest_string = max(each_row["kg_labels"].split("|"), key=len)
                    xaxis_labels.append(each_row["label_clean"] + " \n({})".format(longest_string))
                    for each_score_column in all_score_columns:
                        memo[each_score_column].append("{:.2f}".format(each_row[each_score_column]))

            # add ground truth information
            xaxis_labels.append(each_group["label_clean"].iloc[0])
            for each_score_column in all_score_columns:
                memo[each_score_column].append("{:.2f}".format(each_group[each_score_column].iloc[0]))
        # build figure
        bar = Bar()
        bar.add_xaxis(xaxis_labels)
        for k, v in memo.items():
            bar.add_yaxis(k, v)

        # set the global options
        bar.set_global_opts(title_opts=opts.TitleOpts(title=title, pos_left='40%'),
                            legend_opts=opts.LegendOpts(pos_left="center", pos_top="bottom", orient='horizontal'),
                            brush_opts=opts.BrushOpts(),
                            toolbox_opts=opts.ToolboxOpts(
                                feature=opts.ToolBoxFeatureOpts(
                                    save_as_image=opts.ToolBoxFeatureSaveAsImageOpts(
                                        title="save as image"
                                    ),
                                    magic_type=opts.ToolBoxFeatureMagicTypeOpts(
                                        line_title="switch to line chart",
                                        bar_title="switch to bar chart",
                                        stack_title="switch to stacked values",
                                        tiled_title="switch to tiled values"
                                    ),
                                    data_zoom=opts.ToolBoxFeatureDataZoomOpts(
                                        zoom_title="zoom in",
                                        back_title="zoom reset"
                                    ),
                                    restore=opts.ToolBoxFeatureRestoreOpts(
                                        title="reset"
                                    ),
                                    data_view=opts.ToolBoxFeatureDataViewOpts(
                                        title="Data table view",
                                        lang=["Table view", "Close", "Refresh"],
                                    ),
                                    brush=opts.ToolBoxFeatureBrushOpts(
                                        rect_title="rectangle choice",
                                        polygon_title="polygon choice",
                                        clear_title="clear choices",
                                        keep_title="keep choices"
                                    )
                                )
                            ),
                            datazoom_opts=opts.DataZoomOpts(orient="vertical"),
                            # yaxis_opts=opts.AxisOpts(name='labels', name_gap=5000, name_rotate=15),
                            tooltip_opts=opts.TooltipOpts(
                                is_show=True, trigger="axis", axis_pointer_type="shadow"
                            ),
                            xaxis_opts=opts.AxisOpts(
                                axistick_opts=opts.AxisTickOpts(
                                    is_inside=True,
                                    length=850,
                                    linestyle_opts=opts.LineStyleOpts(
                                        type_="dotted", opacity=0.5)
                                )
                            )
                            )

        # do not shown bar label values
        bar.set_series_opts(label_opts=opts.LabelOpts(is_show=False))

        bar.reversal_axis()

        grid = (
            Grid(init_opts=opts.InitOpts(
                width="1500px", height="1000px", page_title="Table Linker visualization page")
            ).add(
                bar, grid_opts=opts.GridOpts(pos_top='5%', pos_bottom="10%", pos_right='5%', pos_left="20%")
            )
        )
        grid.render(output_path + ".html")
