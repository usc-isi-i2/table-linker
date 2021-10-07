from abc import ABC, abstractmethod
from functools import partial
import rltk.similarity as sim


def word_tokenizer(s):
    return s.split(' ')


def ngram_tokenizer(s, n, keep_start_and_end=False):
    n = int(n)
    keep_start_and_end = bool(keep_start_and_end)

    if keep_start_and_end:
        s = '_{}_'.format(s.lower())
    if len(s) < n:
        return [s]
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def get_tokenizer(name, **kwargs):
    tokenizer = {
        'ngram': ngram_tokenizer,
        'word': word_tokenizer
    }[name]
    return partial(tokenizer, **kwargs)


"""
How to add new stringSimilarityModule classes:
1. Please ensure the new class name is "*Similarity", so that the system will automatically find them
2. Please follow the abstract class defined below and use the superclass of this abstract class to define new similarity module
3. Basically, only the function `_similarity` is necessary to be implemented.
4. if your similarity calculation required the full text for indexing or other help functions, 
   please include this in __init__ function. You can refer to "TfidfSimilarity" class as an example.  
"""


class StringSimilarityModule(ABC):
    def __init__(self, tl_args, **method_args):
        # tl_args is necessary if operation specification (like case sensitive) is needed
        # kwargs is necessary if tokenization (need all data in df) is needed
        # set tl args
        self._ignore_case = tl_args.get('ignore_case', False)

        # set method args
        tokenizer_kwargs = {}
        for k, v in method_args.items():
            setattr(self, '_{}'.format(k), v)
            if k.startswith('tokenizer_'):
                tokenizer_kwargs[k[len('tokenizer_'):]] = v
        self._arg_str = ','.join(['{}={}'.format(k, v) for k, v in method_args.items()])

        if hasattr(self, '_tokenizer'):
            self._tokenize = get_tokenizer(self._tokenizer, **tokenizer_kwargs)

    def get_name(self) -> str:
        # return the module name and corresponding config
        # for example: "ngram:n=3"
        return '{}({})'.format(self.__class__.__name__, self._arg_str)

    def similarity(self, str1: str, str2: str, threshold=0) -> float:
        # return the similarity score, if the similarity score is lower than threshold, return 0
        if self._ignore_case:
            str1 = str1.lower()
            str2 = str2.lower()
        if hasattr(self, '_tokenize'):
            str1 = self._tokenize(str1)
            str2 = self._tokenize(str2)
        # the threshold here may only be effective if it is implemented by the underlying function
        similarity = self._similarity(str1, str2, threshold)
        # force the score to be 0 if it is less than the threshold
        if threshold > similarity:
            return 0.0
        return similarity

    @abstractmethod
    def _similarity(self, str1: str, str2: str, threshold: float) -> float:
        # detail implementation of the method
        raise NotImplementedError


class LevenshteinSimilarity(StringSimilarityModule):
    # levenshtein

    def _similarity(self, str1: str, str2: str, threshold: float):
        return sim.levenshtein_similarity(str1, str2, lower_bound=threshold)


class JaroWinklerSimilarity(StringSimilarityModule):
    # jaro_winkler

    def __init__(self, tl_args, threshold=0.7, scaling_factor=0.1, prefix_len=4):
        threshold = float(threshold)
        scaling_factor = float(scaling_factor)
        prefix_len = int(prefix_len)
        super().__init__(tl_args,
                         threshold=threshold, scaling_factor=scaling_factor, prefix_len=prefix_len)

    def _similarity(self, str1: str, str2: str, threshold: float):
        return sim.jaro_winkler_similarity(str1, str2,
                                           threshold=self._threshold, scaling_factor=self._scaling_factor,
                                           prefix_len=self._prefix_len)


class NeedlemanSimilarity(StringSimilarityModule):
    # needleman

    def __init__(self, tl_args, match=2, mismatch=-1, gap=-0.5):
        match = float(match)
        mismatch = float(mismatch)
        gap = float(gap)
        super().__init__(tl_args,
                         match=match, mismatch=mismatch, gap=gap)

    def _similarity(self, str1: str, str2: str, threshold: float):
        return sim.needleman_wunsch_similarity(str1, str2,
                                               match=self._match, mismatch=self._mismatch, gap=self._gap)


class SoundexSimilarity(StringSimilarityModule):
    # soundex

    def _similarity(self, str1: str, str2: str, threshold: float):
        return sim.soundex_similarity(str1, str2)


class MetaphoneSimilarity(StringSimilarityModule):
    # metaphone

    def _similarity(self, str1: str, str2: str, threshold: float):
        return sim.metaphone_similarity(str1, str2)


class NysiisSimilarity(StringSimilarityModule):
    # nysiis

    def _similarity(self, str1: str, str2: str, threshold: float):
        return sim.nysiis_similarity(str1, str2)


class CosineSimilarity(StringSimilarityModule):
    # cosine:tokenizer=word

    def __init__(self, tl_args, **kwargs):
        super().__init__(tl_args, **kwargs)

    def _similarity(self, str1: list, str2: list, threshold: float):
        return sim.string_cosine_similarity(str1, str2)


class JaccardSimilarity(StringSimilarityModule):
    # jaccard:tokenizer=word

    def __init__(self, tl_args, **kwargs):
        super().__init__(tl_args, **kwargs)

    def _similarity(self, str1: list, str2: list, threshold: float):
        return sim.jaccard_index_similarity(set(str1), set(str2))


class HybridJaccardSimilarity(StringSimilarityModule):
    # hybrid_jaccard:tokenizer=word

    def __init__(self, tl_args, **kwargs):
        super().__init__(tl_args, **kwargs)

    def _similarity(self, str1: list, str2: list, threshold: float):
        return sim.hybrid_jaccard_similarity(set(str1), set(str2), lower_bound=threshold)


class MongeElkanSimilarity(StringSimilarityModule):
    # monge_elkan:tokenizer=word

    def __init__(self, tl_args, **kwargs):
        super().__init__(tl_args, **kwargs)

    def _similarity(self, str1: list, str2: list, threshold: float):
        return sim.monge_elkan_similarity(str1, str2, lower_bound=threshold)


class SymmetricMongeElkanSimilarity(StringSimilarityModule):
    # symmetric_monge_elkan:tokenizer=word

    @property
    def support_threshold(self):
        return True

    def __init__(self, tl_args, **kwargs):
        super().__init__(tl_args, **kwargs)

    def _similarity(self, str1: list, str2: list, threshold: float):
        return sim.symmetric_monge_elkan_similarity(str1, str2, lower_bound=threshold)


class TfidfSimilarity(StringSimilarityModule):
    # tfidf:tokenizer=word

    def __init__(self, tl_args, **kwargs):
        super().__init__(tl_args, **kwargs)

        self._tfidf = sim.TF_IDF()
        df = tl_args['df']
        col_name1 = tl_args['target_label_column_name']
        col_name2 = tl_args['candidate_label_column_name']
        fake_id = 0
        for _, v in df[col_name1].items():
            if self._ignore_case:
                v = v.lower()
            self._tfidf.add_document(str(fake_id), self._tokenize(v))
            fake_id += 1
        for _, v in df[col_name2].items():
            for vv in v:
                if self._ignore_case:
                    vv = vv.lower()
                self._tfidf.add_document(str(fake_id), self._tokenize(vv))
                fake_id += 1
        self._tfidf.pre_compute()

    def _similarity(self, str1: list, str2: list, threshold: float):
        # because doc_id is not available
        # here tf will be re-computed
        tf_x = sim.compute_tf(str1)
        tfidf_x = {k: v * self._tfidf.idf[k] for k, v in tf_x.items()}
        tf_y = sim.compute_tf(str2)
        tfidf_y = {k: v * self._tfidf.idf[k] for k, v in tf_y.items()}
        return sim.tf_idf_cosine_similarity(tfidf_x, tfidf_y)
