import pandas as pd
import re
import sys
import os
import rltk.similarity as sim

class Match(object):
    def __init__(self, input_path, context_path, args):
        self.final_data = pd.read_csv(input_path)
        self.data = pd.DataFrame()
        self.result_data = pd.DataFrame()
        self.context = pd.read_csv(context_path)
        self.output_column_name = args.get("output_column")
        self.threshold_1 = args.pop("similarity-string-threshold")
        self.threshold_2 = args.pop("similarity-quantity-threshold")
        self.debug = args.pop("debug")
        self.final_data = self.final_data.reindex(columns = self.final_data.columns.tolist() 
                                  + ['context_properties', 'monge_elkan_sim', self.output_column_name])

    def quantity_score(self, quantity_1, quantity_2):
        '''
        Purpose: Calculates the score between two quantities by taking the absolute difference between them and dividing by the max of both. 
        It is then subtracted from 1. 
        Returns: score
        '''
        if quantity_1 == 0.0 and quantity_2 == 0.0:
            return 1
        max_val = max(abs(quantity_1), abs(quantity_2))
        abs_diff = abs(quantity_1 - quantity_2)
        final_val = 1 - (abs_diff/max_val)
        return final_val

    def match_quantity(self, q_context, all_property_list, check = "q"):
        '''
        Purpose: Matching the given context (of type numerical/quantity) to the property with highest similarity
        Args:
            s_context: Passed piece of context that needs to be matched. 
            all_property_list: Contains the list of properties and their values for the given q_node.
            check = "i" represents that the property value is of type quantity.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        '''
        property_list = [prop for prop in all_property_list if prop.lower().startswith(check.lower())]
        prop_val = ""
        max_sim = 0.0
        #We need to check if the quantity present in the check_for is also present in the properties result.
        check_for = float(q_context.replace('"', ''))
        for prop in property_list:
            prop = prop.split(":")
            p_value = prop[0]
            check_with_temp = p_value[1:] #Removing the check portion
            check_with = float(check_with_temp.replace('"', ''))
            value = self.quantity_score(check_with, check_for)
            if value >= self.threshold_2 and value >= max_sim:
                prop_val = prop[1] 
                max_sim = value
        max_sim = round(max_sim, 4)
        return prop_val, max_sim

    def match_dates(self, d_context, all_property_list, check = "d"):
        '''
        Purpose: Matching the given context (of type date_year) to the property with highest similarity
        Args:
            s_context: Passed piece of context that needs to be matched. 
            all_property_list: Contains the list of properties and their values for the given q_node.
            check = "d" represents that the property value is of type date.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        '''
        property_list = [prop for prop in all_property_list if prop.lower().startswith(check.lower())]
        prop_val = ""
        max_sim = 0.0
        for prop in property_list:
            prop = prop.split(":")
            p_value = prop[0]
            check_with = self.remove_punctuation(p_value[1:])
            if self.remove_punctuation(d_context) == check_with:
                prop_val = prop[1] 
                max_sim = 1.0
        return prop_val, max_sim

    def preprocess(self, word):
        word = word.lower()
        preprocessed_word = self.remove_punctuation(word)
        preprocessed_word = preprocessed_word.split(" ")
        return preprocessed_word

    def remove_punctuation(self, input_string):
        result = re.sub(r'[^\w\s]', '', input_string)
        return result

    def match_string_item(self, s_context, all_property_list, check = "i"): 
        '''
        Purpose: Matching the given context (of type string) to the property with highest similarity
        Args:
            s_context: Passed piece of context that needs to be matched. 
            all_property_list: Contains the list of properties and their values for the given q_node.
            check = "i" represents that the property value is of type item.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        '''
        check_for = self.preprocess(s_context)
        property_list = [prop for prop in all_property_list if prop.lower().startswith(check.lower())]
        prop_val = ""
        max_sim = 0.0
        for prop in property_list:
            prop = prop.split(":")
            p_value = prop[0]
            check_with_temp = self.remove_punctuation(p_value[1:])
            check_with = self.preprocess(check_with_temp)
            sim = self.sym_monge_alken(check_with, check_for)
            if sim >= self.threshold_1 and sim >= max_sim:
                if len(prop) > 1:#Resolves error if the context does not have a property
                    prop_val = prop[1]
                    max_sim = sim
        return prop_val, max_sim

    def process_context_string(self, s_context, all_property_list):
        '''
        Purpose: Before matching with the properties, necessary processing to handle cases where the comma-separated values match to the same properties.
        Args:
            s_context: Passed piece of context that needs to be matched. 
            all_property_list: Contains the list of properties and their values for the given q_node.
        Returns: The Property matched and the similarity by which the property matched to the passed context.
        '''
        if "," in s_context:
            #All the items separated by , should have same property. Finding properties for each item and appending the property to temp
            temp = []
            sim_list = []
            sub_context_list = s_context.split(", ")
            for sub_s_context in sub_context_list:
                p, s = self.match_string_item(sub_s_context, all_property_list)
                temp.append(p)
                sim_list.append(s)
            #If all elements in temp have same value for property return that property
            if len(set(temp))==1:
                p_val = temp[0]
                sim = sum(sim_list)/len(sim_list)
            else:
                p_val = ""
                sim = 0.0
        else:
            p_val, sim = self.match_string_item(s_context, all_property_list)
        max_sim = round(sim, 4)
        return p_val, max_sim

    def sym_monge_alken(self,l1, l2):
        val = sim.hybrid.symmetric_monge_elkan_similarity(l1, l2, function=self.jaccard_index_similarity)
        return val
    
    def jaccard_index_similarity(self, l1, l2):
        set_l1 = set(l1)
        set_l2 = set(l2)
        val = sim.jaccard.jaccard_index_similarity(set_l1, set_l2)
        return val

    def calc_score(self):
        '''
        Purpose: Calculates the score by using the properties and the similarity with which they matched. 
        '''
        #Starting the score calculations
        #Part 1: Calculating Property values for each of the property that appear in the data file
        #Part 1 - a: Calaculating the number of occurences in each cell.
        columns = ["column", "row", "property", "position", "number_of_occurences"]
        properties_set = pd.DataFrame(columns = columns)
        #counter is the index for the properties_set
        counter = 0
        for i in range(len(self.data.index)):
            value_of_row = self.data['row'].values[i]
            value_of_column = self.data['column'].values[i]
            value_of_property = self.data['context_properties'].values[i]
            list_of_properties = value_of_property.split("|")
            value_of_sims = self.data['monge_elkan_sim'].values[i]
            list_of_sims = value_of_sims.split("|")
            #The positions will be denoted by the index. (Alternative: using dictionary instead - extra overhead)
            for j in range(len(list_of_properties)):
                position = j + 1
                if list_of_properties[j] != "":
                    if list_of_properties[j] not in properties_set.property.values:
                        #Add a new row
                        properties_set.loc[counter] = [value_of_column, value_of_row, list_of_properties[j], str(position), list_of_sims[j]]
                        counter = counter + 1
                    else : 
                        #Increment the count if same position, else add another row with the new position
                        ind = properties_set[(properties_set['property']==list_of_properties[j]) & (properties_set['row']==value_of_row) & (properties_set['position']==str(position))].index.values
                        if len(ind)!=0: 
                            other_row = properties_set['row'].values[ind]
                            old_count = properties_set['number_of_occurences'].values[ind]
                            new_count = float(old_count[0]) + float(list_of_sims[j])
                            properties_set.iloc[ind, properties_set.columns.get_loc('number_of_occurences')] = str(new_count)
                        else:
                            properties_set.loc[counter] = [value_of_column, value_of_row, list_of_properties[j], str(position), list_of_sims[j]]
                            counter = counter + 1    
        #Part 1 - b - Calculating each individual property's value (also considers position)                
        properties_set = properties_set.reindex(columns = properties_set.columns.tolist() 
                                          + ['prop_val'])
        for i in range(len(properties_set.index)):
            occ = properties_set['number_of_occurences'].values[i]
            if float(occ) > 0:
                value = round(1/float(occ), 4)
            else:
                value = 0
            properties_set.iloc[i, properties_set.columns.get_loc('prop_val')] = str(value)
            
        properties_l_df = properties_set['property']
        properties_list = properties_l_df.values.tolist()
        c_prop_list = list(set(properties_list))
        positions_list = properties_set['position']
        position_l = positions_list.values.tolist()
        c_pos_list = list(set(position_l))
        row_list = properties_set['row']
        row_l = row_list.values.tolist()
        c_row_list = list(set(row_l))
        properties_with_score_metric = pd.DataFrame(columns = ['property', 'position', 'value'])
        counter = 0
        for prop in c_prop_list:
            for pos in c_pos_list:
                ind = properties_set[(properties_set['property']==prop) & (properties_set['position']==pos)].index.values
                if len(ind)!=0:
                    property_cal = 0
                    for i in ind:
                        prop_val = properties_set['prop_val'].values[i]
                        property_cal = round((property_cal + float(prop_val)), 4)
                    f_prop_cal = round(property_cal/len(c_row_list), 4)
                    properties_with_score_metric.loc[counter] = [prop, pos, str(f_prop_cal)]
                    counter = counter + 1

        #Part 2 - Sum up the individual property values for a row (update:mutiply with the similarity)
        for l in range(len(self.data.index)):
            properties_str = self.data['context_properties'].values[l]
            properties_list = properties_str.split("|")
            sim_str = self.data['monge_elkan_sim'].values[l]
            sim_list = sim_str.split("|")
            sum_prop = 0
            for i in range(len(properties_list)):
                if properties_list[i] != "":
                    ind = properties_with_score_metric[(properties_with_score_metric['property']==properties_list[i])& (properties_with_score_metric['position']==str(i+1))].index.values
                    value = properties_with_score_metric['value'].values[ind]
                    
                    sum_prop = round(sum_prop + (float(value)*float(sim_list[i])), 4)
                if sum_prop > 1:
                    sum_prop = 1
                self.data.iloc[l, self.data.columns.get_loc(self.output_column_name)] = sum_prop

    def process_data_by_column(self):
        '''
        Purpose: Groups the dataframe by column, sends for property matching and score calculation and joins the grouped data.
        Returns: A Dataframe with the given column name containing the score with which the context matched to properties. 
        '''
        grouped_object = self.final_data.groupby(['column'])
        for cell, group in grouped_object:
            self.data = group.reset_index(drop=True)
            self.process_data_context()
            self.result_data = pd.concat([self.result_data, self.data])
            self.result_data = self.result_data.drop_duplicates()            
        self.result_data = self.result_data.reset_index(drop=True)
        if self.debug==False:
            self.result_data = self.result_data.drop(columns=['context_properties', 'monge_elkan_sim'])
        self.result_data.to_csv(sys.stdout, index=False)

    def process_data_context(self):
        '''
        Purpose: Processes the dataframe, reads each context_value separated by "|" and tries to match them to either date, string or quantity depending upon the structure of the context.
        '''
        for i in range(len(self.data.index)):
            prop_list = []
            sim_list = []
            val = self.data['context'].values[i]
            q_node = self.data['kg_id'].values[i] 
            #if there is empty context in the data file
            try:
                val_list = val.split("|")
            except:
                val_list = ""
            #Get the context associated with the q_node from the context file
            context_value_index = self.context[self.context['qnode']==q_node].index.values
            if isinstance(q_node, float) and str(q_node) == 'nan':
                #No q_node in the file
                sim_str = "0.0"
                prop_str = ""
                self.data.iloc[i, self.data.columns.get_loc('monge_elkan_sim')] = sim_str
                self.data.iloc[i, self.data.columns.get_loc('context_properties')] = prop_str
                continue
            #In some of the files, there is no context for a particular q-node. Removed during context file generation.
            if len(context_value_index) != 0:
                context_value = self.context['context'].values[context_value_index[0]]
                all_property_list = context_value.split("|")
            else:
                sim_str = "0.0"
                prop_str = ""
                self.data.iloc[i, self.data.columns.get_loc('monge_elkan_sim')] = sim_str
                self.data.iloc[i, self.data.columns.get_loc('context_properties')] = prop_str
                continue
            for v in val_list:
                #For quantity matching, we will give multiple tries to handle cases where numbers are separated with , or are in decimals
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
                    property_v, sim = self.match_dates(to_match_1, all_property_list)
                    if property_v == "":
                        if to_match_1.isnumeric() or to_match_2.isnumeric():
                            property_v, sim = self.match_quantity(to_match_1, all_property_list)
                        elif num_v is not None:
                            property_v, sim = self.match_quantity(num_v, all_property_list)
                else:
                    property_v, sim = self.process_context_string(v, all_property_list)  
                prop_list.append(property_v)
                sim_list.append(str(sim))
            prop_str = "|".join(prop_list)
            sim_str = "|".join(sim_list)
            self.data.iloc[i, self.data.columns.get_loc('context_properties')] = prop_str
            self.data.iloc[i, self.data.columns.get_loc('monge_elkan_sim')] = sim_str
        self.calc_score()
