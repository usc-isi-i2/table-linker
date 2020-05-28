import pandas as pd
import typing
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt

from tl.exceptions import RequiredColumnMissingException
from tl.evaluation.evaluation import metrics


class FigurePlotterUnit:
    def __init__(self):
        pass

    @staticmethod
    def plot_bar_figure(columns: typing.List[str], k: typing.List[int],
                        df: pd.DataFrame, output_path: str = None):
        """
        Call metric function to evaluate the results and plot it as a figure for visualization
        :param columns: the target score columns
        :param k: the target top-k values for candidates
        :param df: input dataframe
        :param output_path: output path, if given, will save this figure as a png image
        :return:
        """
        for each_column in columns:
            if each_column not in df.columns:
                raise RequiredColumnMissingException("Column {} does not exist in input data.".format(each_column))

        results = dict()
        i = 0
        max_score = metrics(column=columns[0], df=df, k=len(df), tag="").iloc[0, 2]
        for each_column in columns:
            for each_k in k:
                each_metric_result = metrics(column=each_column, df=df, k=int(each_k), tag="")
                accuracy = each_metric_result.iloc[0, 2]
                each_res = {"k": each_k, "column": each_column, "accuracy": accuracy, "normalized_accuracy": accuracy / max_score}
                results[i] = each_res
                i += 1
        plot_df = pd.DataFrame.from_dict(results, orient="index")

        figure_object = FigurePlotterUnit.plot_figure(plot_df, max_score)
        if output_path:
            FigurePlotterUnit.save_to_disk(figure_object, output_path)

    @staticmethod
    def plot_figure(plot_df: pd.DataFrame, max_score: float):
        fig_dims = (15, 10)
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
        ax.text(max_score - 0.018, count_columns / 2, "max score line {:.2f}".format(max_score), fontsize=20, rotation=90, color="#FF0000")

        # add title
        ax.set_title('Score Analysis', fontsize=25)

        # add normalized score text
        prev_part = None
        dist_each_bar = 1 / (len(plot_df['k'].unique()) + 1)
        current_pos = -2 * dist_each_bar + 0.05
        for _, each_row in plot_df.iterrows():
            if prev_part != each_row["column"]:
                current_pos += dist_each_bar
                prev_part = each_row["column"]
            ax.text(0.1, current_pos,
                    "{:.2f} : {:.2f}".format(each_row["accuracy"], each_row["normalized_accuracy"]),
                    fontsize=20, color="#1EC2FF")
            current_pos += dist_each_bar
        return ax

    @staticmethod
    def save_to_disk(figure_object, output_path: str) -> None:
        figure_object.get_figure().savefig(output_path)
