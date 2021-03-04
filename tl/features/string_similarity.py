import pandas as pd
import typing
import inspect
import copy
import tl.features.similarity_units

from collections import defaultdict
from tl.exceptions import UnsupportTypeError, RequiredColumnMissingException
DEFAULT_COLUMN_COMB_NAME = ("label_clean", "kg_labels")


class StringSimilarity:
    def __init__(self, similarity_method: typing.List[str], **kwargs):
        self.similarity_units = []
        self.df = copy.deepcopy(kwargs["df"])
        self.original_df = kwargs["df"]
        self.target_label_column_name, self.candidate_label_column_name = kwargs.get("target_columns", (None, None))

        for each_col in [self.target_label_column_name, self.candidate_label_column_name]:
            if each_col and each_col not in self.df:
                raise RequiredColumnMissingException("No specified column name `{}` found!".format(each_col))

        if not self.target_label_column_name:
            if "label_clean" in self.df:
                self.target_label_column_name = "label_clean"
                kwargs['target_label_column_name'] = self.target_label_column_name
            elif "label" in self.df:
                self.target_label_column_name = "label"
                kwargs['target_label_column_name'] = self.target_label_column_name
            else:
                raise RequiredColumnMissingException("No `label` or `label_clean` column found!")
        else:
            kwargs["candidate_label_column_name"] = self.candidate_label_column_name

        if not self.candidate_label_column_name:
            if "kg_labels" in self.df:
                self.candidate_label_column_name = "kg_labels"
                kwargs['candidate_label_column_name'] = self.candidate_label_column_name
            else:
                raise RequiredColumnMissingException("No `kg_labels` column found!")
        else:
            kwargs["target_label_column_name"] = self.target_label_column_name

        output_column_name = kwargs.get("output_column", None)
        if output_column_name is not None:
            self.has_output_column_name = True
            self.compared_column_names = output_column_name
        elif (self.target_label_column_name, self.candidate_label_column_name) != DEFAULT_COLUMN_COMB_NAME:
            self.has_output_column_name = False
            self.compared_column_names = self.target_label_column_name + "_" + self.candidate_label_column_name
        else:
            self.compared_column_names = None

        # split the candidate labels
        self.df[self.candidate_label_column_name] = \
            self.df[self.candidate_label_column_name].apply(lambda x: x.split("|") if isinstance(x, str) else [])
        kwargs["df"] = self.df

        for each_method in similarity_method:
            # method1:a1=v1:a2=v2:a3=v3
            try:
                args = each_method.split(':')
                method_name = args[0]
                method_args = {k: v for k, v in [v.split('=') for v in args[1:]]}
                cls = getattr(tl.features.similarity_units,
                              '{}Similarity'.format(''.join([x.capitalize() for x in method_name.split('_')])))
                self.similarity_units.append(cls(tl_args=kwargs, **method_args))
            except:
                raise UnsupportTypeError("Similarity method {} does not exist or wrong arguments".format(each_method))

    @staticmethod
    def get_all_similarity_models():
        pass
        # for name, obj in inspect.getmembers(foo):
        #     if inspect.isclass(obj):
        #         print
        #         obj

    def get_similarity_score(self):
        scores = defaultdict(list)
        for _, each_row in self.df.iterrows():
            for each_similarity_unit in self.similarity_units:
                # the output column name, should be the type + config for this similarity calculation unit
                similarity_unit_name = each_similarity_unit.get_name()
                # get max score amount all labels of candidate node and use the highest one
                max_score = 0
                all_labels = each_row[self.candidate_label_column_name]
                target_label = each_row[self.target_label_column_name]
                if isinstance(all_labels, list):
                    for each_label in all_labels:
                        each_similarity_score = each_similarity_unit.similarity(str(target_label), str(each_label))
                        if each_similarity_score > max_score:
                            max_score = each_similarity_score
                if self.has_output_column_name:
                    similarity_unit_name = self.compared_column_names
                elif self.compared_column_names:
                    similarity_unit_name = self.compared_column_names + "_" + similarity_unit_name
                scores[similarity_unit_name].append(max_score)

        # append the scores to input df
        df_scores = pd.DataFrame.from_dict(scores)
        output_df = pd.concat([self.original_df, df_scores], axis=1)
        return output_df
