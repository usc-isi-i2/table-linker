import pandas as pd
import re
import sys
import os

class match(object):
    def __init__(self, input_path, context_path, args):
        #print(args)
        self.final_data = pd.read_csv(input_path)
        self.data = pd.DataFrame()
        self.result_data = pd.DataFrame()
        self.context = pd.read_csv(context_path)
        self.output_column_name = args.get("output_column")
        self.threshold_1 = args.pop("sim_string")
        self.threshold_2 = args.pop("sim_quantity")
        self.debug = args.pop("debug")
        self.final_data = self.final_data.reindex(columns = self.final_data.columns.tolist() 
                                  + ['context_properties', 'monge_elkan_sim', self.output_column_name])
    def preprocess(self, sent):
        sent = sent.lower()
        new_sent = self.remove_punctuation(sent)
        new_sent = self.tokenize(new_sent)
        return new_sent

    def tokenize(self, sent):
        sent = sent.split(" ")
        return sent

    def remove_punctuation(self, sent):
        res = re.sub(r'[^\w\s]', '', sent)
        return res

    def quantity_matching(self, context_target, context_try):
        if context_target == 0.0 and context_try == 0.0:
            return 1
        max_val = max(abs(context_target), abs(context_try))
        abs_diff = abs(context_target - context_try)
        final_val = 1 - (abs_diff/max_val)
        return final_val

    def remove_comma(self, string):
        string = string.replace(',', '')
        return string

    def matching_with_quantity(self, context_to_do, all_props, check = "q"):
        res = [idx for idx in all_props if idx.lower().startswith(check.lower())]
        prop_val = "NaN"
        sim = 0.0
        res2 = "NaN"
        for x in res:
            x = x.split(":")
            n = x[0]
            check_with_t = n[1:]
            check_with = float(check_with_t.replace('"', ''))
            check_for = float(context_to_do.replace('"', ''))
            value = self.quantity_matching(check_with, check_for)
            if value >= self.threshold_2 and value >= sim:
                prop_val = x[1] 
                sim = value
                res2 = check_with
        #print(prop_val, sim, value)
        sim = round(sim, 4)
        return prop_val, sim

    def matching_with_date(self, context_to_do, all_props, check = "d"):
        res = [idx for idx in all_props if idx.lower().startswith(check.lower())]
        prop_val = "NaN"
        sim = 0.0
        for x in res:
            x = x.split(":")
            n = x[0]
            check_with = self.remove_punctuation(n[1:])
            if self.remove_punctuation(context_to_do) == check_with:
                prop_val = x[1] 
                sim = 1.0
        return prop_val, sim

    def same_elements(self, lst):
        ele = lst[0]
        chk = True
        for item in lst:
            if ele != item:
                chk = False
                break;         
        return chk

    def matching_with_item(self, context_to_do, all_props, check = "i"): 
        p_context_to_do = self.preprocess(context_to_do)
        res = [idx for idx in all_props if idx.lower().startswith(check.lower())]
        prop_val = "NaN"
        max = 0.0
        for x in res:
            x = x.split(":")
            n = x[0]
            check_with = self.remove_punctuation(n[1:])
            p_check_with = self.preprocess(check_with)
            sim = self.symmetric_monge_elkan(p_check_with, p_context_to_do)
            if sim >= self.threshold_1 and sim >= max:
                if len(x) > 1:#Resolves error if the context does not have a property
                    prop_val = x[1]
                    max = sim
        return prop_val, max

    def Convert(string):
        li = list(string.split(" "))
        return li

    def for_a_string(self, context_to_do, all_props):
        if "," in context_to_do:
            #All the items separated by , should have same property. Finding properties for each item and appending the property to temp
            temp = []
            sim_l = []
            list_c_to_do = context_to_do.split(", ")
            for l in list_c_to_do:
                x, s = self.matching_with_item(l, all_props)
                temp.append(x)
                sim_l.append(s)
            #If all elements in temp have same value for property return that property
            if self.same_elements(temp):
                p_val = temp[0]
                sim = sum(sim_l)/len(sim_l)
            else:
                p_val = "NaN"
                sim = 0.0
        else:
            p_val, sim = self.matching_with_item(context_to_do, all_props)
        sim = round(sim, 4)
        return p_val, sim

    def jaccard_index_similarity(self, list1, list2):
        set_l1 = set(list1)
        set_l2 = set(list2)
        if len(set_l1) == 0 or len(set_l2) == 0:
            return 0
        intersection = len(set_l1 & set_l2)
        union = (len(set_l1) + len(set_l2) - intersection)
        return float(intersection) / (union)

    def monge_elkan_similarity(self, list1, list2):
        if len(list1) == 0:
            return 0.0
        final_score = 0
        for i in list1:
            max_val =  float('-inf')
            for j in list2:
                max_val = max(max_val, self.jaccard_index_similarity(i, j))
                
            final_score += max_val
        return float(final_score) / float(len(list1))

    def symmetric_monge_elkan(self, list1, list2):
        s1 = self.monge_elkan_similarity(list1, list2)
        s2 = self.monge_elkan_similarity(list2, list1)
        return (s1 + s2) / 2

    #symmetric_monge_elkan_similarity(['fighting'], ['fighting', 'game'])
    def jaccard(self, list1, list2):
        intersection = len(list(set(list1).intersection(list2)))
        union = (len(list1) + len(list2)) - intersection
        return float(intersection) / union

    def calc_score(self):
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
            print("This is the value", value_of_column, value_of_property, i)
            list_of_properties = value_of_property.split("|")
            value_of_sims = self.data['monge_elkan_sim'].values[i]
            list_of_sims = value_of_sims.split("|")
            #The positions will be denoted by the index. (Alternative: using dictionary instead - extra overhead)
            for j in range(len(list_of_properties)):
                position = j + 1
                if list_of_properties[j] != "NaN":
                    if list_of_properties[j] not in properties_set.property.values:
                        #Add a new row
                        properties_set.loc[counter] = [value_of_column, value_of_row, list_of_properties[j], str(position), list_of_sims[j]]
                        counter = counter + 1
                        #print("counter", counter)
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
            sum_p = 0
            for i in range(len(properties_list)):
                if properties_list[i] != "NaN":
                    ind = properties_with_score_metric[(properties_with_score_metric['property']==properties_list[i])& (properties_with_score_metric['position']==str(i+1))].index.values
                    value = properties_with_score_metric['value'].values[ind]
                    
                    sum_p = round(sum_p + (float(value)*float(sim_list[i])), 4)
                if sum_p > 1:
                    sum_p = 1
                self.data.iloc[l, self.data.columns.get_loc(self.output_column_name)] = sum_p

    def get_unique_numbers(self, numbers):
        unique = []

        for number in numbers:
            if number in unique:
                continue
            else:
                unique.append(number)
        return unique

    def divide_by_column(self):
        #print(self.final_data.head())
        to_check = self.final_data['column'].values.tolist()
        x = self.final_data.columns.tolist()
        self.result_data = pd.DataFrame(columns = x)
        unique_d = self.get_unique_numbers(to_check)
        for i in unique_d:
            self.data = self.final_data[self.final_data['column']==i]
            self.data = self.data.reset_index(drop=True)
            self.initialize()
            self.result_data = pd.concat([self.result_data, self.data])
            self.result_data = self.result_data.drop_duplicates()
        self.result_data = self.result_data.reset_index(drop=True)
        if self.debug==False:
            self.result_data = self.result_data.drop(columns=['context_properties', 'monge_elkan_sim'])
        self.result_data.to_csv(sys.stdout, index=False)

    def initialize(self):
        for i in range(len(self.data.index)):
            prop_list = []
            sim_list = []
            val = self.data['context'].values[i]
            q_node = self.data['kg_id'].values[i] 
            #if there is empty context in the data file
            try:
                val_list = val.split("|")
            except:
                val_list = "NaN"
            pro = self.context[self.context['qnode']==q_node].index.values
            if isinstance(q_node, float) and str(q_node) == 'nan':
                #No q_node in the file
                sim_str = "0.0"
                prop_str = "NaN"
                self.data.iloc[i, self.data.columns.get_loc('monge_elkan_sim')] = sim_str
                self.data.iloc[i, self.data.columns.get_loc('context_properties')] = prop_str
                continue
            #In some of the files, there is no context for a particular q-node. Removed during context file generation.
            if len(pro) != 0:
               
                int_prop = self.context['context'].values[pro[0]]
                all_props = int_prop.split("|")
            else:
                sim_str = "0.0"
                prop_str = "NaN"
                self.data.iloc[i, self.data.columns.get_loc('monge_elkan_sim')] = sim_str
                self.data.iloc[i, self.data.columns.get_loc('context_properties')] = prop_str
                continue
            for v in val_list:
                try_x = v.replace('"', '')
                try_1 = self.remove_comma(try_x)
                try_2 = try_1.replace(".", "0")
                num_v = None
                if " " in try_2:
                    split_v = try_1.split(" ")
                    for s in split_v:
                        s_1 = s.replace(".", "0")
                        if s_1.isnumeric():
                            num_v = s
                if try_1.isnumeric() or try_2.isnumeric() or num_v is not None:
                    property_v, sim = self.matching_with_date(try_1, all_props)
                    if property_v == "NaN":
                        if try_1.isnumeric() or try_2.isnumeric():
                            property_v, sim = self.matching_with_quantity(try_1, all_props)
                        elif num_v is not None:
                            property_v, sim = self.matching_with_quantity(num_v, all_props)
                else:
                    property_v, sim = self.for_a_string(v, all_props)  
                prop_list.append(property_v)
                sim_list.append(str(sim))
            prop_str = "|".join(prop_list)
            sim_str = "|".join(sim_list)
            self.data.iloc[i, self.data.columns.get_loc('context_properties')] = prop_str
            self.data.iloc[i, self.data.columns.get_loc('monge_elkan_sim')] = sim_str
        self.calc_score()
        
