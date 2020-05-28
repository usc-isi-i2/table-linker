from abc import ABC, abstractmethod
class StringSimilarityModule(ABC):
    def __init__(self, **kwargs):
        # initialize the configs, like tf-idf need all data
        pass

    @abstractmethod
    def get_name(self) -> str:
        # return the module name and corresponding config
        # for example: "ngram:n=3"
        pass

    def similarity(self, str1: str, str2: str, threshold=0) -> float:
        # return the similarity score, if the similarity score is lower than threshold, return 0
        similarity = self._similarity(str1, str2)
        # if the score less than some threshold, return 0
        if threshold > similarity:
            return 0
        return similarity

    @abstractmethod
    def _similarity(self, str1: str, str2: str) -> float:
        # detail implementation of the method
        pass

class NgramSimilarity(StringSimilarityModule):
    def __init__(self, n):
        self.n = n

    def ngram_tokenizer(self, x):
        if len(x) < self.n:
            return [x]
        return [x[i:i + self.n] + "*" for i in range(len(x) - self.n + 1)]

    def get_name(self):
        return "ngram_similarity:n={}".format(self.n)

    def _similarity(self, str1: str, str2: str):
        str1_set = set(self.ngram_tokenizer(str1))
        str2_set = set(self.ngram_tokenizer(str2))
        similarity = len(str1_set.intersection(str2_set)) / len(str1_set.union(str2_set))
        return similarity


class EditDistanceSimilarity(StringSimilarityModule):
    def __init__(self):
        pass

    def _similarity(self, str1: str, str2: str):
        distance = self.edit_distance(str1, str2)
        similarity = distance / len(str1)
        return similarity

    def get_name(self):
        return "edit_distance_similarity"

    @staticmethod
    def edit_distance(word1, word2):
        """Dynamic programming solution"""
        m = len(word1)
        n = len(word2)
        table = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            table[i][0] = i
        for j in range(n + 1):
            table[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if word1[i - 1] == word2[j - 1]:
                    table[i][j] = table[i - 1][j - 1]
                else:
                    table[i][j] = 1 + min(table[i - 1][j], table[i][j - 1], table[i - 1][j - 1])
        return table[-1][-1]


