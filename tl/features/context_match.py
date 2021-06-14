import pandas as pd
import re
import rltk.similarity as similarity


class MatchContext(object):
    def __init__(self, input_path, context_path, args):
        self.final_data = pd.read_csv(input_path, dtype=object)
        self.data = pd.DataFrame()
        self.result_data = pd.DataFrame()
        self.context = pd.read_csv(context_path, sep='\t')
        self.output_column_name = args.get("output_column")
        self.similarity_string_threshold = args.pop("similarity_string_threshold")
        self.similarity_quantity_threshold = args.pop("similarity_quantity_threshold")
        self.debug = args.pop("debug")

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

    def match_context_with_type(self, context: str, all_property_list: list, context_data_type: str) -> (str, float):
        """
        Purpose: Matching the given context (of type numerical/quantity/string/date) to the property
        with highest similarity
        Args:
            context: Passed piece of context that needs to be matched.
            all_property_list: Contains the list of properties and their values for the given q_node.
            context_data_type = "q", "i", "d" represents that the property value is of type quantity, item and date
            year respectively.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        :param all_property_list:
        :param context:
        :param context_data_type:
        """
        property_list = [prop for prop in all_property_list if prop.lower().startswith(context_data_type.lower())]
        prop_val = ""
        max_sim = 0.0
        # We need to check if the quantity present in the check_for is also present in the properties result

        if context_data_type == 'q':
            check_for = float(context.replace('"', ''))
        elif context_data_type == 'd':
            check_for = self.remove_punctuation(context)
        else:
            check_for = self.preprocess(context)

        for prop in property_list:
            prop = prop.split(":")
            p_value = prop[0]
            if context_data_type == 'q':
                check_with_temp = p_value[1:]
                check_with = float(check_with_temp.replace('"', ''))
                value = self.quantity_score(check_with, check_for)
                if value >= self.similarity_quantity_threshold and value >= max_sim:
                    prop_val = prop[1]
                    max_sim = value
            else:
                check_with = self.remove_punctuation(p_value[1:])
                if context_data_type == 'd':
                    if check_for == check_with:
                        prop_val = prop[1]
                        max_sim = 1.0
                elif context_data_type == "i":
                    sim = similarity.hybrid.symmetric_monge_elkan_similarity(self.preprocess(check_with), check_for)
                    if sim >= self.similarity_string_threshold and sim >= max_sim:
                        if len(prop) > 1:  # Resolves error if the context does not have a property
                            prop_val = prop[1]
                            max_sim = sim

        max_sim = round(max_sim, 4)
        return prop_val, max_sim

    def preprocess(self, word: str) -> list:
        word = word.lower()
        preprocessed_word = self.remove_punctuation(word)
        preprocessed_word = preprocessed_word.split(" ")
        return preprocessed_word

    @staticmethod
    def remove_punctuation(input_string: str) -> str:
        result = re.sub(r'[^\w\s]', '', input_string)
        return result

    def process_context_string(self, s_context: str, all_property_list: list) -> (str, float):
        """
        Purpose: Before matching with the properties, necessary processing to handle cases where the comma-separated
        values match to the same properties.
        Args:
            s_context: Passed piece of context that needs to be matched.
            all_property_list: Contains the list of properties and their values for the given q_node.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        """
        if "," in s_context:
            # All the items separated by, should have same property. Finding properties for each item and
            # appending the property to temp
            temp = []
            sim_list = []
            sub_context_list = s_context.split(", ")
            for sub_s_context in sub_context_list:
                p, s = self.match_context_with_type(sub_s_context, all_property_list, context_data_type="i")
                temp.append(p)
                sim_list.append(s)
            # If all elements in temp have same value for property return that property
            if len(set(temp)) == 1:
                p_val = temp[0]
                sim = sum(sim_list) / len(sim_list)
            else:
                p_val = ""
                sim = 0.0
        else:
            p_val, sim = self.match_context_with_type(s_context, all_property_list, context_data_type="i")
        max_sim = round(sim, 4)
        return p_val, max_sim

    def calculate_score(self):
        """
        Purpose: Calculates the score by using the properties and the similarity with which they matched.
        """
        # Starting the score calculations
        # Part 1: Calculating Property values for each of the property that appear in the data file
        # Part 1 - a: Calculating the number of occurrences in each cell.
        columns = ["column", "row", "property", "position", "number_of_occurrences"]
        properties_set = pd.DataFrame(columns=columns)
        # counter is the index for the properties_set
        counter = 0
        for i, row in self.data.iterrows():
            value_of_row = row['row']
            value_of_column = row['column']
            value_of_property = row['context_properties']
            list_of_properties = value_of_property.split("|")
            # The positions will be denoted by the index. (Alternative: using dictionary instead - extra overhead)
            for j in range(len(list_of_properties)):
                position = j + 1
                if list_of_properties[j] != "":
                    if list_of_properties[j] not in properties_set.property.values:
                        # Add a new row
                        properties_set.loc[counter] = [value_of_column, value_of_row, list_of_properties[j],
                                                       str(position), "1"]
                        counter = counter + 1
                    else:
                        # Increment the count if same position, else add another row with the new position
                        ind = properties_set[(properties_set['property'] == list_of_properties[j]) & (
                                properties_set['row'] == value_of_row) & (
                                                     properties_set['position'] == str(position))].index.values
                        if len(ind) != 0:
                            old_count = properties_set['number_of_occurrences'].values[ind]
                            new_count = float(old_count[0]) + 1
                            properties_set.iloc[ind, properties_set.columns.get_loc('number_of_occurrences')] = str(
                                new_count)
                        else:
                            properties_set.loc[counter] = [value_of_column, value_of_row, list_of_properties[j],
                                                           str(position), "1"]
                            counter = counter + 1
                            # Part 1 - b - Calculating each individual property's value (also considers position)
        property_value_list = []
        for i, row in properties_set.iterrows():
            # Record the occurrences of a particular property.
            occurrences = row['number_of_occurrences']
            if float(occurrences) > 0:
                value = round(1 / float(occurrences), 4)
            else:
                value = 0
            property_value_list.append(value)
        properties_set['prop_val'] = property_value_list

        properties_l_df = properties_set['property']
        properties_list = properties_l_df.values.tolist()
        c_prop_list = list(set(properties_list))
        positions_list = properties_set['position']
        position_l = positions_list.values.tolist()
        c_pos_list = list(set(position_l))
        row_list = properties_set['row']
        row_l = row_list.values.tolist()
        c_row_list = list(set(row_l))
        properties_with_score_metric = pd.DataFrame(columns=['property', 'position', 'value'])
        counter = 0
        for prop in c_prop_list:
            for pos in c_pos_list:
                ind = properties_set[
                    (properties_set['property'] == prop) & (properties_set['position'] == pos)].index.values
                if len(ind) != 0:
                    property_cal = 0
                    for i in ind:
                        prop_val = properties_set['prop_val'].values[i]
                        property_cal = round((property_cal + float(prop_val)), 4)
                    f_prop_cal = round(property_cal / len(c_row_list), 4)
                    properties_with_score_metric.loc[counter] = [prop, pos, str(f_prop_cal)]
                    counter = counter + 1

        # Part 2 - Sum up the individual property values for a row (update:multiply with the similarity)
        final_scores_list = []
        for l_index, row in self.data.iterrows():
            properties_str = row['context_properties']
            properties_list = properties_str.split("|")
            sim_str = row['context_similarity']
            sim_list = sim_str.split("|")
            sum_prop = 0
            for i in range(len(properties_list)):
                if properties_list[i] != "":
                    ind = properties_with_score_metric[
                        (properties_with_score_metric['property'] == properties_list[i]) & (
                                properties_with_score_metric['position'] == str(i + 1))].index.values
                    value = properties_with_score_metric['value'].values[ind]

                    sum_prop = round(sum_prop + (float(value) * float(sim_list[i])), 4)
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

        self.result_data = self.result_data.reset_index(drop=True)

        if not self.debug:
            self.result_data = self.result_data.drop(columns=['context_properties', 'context_similarity'])
        return self.result_data

    def process_data_context(self):
        """
        Purpose: Processes the dataframe, reads each context_value separated by "|" and tries to match them to either
        date, string or quantity depending upon the structure of the context.
        """
        final_property_list = []
        final_similarity_list = []
        for i, row in self.data.iterrows():
            prop_list = []
            sim_list = []
            val = row['context']
            q_node = row['kg_id']
            # if there is empty context in the data file
            try:
                val_list = val.split("|")
            except AttributeError:
                val_list = ""
            # Get the context associated with the q_node from the context file
            context_value_index = self.context[self.context['qnode'] == q_node].index.values
            # In some of the files, there is no context for a particular q-node. Removed during context file generation.
            if len(context_value_index) != 0:
                context_value = self.context['context'].values[context_value_index[0]]
                all_property_list = context_value.split("|")
            else:
                final_property_list.append("")
                final_similarity_list.append("0.0")
                continue
            for v in val_list:
                # For quantity matching, we will give multiple tries to handle cases where numbers are separated with
                # or are in decimals
                new_v = v.replace('"', '')
                to_match_1 = new_v.replace(",", "")
                to_match_2 = to_match_1.replace(".", "0")
                num_v = None
                if " " in to_match_2:
                    split_v = to_match_1.split(" ")
                    for s in split_v:
                        new_s = s.replace(".", "0")
                        if new_s.isnumeric():
                            num_v = s

                if to_match_1.isnumeric() or to_match_2.isnumeric() or num_v is not None:
                    property_v, sim = self.match_context_with_type(to_match_1, all_property_list, context_data_type="d")
                    if property_v == "":
                        if to_match_1.isnumeric() or to_match_2.isnumeric():
                            property_v, sim = self.match_context_with_type(to_match_1, all_property_list,
                                                                           context_data_type="q")
                        elif num_v is not None:
                            property_v, sim = self.match_context_with_type(num_v, all_property_list,
                                                                           context_data_type="q")

                else:
                    property_v, sim = self.process_context_string(v, all_property_list)

                prop_list.append(property_v)
                sim_list.append(str(sim))

            prop_str = "|".join(prop_list)
            sim_str = "|".join(sim_list)
            final_property_list.append(prop_str)
            final_similarity_list.append(sim_str)

        self.data['context_properties'] = final_property_list
        self.data['context_similarity'] = final_similarity_list
        self.calculate_score()
