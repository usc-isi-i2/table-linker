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
                 string_separator, output_column_name, context_path=None, custom_context_path=None):
        self.final_data = pd.read_csv(input_path, dtype=object)
        self.data = pd.DataFrame()
        self.final_property_similarity_list = []
        self.value_debug_list = []
        self.result_data = pd.DataFrame()
        self.is_custom = False
        if context_path is None and custom_context_path is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("context_path", "custom_context_path"))

        self.context = self.read_context_file(context_path=context_path, custom_context_path=custom_context_path)

        self.output_column_name = output_column_name
        self.similarity_string_threshold = similarity_string_threshold
        self.similarity_quantity_threshold = similarity_quantity_threshold
        self.string_separator = string_separator.replace('"', '')
        self.properties_with_score_metric = pd.DataFrame(columns=['property', 'position', 'value', 'min_sim'])
        # The following is a dictionary that stores the q_nodes that match with multiple properties
        # with equal similarity.
        self.equal_matched_properties = {}

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

    def match_context_with_type(self, context: str, q_node: str, all_property_set: set, context_data_type: str) -> (
            str, float):
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
        :param q_node:
        :param all_property_set:
        :param context:
        :param context_data_type:
        """
        
        property_list = {prop for prop in all_property_set if prop.lower().startswith(context_data_type.lower())}
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

        for prop in property_list:
            prop = prop.split(":")
            p_value = prop[0]
            if context_data_type == 'q':
                check_with_temp = p_value[1:]
                check_with = float(check_with_temp.replace('"', ''))
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

    def process_context_string(self, s_context: str, q_node: str, all_property_set: set) -> (str, float):
        """
        Purpose: Before matching with the properties, necessary processing to handle cases where the comma-separated
        values match to the same properties.
        Args:
            s_context: Passed piece of context that needs to be matched.
            all_property_set: Contains the list of properties and their values for the given q_node.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
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
            for sub_s_context in sub_context_list:
                p, s, temp_value_matched_to, temp_q_node_matched_to = self.match_context_with_type(
                    sub_s_context, q_node, all_property_set, context_data_type="i")
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
            p_val, sim, value_matched_to, q_node_matched_to = self.match_context_with_type(s_context, q_node,
                                                                                           all_property_set,
                                                                                           context_data_type="i")
        max_sim = round(sim, 4)
        return p_val, max_sim, value_matched_to, q_node_matched_to

    def calculate_property_value(self):
        """
        Purpose: Calculates the score by using the properties and the similarity with which they matched.
        """
        # Starting the score calculations
        # Part 1: Calculating Property values for each of the property that appear in the data file
        # Part 1 - a: Calculating the number of occurrences in each cell.
        columns = ["column", "row", "property", "position", "number_of_occurrences", 'min_sim']
        properties_set = pd.DataFrame(columns=columns)
        self.properties_with_score_metric = pd.DataFrame(columns=['property', 'position', 'value', 'min_sim'])
        # counter is the index for the properties_set
        counter = 0
        for value_of_row, value_of_column, value_of_property, value_of_sim in zip(self.data['row'], self.data['column'],
                                                                                  self.data['context_property'],
                                                                                  self.data['context_similarity']):
            list_of_properties = value_of_property.split("|")
            list_of_sim = value_of_sim.split("|")
            # The positions will be denoted by the index. (Alternative: using dictionary instead - extra overhead)
            for j in range(len(list_of_properties)):
                position = j + 1
                if list_of_properties[j] != "":
                    if list_of_properties[j] not in properties_set.property.values:
                        # Add a new row
                        properties_set.loc[counter] = [value_of_column, value_of_row, list_of_properties[j],
                                                       str(position), "1", list_of_sim[j]]
                        counter = counter + 1
                    else:
                        # Increment the count if same position, else add another row with the new position
                        ind = properties_set[(properties_set['property'] == list_of_properties[j]) & (
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
                            properties_set.loc[counter] = [value_of_column, value_of_row, list_of_properties[j],
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
        c_prop_list = dict.fromkeys(properties_list).keys()
        positions_list = properties_set['position']
        position_l = positions_list.values.tolist()
        c_pos_list = list(dict.fromkeys(position_l).keys())
        row_list = properties_set['row']
        row_l = row_list.values.tolist()
        c_row_list = dict.fromkeys(row_l).keys()
        counter = 0
        for prop in c_prop_list:
            for pos in c_pos_list:
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
                    f_prop_cal = round(property_cal / len(c_row_list), 4)
                    self.properties_with_score_metric.loc[counter] = [prop, pos, f_prop_cal, min_sim_value]
                    counter = counter + 1
        self.properties_with_score_metric = self.properties_with_score_metric.sort_values(['value'], ascending=False)

    def calculate_score(self):
        # Sum up the individual property values for a row (update:multiply with the similarity)
        final_scores_list = []
        for properties_str, sim_str in zip(self.data['context_property'], self.data['context_similarity']):
            sim_list = sim_str.split("|")
            properties_list = properties_str.split("|")
            sum_prop = 0
            for i in range(len(properties_list)):
                if properties_list[i] != "":
                    sim_value = sim_list[i].split("$$")[0]
                    ind_df = self.properties_with_score_metric[
                        (self.properties_with_score_metric['property'] == properties_list[i]) & (
                                self.properties_with_score_metric['position'] == str(i + 1))]
                    value = ind_df['value'].tolist()
                    sum_prop = round(sum_prop + (float(value[0]) * float(sim_value)), 4)
            if sum_prop > 1:
                sum_prop = 1
            final_scores_list.append(sum_prop)
        self.data[self.output_column_name] = final_scores_list

    def process_data_by_column(self):
        """
        Purpose: Groups the dataframe by column, sends for property matching and score calculation
        and joins the grouped data.
        Returns: A Dataframe with the given column name containing the score with which the context matched
        to properties.
        """
        grouped_object = self.final_data.groupby(['column'])
        for cell, group in grouped_object:
            self.data = group.reset_index(drop=True)
            self.process_data_context()
            self.result_data = pd.concat([self.result_data, self.data])
            # self.value_debug_list = []

        self.result_data = self.result_data.reset_index(drop=True)
        return self.result_data

    def mapper(self, idx, q_node, val):
        """
        Purpose: Mapper to the parallel processor to process each row parallely
        Returns: The index of row, property string and the context similarity
                 string
        :param idx:
        :param q_node:
        :param val:
        """
        prop_list = []
        sim_list = []
        matched_to_list = []
        # if there is empty context in the data file
        try:
            val_list = val.split("|")
        except AttributeError:
            val_list = ""

        # In some of the files, there is no context for a particular q-node. Removed during context file generation.
        context_value = self.context.get(q_node, None)

        if context_value:
            all_property_list = context_value.split("|")
            if not self.is_custom:
                all_property_list[0] = all_property_list[0][1:]
                all_property_list[-1] = all_property_list[-1][:-1]
        else:
            return idx, "", "", "0.0"
        all_property_set = set(all_property_list)
        val_set = dict.fromkeys(val_list).keys()
        for v in val_list:
            # For quantity matching, we will give multiple tries to handle cases where numbers are separated with
            if self.remove_punctuation(v) != "":
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
                        to_match_1, q_node, all_property_set, context_data_type="d")
                    if (property_v == "") and (to_match_1.count(".") <= 1):
                        # Number of decimals shouldn't be greater than one.
                        if to_match_1.isnumeric() or to_match_2.isnumeric():
                            property_v, sim, value_matched_to, q_node_matched_to = self.match_context_with_type(
                                to_match_1, q_node,
                                all_property_set,
                                context_data_type="q")
                        elif num_v is not None:
                            property_v, sim, value_matched_to, q_node_matched_to = self.match_context_with_type(
                                num_v, q_node, all_property_set, context_data_type="q")
                            property_v_2, sim_2, value_matched_to_2, q_node_matched_to_2 = self.process_context_string(
                                v, q_node,
                                all_property_set)
                            if sim_2 > sim:
                                property_v = property_v_2
                                sim = sim_2
                                value_matched_to = value_matched_to_2
                                q_node_matched_to = q_node_matched_to_2
                else:
                    property_v, sim, value_matched_to, q_node_matched_to = self.process_context_string(
                        v, q_node, all_property_set
                    )

                prop_list.append(property_v)
                sim_list.append(str(sim))
                value_for_debug = "/".join([property_v, q_node_matched_to, str(sim), value_matched_to])
                matched_to_list.append(value_for_debug)

        prop_str = "|".join(prop_list)
        sim_str = "|".join(sim_list)
        value_debug_str = "|".join(matched_to_list)
        return idx, value_debug_str, prop_str, sim_str

    def collector(self, idx, value_debug_str, prop_str, sim_str):
        """
        Purpose: collects the output of the mapper and appends to
                 final_property_list.
        :param sim_str: 
        :param prop_str:
        :param value_debug_str:
        :param idx:
        """
        self.final_property_similarity_list.append([idx, prop_str, sim_str, value_debug_str])

    def process_data_context(self):
        """
        Purpose: Processes the dataframe, reads each context_value separated by
        "|" and tries to match them to either
        date, string or quantity depending upon the structure of the context.
        """
        self.final_property_similarity_list = []
        cpus = cpu_count()
        pp = ParallelProcessor(cpus, mapper=lambda args: self.mapper(*args),
                               collector=self.collector, batch_size=100)
        pp.start()
        pp.map(zip(self.data.index.values.tolist(), self.data["kg_id"],
                   self.data["context"]))
        pp.task_done()
        pp.join()

        property_sim_df = pd.DataFrame(self.final_property_similarity_list,
                                       columns=["idx", "context_property",
                                                "context_similarity", "context_property_similarity_q_node"])
        property_sim_df.set_index("idx", drop=True, inplace=True)
        self.data = pd.merge(self.data, property_sim_df,
                             left_index=True, right_index=True)
        self.calculate_property_value()
        # Recalculate for the most important property for each q_node's that don't have that property.
        unique_positions = self.properties_with_score_metric['position'].unique().tolist()
        important_properties = []
        important_property_value = []
        min_sim_value = []
        for pos in unique_positions:
            temp_row = self.properties_with_score_metric[
                self.properties_with_score_metric['position'] == pos].sort_values(
                ['value'], ascending=False).head(1)
            important_properties.append(temp_row['property'].values.tolist()[0])
            important_property_value.append(temp_row['value'].values.tolist()[0])
            min_sim_value.append(temp_row['min_sim'].values.tolist()[0])
        for df_ind, q_node, properties_str, similarity_str, context_property_similarity_q_node_str in zip(
                self.data.index, self.data['kg_id'],
                self.data['context_property'], self.data['context_similarity'],
                self.data['context_property_similarity_q_node']):
            property_list = properties_str.split("|")
            similarity_list = similarity_str.split("|")
            context_property_similarity_q_node_list = context_property_similarity_q_node_str.split("|")
            is_change = False
            for p_l in range(len(property_list)):
                # If we have any property for that position
                if str(p_l + 1) in unique_positions:
                    ind = unique_positions.index(str(p_l + 1))
                    imp_prop = important_properties[ind]
                    if property_list[p_l] == imp_prop:
                        continue
                    elif property_list[p_l] == "":
                        # Need to check if this property is present for the particular q_node
                        context_value = self.context.get(q_node, None)
                        # Create a list of this values. In some cases the kg_id may not be present in the context_file.
                        if context_value:
                            # Initial Structuring
                            all_property_list = context_value.split("|")
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
                                weight_factor = 0.5
                                new_sim_val = round(weight_factor * float(min_sim_value[ind]), 4)
                                # Update with new_property
                                is_change = True
                                similarity_list[p_l] = str(new_sim_val) + "$$"
                                property_list[p_l] = imp_prop
                                context_property_similarity_q_node_list[p_l] = "/".join(
                                    [imp_prop, str(new_sim_val) + "$$"])

                    else:
                        # Another property is present at this location instead.
                        pass
            if q_node in self.equal_matched_properties:
                # temp references to the other possible properties that we can place.
                temp_list = self.equal_matched_properties.get(q_node, None)
                matched_property = temp_list[0]
                if matched_property in property_list:
                    temp_position = property_list.index(matched_property) + 1
                    current_property_value = self.properties_with_score_metric[
                        (self.properties_with_score_metric['property'] == matched_property) &
                        (self.properties_with_score_metric['position'] == str(temp_position))]['value'].values[0]
                    max_property = matched_property
                    max_property_value = current_property_value
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
                self.data.loc[df_ind, 'context_property'] = "|".join(property_list)
                self.data.loc[df_ind, 'context_similarity'] = "|".join(similarity_list)
                self.data.loc[df_ind, 'context_property_similarity_q_node'] = "|".join(
                    context_property_similarity_q_node_list)

        self.calculate_score()
