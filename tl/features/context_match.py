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


class MatchContext(object):
    def __init__(self, input_path, similarity_string_threshold, similarity_quantity_threshold,
                 string_separator, missing_property_replacement_factor, ignore_column_name, pseudo_gt_column_name,
                 output_column_name, context_path=None, custom_context_path=None, use_cpus=None,
                 save_property_scores=None, use_saved_property_scores=None):
        self.final_data = pd.read_csv(input_path, dtype=object)
        self.data = pd.DataFrame()
        self.final_property_similarity_list = []
        self.value_debug_list = []
        self.result_data = pd.DataFrame()
        self.only_inverse = False
        self.inverse_context_dict = {}
        self.save_property_scores = save_property_scores
        self.use_saved_property_scores = use_saved_property_scores
        self.is_custom = False
        self.equal_matched_properties = {}
        self.missing_property_replacement_factor = missing_property_replacement_factor
        if context_path is None and custom_context_path is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("context_path", "custom_context_path"))
        self.final_data['index_1'] = self.final_data.index
        self.final_data['column_row'] = list(
            zip(self.final_data['column'], self.final_data['row']))
        self.final_data['label_clean'] = self.final_data['label_clean'].fillna("")
        if pseudo_gt_column_name is not None and pseudo_gt_column_name in self.final_data.columns:
            self.final_data[pseudo_gt_column_name] = self.final_data[pseudo_gt_column_name].astype('float')
            self.final_data_subset = self.final_data[self.final_data[pseudo_gt_column_name] == 1]
            self.to_result_data = self.final_data[self.final_data[pseudo_gt_column_name] == -1]
            self.context_property_column = "pseudo_gt_context_property"
            self.context_similarity_column = "pseudo_gt_context_similarity"
            self.context_debug_column = "pseudo_gt_context_prop_sim_q_node"
        else:
            if ignore_column_name in self.final_data.columns:
                self.final_data[ignore_column_name] = self.final_data[ignore_column_name].astype('float')
                self.final_data_subset = self.final_data[self.final_data[ignore_column_name] == 0]
                self.to_result_data = self.final_data[self.final_data[ignore_column_name] == 1]
                self.context_property_column = "ignore_context_property"
                self.context_similarity_column = "ignore_context_similarity"
                self.context_debug_column = "ignore_context_prop_sim_q_node"
            else:
                self.final_data_subset = self.final_data
                self.to_result_data = None
                self.context_property_column = "context_property"
                self.context_similarity_column = "context_similarity"
                self.context_debug_column = "context_property_similarity_q_node"
        self.output_column_name = output_column_name
        self.context = self.read_context_file(context_path=context_path, custom_context_path=custom_context_path)
        self.similarity_string_threshold = similarity_string_threshold
        self.similarity_quantity_threshold = similarity_quantity_threshold
        self.string_separator = string_separator.replace('"', '')
        self.properties_with_score_metric = pd.DataFrame(columns=['property', 'position', 'value', 'min_sim'])
        # The following is a dictionary that stores the q_nodes that match with multiple properties
        # with equal similarity.
        self.string_separator = string_separator.replace('"', '')
        self.properties_with_score_metric = pd.DataFrame(columns=['property', 'position', 'value', 'min_sim'])
        # The following is a dictionary that stores the q_nodes that match with multiple properties
        # with equal similarity.
        self.equal_matched_properties = {}
        if not use_cpus:
            self.use_cpus = cpu_count()
        else:
            self.use_cpus = min(cpu_count(), use_cpus)

    def read_context_file(self, context_path=None, custom_context_path=None) -> dict:
        context_dict = {}
        custom_context_dict = {}
        if context_path:
            f = open(context_path)
            node1_column = "qnode"
            node2_column = "context"
            context_dict = self._read_context_file_line(f, node1_column, node2_column)
            f.close()
        if custom_context_path:
            extension = os.path.splitext(custom_context_path)[1]
            if extension == '.gz':
                f = gzip.open(custom_context_path, 'rt')
            else:
                f = open(custom_context_path)
            node1_column = "node1"
            node2_column = "node2"
            custom_context_dict = self._read_context_file_line(f, node1_column, node2_column)
            f.close()

        merged_context_dict = collections.defaultdict(str)
        for key, val in itertools.chain(context_dict.items(), custom_context_dict.items()):
            merged_context_dict[key] += val
        return merged_context_dict

    @staticmethod
    def _read_context_file_line(f, node1_column: str, node2_column: str) -> dict:
        context_dict = {}
        feature_idx = -1
        node_idx = -1
        for line in f:
            row = line.strip().split('\t')
            if node1_column in row and node2_column in row:  # first line
                feature_idx = row.index(node2_column)
                node_idx = row.index(node1_column)
            else:
                context_dict[row[node_idx]] = row[feature_idx]

        return context_dict

    @staticmethod
    def quantity_score(quantity_1: float, quantity_2: float) -> float:
        """
        Purpose: Calculates the score between two quantities by taking the absolute difference between them and
        dividing by the max of both.
        It is then subtracted from 1.
        Returns: score
        """
        if quantity_1 == 0.0 and quantity_2 == 0.0:
            return 1
        max_val = max(abs(quantity_1), abs(quantity_2))
        abs_diff = abs(quantity_1 - quantity_2)
        final_val = 1 - (abs_diff / max_val)
        return final_val

    def multiple_properties_match(self, q_node: str, old_property: str, new_property: str):
        """
        Purpose: Both the properties are matched with equal similarity. Stored in the dictionary
        Args:
            q_node: The kg_id of the current row
            old_property: The property that is currently matched to the kg_id
            new_property: The property that might match better, so stored for later.
        """
        if q_node in self.equal_matched_properties:
            temp_list = self.equal_matched_properties.get(q_node, None)
            if new_property not in temp_list:
                temp_list.append(new_property)
                self.equal_matched_properties[q_node] = temp_list
        else:
            if old_property != new_property:
                self.equal_matched_properties[q_node] = [old_property, new_property]

    def match_context_with_type(self, context: str, q_node: str, all_property_set: set, context_data_type: str,
                                property_check: str) -> (str, float):
        """
        Purpose: Matching the given context (of type numerical/quantity/string/date) to the property
        with highest similarity
        Args:
            context: Passed piece of context that needs to be matched.
            q_node: kg_id of the current row.
            all_property_set: Contains the list of properties and their values for the given q_node.
            context_data_type = "q", "i", "d" represents that the property value is of type quantity, item and date
            year respectively.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        :param property_check:
        :param q_node:
        :param all_property_set:
        :param context:
        :param context_data_type:
        """

        property_set = {prop for prop in all_property_set if prop.lower().startswith(context_data_type.lower())}
        prop_val = ""
        max_sim = 0.0
        value_matched_to = ""
        q_node_matched_to = ""
        # We need to check if the quantity present in the check_for is also present in the properties result

        if context_data_type == 'q':
            try:
                check_for = float(context.replace('"', ''))
            except ValueError:
                check_for = ""
        elif context_data_type == 'd':
            check_for = context.split(".")[0]
            check_for = self.remove_punctuation(check_for)
        else:
            check_for = self.preprocess(context)

        for prop in property_set:
            prop = prop.split(":")
            p_value = prop[0]
            if (property_check is not None and property_check == prop[1]) or property_check is None:
                if context_data_type == 'q':
                    check_with_temp = p_value[1:]
                    check_with_temp = check_with_temp.replace('"', '')
                    # The following line handles cases q12wr or equivalent.
                    try:
                        check_with = float(check_with_temp)
                    except ValueError:
                        continue
                    if isinstance(check_with, float) or isinstance(check_with, int):
                        value = self.quantity_score(check_with, check_for)
                        if value >= self.similarity_quantity_threshold and value > max_sim:
                            prop_val = prop[1]
                            max_sim = value
                            value_matched_to = check_with_temp
                            self.equal_matched_properties.pop(q_node, None)
                        elif value >= self.similarity_quantity_threshold and value == max_sim:
                            self.multiple_properties_match(q_node, prop_val, prop[1])

                else:
                    check_with = self.remove_punctuation(p_value[1:])
                    if context_data_type == 'd':
                        if check_for == check_with:
                            prop_val = prop[1]
                            max_sim = 1.0
                            value_matched_to = check_with
                            self.equal_matched_properties.pop(q_node, None)
                        elif check_for == check_with:
                            self.multiple_properties_match(q_node, prop_val, prop[1])
                    elif context_data_type == "i":
                        sim = similarity.hybrid.symmetric_monge_elkan_similarity(self.preprocess(check_with), check_for)
                        if sim >= self.similarity_string_threshold and sim > max_sim:
                            if len(prop) > 1:  # Resolves error if the context does not have a property
                                prop_val = prop[1]
                                if (not prop[1].startswith("P")) and (prop[-2].startswith("P")):
                                    prop_val = prop[-2]
                                max_sim = sim
                                value_matched_to = check_with
                                if len(prop) > 2:
                                    q_node_matched_to = prop[2]
                                self.equal_matched_properties.pop(q_node, None)
                        elif sim >= self.similarity_string_threshold and sim == max_sim and len(prop) > 1:
                            self.multiple_properties_match(q_node, prop_val, prop[1])

        max_sim = round(max_sim, 4)
        return prop_val, max_sim, value_matched_to, q_node_matched_to

    def preprocess(self, word: str) -> list:
        word = word.lower()
        preprocessed_word = self.remove_punctuation(word)
        preprocessed_word = preprocessed_word.split(" ")
        return preprocessed_word

    @staticmethod
    def remove_punctuation(input_string: str) -> str:
        result = re.sub(r'[^\w\s]', '', input_string)
        return result

    def process_context_string(self, s_context: str, q_node: str, all_property_set: set, property_check: str) -> (
            str, float):
        """
        Purpose: Before matching with the properties, necessary processing to handle cases where the comma-separated
        values match to the same properties.
        Args:
            s_context: Passed piece of context that needs to be matched.
            all_property_set: Contains the list of properties and their values for the given q_node.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        :param property_check:
        :param all_property_set:
        :param s_context:
        :param q_node:
        """

        if self.string_separator in s_context:
            # All the items separated by, should have same property. Finding properties for each item and
            # appending the property to temp
            temp = []
            sim_list = []
            value_matched_to_list = []
            q_node_matched_to_list = []
            sub_context_list = s_context.split(self.string_separator)
            sub_s_context_dict = dict.fromkeys(sub_context_list).keys()
            for sub_s_context in sub_s_context_dict:
                p, s, temp_value_matched_to, temp_q_node_matched_to = self.match_context_with_type(
                    sub_s_context, q_node, all_property_set, context_data_type="i", property_check=property_check)
                if p != "":
                    temp.append(p)
                    sim_list.append(s)
                    value_matched_to_list.append(temp_value_matched_to)
                    q_node_matched_to_list.append(temp_q_node_matched_to)
            # If all elements in temp have same value for property return that property
            # Update: If there are multiple properties, we take the property that has maximum occurrences.
            if len(set(temp)) == 1:
                p_val = temp[0]
                value_matched_to = value_matched_to_list[0]
                q_node_matched_to = q_node_matched_to_list[0]
                sim = max(sim_list)
            elif len(temp) > 1:
                if len(set(temp)) == len(temp):
                    # If all the properties are matched are different
                    sim = max(sim_list)
                    sim_ind = sim_list.index(sim)
                    p_val = temp[sim_ind]
                    value_matched_to = value_matched_to_list[sim_ind]
                    q_node_matched_to = q_node_matched_to_list[sim_ind]
                    sim = sim / len(temp)
                else:
                    most_common_property = mode(temp)
                    # indices_for_prop = temp.index(most_common_property)`
                    new_sim_list = []
                    q_node_matched_to = ""
                    value_matched_to = ""
                    for k in range(len(temp)):
                        if temp[k] == most_common_property:
                            new_sim_list.append(sim_list[k])
                            value_matched_to = value_matched_to + value_matched_to_list[k]
                            q_node_matched_to = q_node_matched_to + q_node_matched_to_list[k]
                    p_val = most_common_property
                    sim = sum(new_sim_list) / len(new_sim_list)
            else:
                p_val = ""
                sim = 0.0
                value_matched_to = ""
                q_node_matched_to = ""

        else:
            p_val, sim, value_matched_to, q_node_matched_to = self.match_context_with_type(s_context,
                                                                                           q_node, all_property_set,
                                                                                           context_data_type="i",
                                                                                           property_check=property_check)
        max_sim = round(sim, 4)
        return p_val, max_sim, value_matched_to, q_node_matched_to

    def inverse_property_calculation_and_score_calculation(self, column_val):
        columns = ["column", "row", "property", "number_of_occurrences", 'min_sim']
        properties_set = pd.DataFrame(columns=columns)
        self.properties_with_score_metric = pd.DataFrame(columns=['column', 'property', 'value', 'min_sim'])
        # counter is the index for the properties_set
        counter = 0
        for value_of_row, value_of_column, list_of_properties, list_of_sim in zip(self.data['row'],
                                                                                  self.data['column'],
                                                                                  self.data[
                                                                                      'reverse_context_property'],
                                                                                  self.data[
                                                                                      'reverse_context_similarity']):
            dict_of_properties = {(list_of_properties[i], i): i for i in range(len(list_of_properties))}
            for (d_property, j) in dict_of_properties:
                if d_property != "":
                    if d_property not in properties_set.property.values:
                        # Add a new row
                        properties_set.loc[counter] = [value_of_column, value_of_row, d_property, "1",
                                                       list_of_sim[j]]
                        counter = counter + 1
                    else:
                        # Increment the count if same position, else add another row with the new position
                        ind = properties_set[(properties_set['property'] == d_property) & (
                                properties_set['row'] == value_of_row)].index.values
                        if len(ind) != 0:
                            old_count = properties_set['number_of_occurrences'].values[ind]
                            new_count = float(old_count[0]) + 1
                            old_sim = properties_set['min_sim'].values[ind]
                            new_sim = str(max(float(old_sim), float(list_of_sim[j])))
                            properties_set.iloc[ind, properties_set.columns.get_loc('number_of_occurrences')] = str(
                                new_count)
                            properties_set.iloc[ind, properties_set.columns.get_loc('min_sim')] = new_sim
                        else:
                            properties_set.loc[counter] = [value_of_column, value_of_row, d_property, "1",
                                                           list_of_sim[j]]
                            counter = counter + 1
                            # Part 1 - b - Calculating each individual property's value (also considers position)
        property_value_list = []
        for occurrences in zip(properties_set['number_of_occurrences']):
            # Record the occurrences of a particular property.
            if float(occurrences[0]) > 0:
                value = round(1 / float(occurrences[0]), 4)
            else:
                value = 0
            property_value_list.append(value)
        properties_set['prop_val'] = property_value_list

        properties_l_df = properties_set['property']
        properties_list = properties_l_df.values.tolist()
        c_prop_set = dict.fromkeys(properties_list).keys()
        row_list = properties_set['row']
        row_l = row_list.values.tolist()
        c_row_set = dict.fromkeys(row_l).keys()
        counter = 0
        for prop in c_prop_set:
            # Update : Added the minimum similarity values for each property
            ind = properties_set[
                (properties_set['property'] == prop)].index.values
            if len(ind) != 0:
                min_values_list = []
                property_cal = 0
                for i in ind:
                    prop_val = properties_set['prop_val'].values[i]
                    property_cal = round((property_cal + float(prop_val)), 4)
                    min_values_list.append(properties_set['min_sim'].values[i])
                min_sim_value = min(min_values_list)
                f_prop_cal = round(property_cal / len(c_row_set), 4)
                self.properties_with_score_metric.loc[counter] = [str(column_val) + "_inv", prop, f_prop_cal,
                                                                  min_sim_value]
                counter = counter + 1
        self.properties_with_score_metric = self.properties_with_score_metric.sort_values(['value'],
                                                                                          ascending=False)
        final_scores_list = []
        final_value_debug_str_list = []
        for properties_list, sim_list, value_debug_str_list, current_score, current_actual_score in zip(
                self.data['reverse_context_property'],
                self.data['reverse_context_similarity'],
                self.data[
                    'reverse_context_property_similarity_q_node'],
                self.data[self.output_column_name], self.data['actual_' + self.output_column_name]):
            sum_prop = 0
            property_values_list = []
            for i in range(len(properties_list)):
                curr_property = properties_list[i]
                if curr_property != "":
                    sim_value = sim_list[i].split("$$")[0]

                    ind_df = self.properties_with_score_metric[
                        (self.properties_with_score_metric['property'] == curr_property)]
                    value = ind_df['value'].tolist()
                    prop_value = value[0]
                    sum_prop = round(sum_prop + (float(prop_value) * float(sim_value)), 4)
                    property_values_list.append(prop_value)
                    value_debug_str_list[i] = value_debug_str_list[i].replace(curr_property,
                                                                              curr_property + "(" + str(
                                                                                  prop_value) + ")")
            final_value_debug_str_list.append("|".join(value_debug_str_list))
            final_scores_list.append(float(sum_prop) + float(current_actual_score))
        self.data['reverse_context_property_similarity_q_node'] = final_value_debug_str_list
        self.data['actual_' + self.output_column_name] = final_scores_list
        final_scores_list = [1 if score > 1 else score for score in final_scores_list]
        self.data[self.output_column_name] = final_scores_list

    def calculate_property_value(self, column_value):
        """
        Purpose: Calculates the score by using the properties and the similarity with which they matched.
        """
        # Starting the score calculations
        # Part 1: Calculating Property values for each of the property that appear in the data file
        # Part 1 - a: Calculating the number of occurrences in each cell.
        columns = ["column", "row", "property", "position", "number_of_occurrences", 'min_sim']
        properties_set = pd.DataFrame(columns=columns)
        self.properties_with_score_metric = pd.DataFrame(columns=['column', 'property', 'position', 'value', 'min_sim'])
        # counter is the index for the properties_set
        counter = 0
        for value_of_row, value_of_column, list_of_properties, list_of_sim in zip(self.data['row'],
                                                                                  self.data['column'],
                                                                                  self.data[
                                                                                      self.context_property_column],
                                                                                  self.data[
                                                                                      self.context_similarity_column]):

            dict_of_properties = {(list_of_properties[i], i): i for i in range(len(list_of_properties))}
            for (d_property, j) in dict_of_properties:
                position = j + 1
                if d_property != "":
                    if d_property not in properties_set.property.values:
                        # Add a new row
                        properties_set.loc[counter] = [value_of_column, value_of_row, d_property,
                                                       str(position), "1", list_of_sim[j]]
                        counter = counter + 1
                    else:
                        # Increment the count if same position, else add another row with the new position
                        ind = properties_set[(properties_set['property'] == d_property) & (
                                properties_set['row'] == value_of_row) & (
                                                     properties_set['position'] == str(position))].index.values
                        if len(ind) != 0:
                            old_count = properties_set['number_of_occurrences'].values[ind]
                            new_count = float(old_count[0]) + 1
                            old_sim = properties_set['min_sim'].values[ind]
                            new_sim = str(max(float(old_sim), float(list_of_sim[j])))
                            properties_set.iloc[ind, properties_set.columns.get_loc('number_of_occurrences')] = str(
                                new_count)
                            properties_set.iloc[ind, properties_set.columns.get_loc('min_sim')] = new_sim
                        else:
                            properties_set.loc[counter] = [value_of_column, value_of_row, d_property,
                                                           str(position), "1", list_of_sim[j]]
                            counter = counter + 1
                            # Part 1 - b - Calculating each individual property's value (also considers position)
        property_value_list = []
        for occurrences in zip(properties_set['number_of_occurrences']):
            # Record the occurrences of a particular property.
            if float(occurrences[0]) > 0:
                value = round(1 / float(occurrences[0]), 4)
            else:
                value = 0
            property_value_list.append(value)
        properties_set['prop_val'] = property_value_list

        properties_l_df = properties_set['property']
        properties_list = properties_l_df.values.tolist()
        c_prop_set = dict.fromkeys(properties_list).keys()
        positions_list = properties_set['position']
        position_l = positions_list.values.tolist()
        c_pos_set = dict.fromkeys(position_l).keys()
        row_list = properties_set['row']
        row_l = row_list.values.tolist()
        c_row_set = dict.fromkeys(row_l).keys()
        counter = 0
        for prop in c_prop_set:
            for pos in c_pos_set:
                # Update : Added the minimum similarity values for each property
                ind = properties_set[
                    (properties_set['property'] == prop) & (properties_set['position'] == pos)].index.values
                if len(ind) != 0:
                    min_values_list = []
                    property_cal = 0
                    for i in ind:
                        prop_val = properties_set['prop_val'].values[i]
                        property_cal = round((property_cal + float(prop_val)), 4)
                        min_values_list.append(properties_set['min_sim'].values[i])
                    min_sim_value = min(min_values_list)
                    f_prop_cal = round(property_cal / len(c_row_set), 4)
                    self.properties_with_score_metric.loc[counter] = [str(column_value), prop, pos, f_prop_cal,
                                                                      min_sim_value]
                    counter = counter + 1
        self.properties_with_score_metric = self.properties_with_score_metric.sort_values(['value'], ascending=False)

    def calculate_score(self):
        # Sum up the individual property values for a row (update:multiply with the similarity)
        final_scores_list = []
        final_value_debug_str_list = []
        for properties_list, sim_list, value_debug_str_list in zip(self.data[self.context_property_column],
                                                                   self.data[self.context_similarity_column],
                                                                   self.data[self.context_debug_column]):
            sum_prop = 0
            property_values_list = []
            for i in range(len(properties_list)):
                curr_property = properties_list[i]
                if curr_property != "":
                    sim_value = sim_list[i].split("$$")[0]

                    ind_df = self.properties_with_score_metric[
                        (self.properties_with_score_metric['property'] == curr_property) & (
                                self.properties_with_score_metric['position'] == str(i + 1))]
                    value = ind_df['value'].tolist()
                    prop_value = value[0]
                    sum_prop = round(sum_prop + (float(prop_value) * float(sim_value)), 4)
                    property_values_list.append(prop_value)
                    value_debug_str_list[i] = value_debug_str_list[i].replace(curr_property,
                                                                              curr_property + "(" + str(
                                                                                  prop_value) + ")")
            final_value_debug_str_list.append("|".join(value_debug_str_list))
            final_scores_list.append(sum_prop)
        self.data[self.context_debug_column] = final_value_debug_str_list
        self.data['actual_' + self.output_column_name] = final_scores_list
        final_scores_list = [1 if score > 1 else score for score in final_scores_list]
        self.data[self.output_column_name] = final_scores_list

    def process_data_by_column(self):
        """
        Purpose: Groups the dataframe by column, sends for property matching and score calculation
        and joins the grouped data.
        Returns: A Dataframe with the given column name containing the score with which the context matched
        to properties.
        """
        # Identify the major important columns in all the columns present.
        all_columns_properties_values_df = pd.DataFrame()
        corresponding_num_labels = {}
        grouped_object = self.final_data_subset.groupby(['column'])
        for cell, group in grouped_object:
            number_of_rows = len(group['label_clean'].unique())
            corresponding_num_labels[cell] = number_of_rows
        max_value = max(corresponding_num_labels.values())
        major_column = [k for k, v in corresponding_num_labels.items() if v == max_value]
        all_labels = dict(zip(self.final_data_subset.column_row,
                              self.final_data_subset.label_clean))
        if self.use_saved_property_scores:
            saved_properties_df = pd.read_csv(self.use_saved_property_scores)

        for cell, group in grouped_object:
            self.data = group.reset_index(drop=True)
            if self.use_saved_property_scores:
                current_saved_properties_df = saved_properties_df[saved_properties_df['column'] == str(cell)]
                current_saved_properties_df = current_saved_properties_df.drop_duplicates(subset='position',
                                                                                          keep='first')
            else:
                current_saved_properties_df = None
            current_labels = dict(zip(self.data.column_row, self.data.label_clean))
            if cell in major_column:
                labels_to_process_for_infer_context = {k: all_labels[k] for k in all_labels
                                                       if k not in current_labels if k != ""}
                self.process_data_context(cell, labels_to_process_for_infer_context, current_saved_properties_df)
            else:
                self.process_data_context(cell, [], current_saved_properties_df)
            all_columns_properties_values_df = pd.concat([all_columns_properties_values_df,
                                                          self.properties_with_score_metric])
            self.result_data = pd.concat([self.result_data, self.data])
        if self.to_result_data is not None:
            only_inverse_context_data = self.to_result_data.groupby(['column'])
            for cell, group in only_inverse_context_data:
                self.data = group.reset_index(drop=True)
                if cell in major_column:

                    labels_to_process_for_infer_context = {k: all_labels[k] for k in all_labels
                                                           if k not in current_labels if k != ""}
                    self.process_data_context(cell, labels_to_process_for_infer_context, None, only_inverse = True)

                self.result_data = pd.concat([self.result_data, self.data])

        # self.result_data = pd.concat([self.result_data, self.to_result_data])
        self.result_data = self.result_data.sort_values(by='index_1')
        self.result_data = self.result_data.reset_index(drop=True)
        self.result_data = self.result_data.drop(columns='index_1')
        if self.output_column_name not in self.result_data.columns:
            self.result_data = self.result_data.reindex(columns=self.result_data.columns.tolist() + [
                self.output_column_name, self.context_property_column, 'actual_' + self.output_column_name,
                self.context_similarity_column,
                self.context_debug_column])
        self.result_data[self.output_column_name] = self.result_data[self.output_column_name].fillna(0.0)
        self.result_data['actual_' + self.output_column_name] = self.result_data[
            'actual_' + self.output_column_name].fillna(0.0)
        self.result_data = self.result_data.astype(object)
        self.result_data['reverse_context_property'] = ""
        self.result_data['reverse_context_similarity'] = ""
        self.result_data['reverse_context_property_similarity_q_node'] = ""
        for q_node_1 in self.inverse_context_dict:
            q_node_val = self.inverse_context_dict[q_node_1]
            property_list = []
            similarity_list = []
            q_node_matched_from_list = []
            q_node_value_list = []
            debug_value = []
            for property_l in q_node_val:
                [q_node_value, sim, q_node_matched_from] = q_node_val[property_l]
                q_node_matched_from_list.append(q_node_matched_from)
                q_node_value_list.append(q_node_value)
                property_list.append(property_l)
                similarity_list.append(sim)
                debug_value.append("/".join([property_l, q_node_matched_from, str(sim), q_node_value]))
            try:

                index_values = self.result_data[self.result_data['kg_id'] == q_node_1].index.values
                for index_val in index_values:
                    self.result_data.iloc[
                        index_val, self.result_data.columns.get_loc('reverse_context_similarity')] = similarity_list
                    self.result_data.iloc[
                        index_val, self.result_data.columns.get_loc('reverse_context_property')] = property_list
                    self.result_data.iloc[index_val, self.result_data.columns.get_loc(
                        'reverse_context_property_similarity_q_node')] = debug_value
            except IndexError:
                continue
        grouped_object = self.result_data.groupby(['column'])
        result_data_2 = pd.DataFrame()
        for cell, group in grouped_object:
            self.data = group.reset_index(drop=True)
            if cell not in major_column:
                self.inverse_property_calculation_and_score_calculation(cell)
                result_data_2 = pd.concat([result_data_2, self.data])
            else:
                result_data_2 = pd.concat([result_data_2, self.data])
            all_columns_properties_values_df = pd.concat(
                [all_columns_properties_values_df, self.properties_with_score_metric])
        result_data_2 = result_data_2.drop(columns=['column_row'])
        if self.save_property_scores:
            all_columns_properties_values_df.to_csv(self.save_property_scores, index=False)
        return result_data_2

    def matches_to_check_for(self, v, q_node, all_property_set, property_check):
        # For quantity matching, we will give multiple tries to handle cases where numbers are separated with
        new_v = v.replace('"', '')
        to_match_1 = new_v.replace(",", "")
        to_match_2 = to_match_1.replace(".", "0")

        num_v = None

        if " " in to_match_2:
            split_v = to_match_1.split(" ")
            for s in split_v:
                if not s == ".":
                    new_s = s.replace(".", "0")
                    if new_s.isnumeric():
                        num_v = s

        if to_match_1.isnumeric() or to_match_2.isnumeric() or num_v is not None:
            property_v, sim, value_matched_to, q_node_matched_to = self.match_context_with_type(
                to_match_1, q_node, all_property_set, context_data_type="d", property_check=property_check)
            if (property_v == "") and (to_match_1.count(".") <= 1):
                # Number of decimals shouldn't be greater than one.
                if to_match_1.isnumeric() or to_match_2.isnumeric():
                    property_v, sim, value_matched_to, q_node_matched_to = self.match_context_with_type(
                        to_match_1, q_node,
                        all_property_set,
                        context_data_type="q", property_check=property_check)
                elif num_v is not None:
                    property_v, sim, value_matched_to, q_node_matched_to = self.match_context_with_type(
                        num_v, q_node, all_property_set, context_data_type="q", property_check=property_check)
                    property_v_2, sim_2, value_matched_to_2, q_node_matched_to_2 = self.process_context_string(
                        v, q_node,
                        all_property_set, property_check=property_check)
                    if sim_2 > sim:
                        property_v = property_v_2
                        sim = sim_2
                        value_matched_to = value_matched_to_2
                        q_node_matched_to = q_node_matched_to_2
        else:
            property_v, sim, value_matched_to, q_node_matched_to = self.process_context_string(
                v, q_node, all_property_set, property_check
            )
        return property_v, sim, value_matched_to, q_node_matched_to

    def match_for_inverse_context(self, q_node, all_property_set, labels_for_inverse_context, q_label):
        context_data_type = 'i'
        property_set = {prop for prop in all_property_set if prop.lower().startswith(context_data_type.lower())}
        prop = ""
        matched_to = ""
        max_sim = 0
        q_node_matched = ""
        from_q_node_matched = ""
        for property_l in property_set:
            split_list = property_l.split(":")
            label_val = split_list[0]
            label_val_clean = label_val[1:]
            label_val_clean_list = label_val_clean.split(" ")
            property_value = split_list[1]
            q_node_val = split_list[2]
            for m in labels_for_inverse_context:
                label_value_row = labels_for_inverse_context[m]
                label_value_list = label_value_row.split(" ")
                sim = similarity.hybrid.symmetric_monge_elkan_similarity(label_value_list, label_val_clean_list)
                if sim >= self.similarity_string_threshold:
                    if sim > max_sim:
                        prop = property_value
                        max_sim = sim
                        matched_to = q_label
                        q_node_matched = q_node_val
                        from_q_node_matched = q_node
        max_sim = round(max_sim, 4)
        result_list = [q_node_matched, prop, matched_to, str(max_sim), from_q_node_matched]

        return result_list

    def mapper(self, idx, q_node, q_node_label, val, labels_for_inverse_context, important_properties_per_observation):
        """
        Purpose: Mapper to the parallel processor to process each row parallely
        Returns: The index of row, property string and the context similarity
                 string
        :param important_properties_per_observation:
        :param q_node_label:
        :param labels_for_inverse_context:
        :param idx:
        :param q_node:
        :param val:
        """
        prop_list = []
        sim_list = []
        matched_to_list = []
        # if there is empty context in the data file
        context_value = self.context.get(q_node, None)
        if context_value:
            all_property_list = re.split(r'(?<!\\)\|', context_value)
            if not self.is_custom:
                all_property_list[0] = all_property_list[0][1:]
                all_property_list[-1] = all_property_list[-1][:-1]
        else:
            return idx, [], [], ["0.0"], []
        all_property_set = set(all_property_list)
        if not self.only_inverse:
            try:
                val_list = val.split("|")
            except AttributeError:
                val_list = ""
            val_positions = list(range(0, len(val_list)))
            val_dict = dict(zip(val_positions, val_list))
            for p in val_dict:
                v = val_dict[p]
                # For quantity matching, we will give multiple tries to handle cases where numbers are separated with
                if important_properties_per_observation is not None:
                    property_check = important_properties_per_observation.get(p+1, None)
                else:
                    property_check = None
                if self.remove_punctuation(v) != "":
                    property_v, sim, value_matched_to, q_node_matched_to = self.matches_to_check_for(v,
                                                                                                     q_node,
                                                                                                     all_property_set,
                                                                                                     property_check)
                    prop_list.append(property_v)
                    sim_list.append(str(sim))
                    value_for_debug = "/".join([property_v, q_node_matched_to, str(sim), value_matched_to])
                    matched_to_list.append(value_for_debug)
        else:
            matched_to_list = []
            prop_list = []
            sim_list = []
        results = self.match_for_inverse_context(q_node, all_property_set, labels_for_inverse_context, q_node_label)
        return idx, matched_to_list, prop_list, sim_list, results

    def collector(self, idx, value_debug_str, prop_str, sim_str, results):
        """
        Purpose: collects the output of the mapper and appends to
                 final_property_list.
        :param results:
        :param sim_str:
        :param prop_str:
        :param value_debug_str:
        :param idx:
        """
        self.final_property_similarity_list.append([idx, prop_str, sim_str, value_debug_str])
        if results:
            if not results[0] == "":
                if results[0] in self.inverse_context_dict:
                    current_element = self.inverse_context_dict.get(results[0])
                    current_element[results[1]] = results[2:]
                else:
                    current_element = {results[1]: results[2:]}
                    self.inverse_context_dict[results[0]] = current_element

    def process_data_context(self, column_val, labels_to_process_for_inverse_context, current_saved_properties_df,
                             only_inverse = False):
        """
        Purpose: Processes the dataframe, reads each context_value separated by
        "|" and tries to match them to either
        date, string or quantity depending upon the structure of the context.
        """
        self.only_inverse = only_inverse
        self.final_property_similarity_list = []
        cpus = self.use_cpus
        if current_saved_properties_df is not None:
            important_properties_per_observation = dict(
                zip(current_saved_properties_df['position'].values, current_saved_properties_df['property'].values))
        else:
            important_properties_per_observation = None
        batch = self.data.shape[0] // cpus
        if cpus > 1:
            pp = ParallelProcessor(cpus, mapper=lambda args: self.mapper(*args),
                                   collector=self.collector, batch_size=batch)
            pp.start()
            range_len = len(self.data.index.values)
            label_list = [labels_to_process_for_inverse_context] * range_len
            important_properties_per_observation_list = [important_properties_per_observation] * range_len
            pp.map(
                zip(self.data.index.values.tolist(), self.data["kg_id"], self.data['label_clean'], self.data["context"],
                    label_list, important_properties_per_observation_list))
            pp.task_done()
            pp.join()
        else:
            for idx, q_node, q_node_label, val in zip(self.data.index.values.tolist(), self.data["kg_id"],
                                                      self.data['label_clean'], self.data["context"]):
                idx, value_debug_str, prop_str, sim_str, results = self.mapper(idx, q_node, q_node_label, val,
                                                                               labels_to_process_for_inverse_context,
                                                                               important_properties_per_observation)
                self.collector(idx, value_debug_str, prop_str, sim_str, results)

        property_sim_df = pd.DataFrame(self.final_property_similarity_list,
                                       columns=["idx", self.context_property_column,
                                                self.context_similarity_column, self.context_debug_column])
        property_sim_df.set_index("idx", drop=True, inplace=True)
        self.data = pd.merge(self.data, property_sim_df,
                             left_index=True, right_index=True)
        self.calculate_property_value(column_val)
        # Recalculate for the most important property for each q_node's that don't have that property.
        unique_positions = self.properties_with_score_metric['position'].unique().tolist()
        important_properties = []
        important_property_value = []
        min_sim_value = []
        # No need of converting others to set as directly referenced from the index.
        unique_positions_dict = {unique_positions[i]: i for i in range(0, len(unique_positions))}

        for pos in unique_positions_dict:
            temp_row = self.properties_with_score_metric[
                self.properties_with_score_metric['position'] == pos].sort_values(
                ['value'], ascending=False).head(1)
            important_properties.append(temp_row['property'].values.tolist()[0])
            important_property_value.append(temp_row['value'].values.tolist()[0])
            min_sim_value.append(temp_row['min_sim'].values.tolist()[0])

        for df_ind, q_node, property_list, similarity_list, context_property_similarity_q_node_list in zip(
                self.data.index, self.data['kg_id'],
                self.data[self.context_property_column], self.data[self.context_similarity_column],
                self.data[self.context_debug_column]):
            # property_list = properties_str.split("|")
            # similarity_list = similarity_str.split("|")
            property_list_dict = {(property_list[i], i): i for i in range(0, len(property_list))}
            # context_property_similarity_q_node_list = context_property_similarity_q_node_str.split("|")
            is_change = False
            for (p_property, p_l) in property_list_dict:
                # If we have any property for that position
                if str(p_l + 1) in unique_positions_dict:
                    ind = unique_positions_dict[str(p_l + 1)]
                    imp_prop = important_properties[ind]
                    if p_property == imp_prop:
                        continue
                    elif p_property == "":
                        # Need to check if this property is present for the particular q_node
                        context_value = self.context.get(q_node, None)
                        # Create a list of this values. In some cases the kg_id may not be present in the context_file.
                        if context_value:
                            # Initial Structuring
                            all_property_list = re.split(r'(?<!\\)\|', context_value)
                            if not self.is_custom:
                                all_property_list[0] = all_property_list[0][1:]
                                all_property_list[-1] = all_property_list[-1][:-1]
                            all_property_set = set(all_property_list)
                            # Separate list of only properties.
                            is_present = False
                            for prop in all_property_set:
                                prop = prop.split(":")
                                if len(prop) > 1:
                                    if prop[1] == imp_prop:
                                        # Early Stop - The property is present but has not matched to the context
                                        is_present = True
                                        break
                            # The property is not present at the location
                            if not is_present:
                                new_sim_val = round(
                                    self.missing_property_replacement_factor * float(min_sim_value[ind]), 4)
                                # Update with new_property
                                is_change = True
                                similarity_list[p_l] = str(new_sim_val) + "$$"
                                property_list[p_l] = imp_prop
                                context_property_similarity_q_node_list[p_l] = "/".join(
                                    [imp_prop, "", str(new_sim_val) + "$$", ""])

                    else:
                        # Another property is present at this location instead.
                        pass
            # equal_matched_properties is a dict
            if q_node in self.equal_matched_properties:
                # temp references to the other possible properties that we can place.
                temp_list = self.equal_matched_properties.get(q_node, None)
                matched_property = temp_list[0]
                if matched_property in property_list_dict:
                    temp_position = property_list.index(matched_property) + 1
                    current_property_value = self.properties_with_score_metric[
                        (self.properties_with_score_metric['property'] == matched_property) &
                        (self.properties_with_score_metric['position'] == str(temp_position))]['value'].values[0]
                    max_property = matched_property
                    max_property_value = current_property_value
                    # Following is a list of two items - contains old_property, possible_new_property
                    for temp_prop in temp_list:
                        if not temp_prop == matched_property:
                            temp_prop_value_l = self.properties_with_score_metric[
                                (self.properties_with_score_metric['property'] == temp_prop) &
                                (self.properties_with_score_metric['position'] == str(temp_position))]['value'].values
                            if len(temp_prop_value_l) >= 1:
                                temp_prop_value = temp_prop_value_l[0]
                                if temp_prop_value > max_property_value:
                                    max_property = temp_prop
                                    max_property_value = temp_prop_value
                    property_list[temp_position - 1] = max_property

            if is_change:
                self.data.at[df_ind, self.context_property_column] = property_list
                self.data.at[df_ind, self.context_similarity_column] = similarity_list
                self.data.at[df_ind, self.context_debug_column] = context_property_similarity_q_node_list
        self.calculate_score()
