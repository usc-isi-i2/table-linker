import pandas as pd
import re
import rltk.similarity as similarity
from tl.exceptions import RequiredInputParameterMissingException
from statistics import mode
import gzip
from pyrallel import ParallelProcessor
from multiprocessing import cpu_count
import itertools
import collections
import os
from tl.features import context_property_match


class MatchContext(object):
    def __init__(self, input_path, similarity_string_threshold, similarity_quantity_threshold,
                 string_separator, missing_property_replacement_factor, ignore_column_name, output_column_name,
                 context_path=None, custom_context_path=None, use_cpus=None):
        self.final_data = pd.read_csv(input_path, dtype=object)
        self.data = pd.DataFrame()
        self.final_property_similarity_list = []
        self.value_debug_list = []
        self.result_data = pd.DataFrame()
        self.inverse_context_dict = {}
        self.is_custom = False
        self.missing_property_replacement_factor = missing_property_replacement_factor
        if context_path is None and custom_context_path is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("context_path", "custom_context_path"))
        self.final_data['index_1'] = self.final_data.index
        self.final_data['column_row'] = list(
            zip(self.final_data['column'], self.final_data['row']))
        self.final_data['label_clean'] = self.final_data['label_clean'].fillna("")
        if ignore_column_name in self.final_data.columns:
            self.final_data[ignore_column_name] = self.final_data[ignore_column_name].astype('float')
            self.final_data_subset = self.final_data[self.final_data[ignore_column_name] == 0]
            self.to_result_data = self.final_data[self.final_data[ignore_column_name] == 1]
        else:
            self.final_data_subset = self.final_data
            self.to_result_data = None
        # self.context = self.read_context_file(context_path=context_path, custom_context_path=custom_context_path)
        self.context_path = context_path
        self.custom_context_path = custom_context_path
        self.output_column_name = output_column_name

        self.similarity_string_threshold = similarity_string_threshold
        self.similarity_quantity_threshold = similarity_quantity_threshold
        self.string_separator = string_separator.replace('"', '')
        self.properties_with_score_metric = pd.DataFrame(columns=['property', 'position', 'value', 'min_sim'])
        # The following is a dictionary that stores the q_nodes that match with multiple properties
        # with equal similarity.
        self.equal_matched_properties = {}
        self.use_cpus = use_cpus

    def call_for_context(self):
        obj_val = context_property_match.MatchContextProperty(self.final_data_subset, self.to_result_data,
                                                              self.similarity_string_threshold,
                                                              self.similarity_quantity_threshold,
                                                              self.string_separator,
                                                              self.missing_property_replacement_factor,
                                                              self.output_column_name,
                                                              self.context_path, self.custom_context_path,
                                                              self.use_cpus, save_property_scores=None)
        return obj_val.process_data_by_column()
