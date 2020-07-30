

## Introduction
Currently, the most up-to-date index is `wiki_labels_aliases_3`, which contains the pre-computed pagerank of all wikidata nodes and the latest aliases / labels.

### Generating features
To start, run following script, it will do:
1. fetech the possible candidates with 3 existing search method (`exact-match`, `phrase-match` and `fuzzy-match`).
2. Normalize the retrieval score and drop duplicate candidates from different match methods.
3. Apply ground turth labeler to add ground truth column.
4. Add text embedding vector scores with `ground-truth` mode and then normalize this score.
5. Add text embedding vctor scores with `pre computed page rank` mode and then normalize this score.
6. Compute the extra information score.
7. Compute the string similairty between the input string and candidate labels.

Then, the output file will contains different features which can be used / analysis for the future.
For details explaination and introduction to each function, please refer to the main page's readme file.
```
tl --url http://kg2018a.isi.edu:9200 --index wiki_labels_aliases_3 \
canonicalize --csv -c 2 --add-other-information input/russia_chieves.csv \
/ clean -c label \
/ get-exact-matches -i -c label_clean \
/ get-phrase-matches -c label_clean -n 30 \
/ get-fuzzy-matches -c label_clean -n 10 \
/ normalize-scores -c retrieval_score \
/ ground-truth-labeler -f gt/chief_subset_col2_canonicalized.csv \
/ drop-duplicate -c kg_id --score-column retrieval_score_normalized \
/ add-text-embedding-feature \
--embedding-model bert-base-nli-cls-token \
--column-vector-strategy ground-truth \
--save-embedding-feature --centroid-sampling-amount 0 \
--sparql-query-endpoint https://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql \
--distance-function cosine \
--use-default-file true \
--output-column-name gt_embed_score \
--ignore-empty-sentences \
/ normalize-scores -c gt_embed_score \
/ add-text-embedding-feature \
--column-vector-strategy page-rank-precomputed --output-column-name pagerank-precomputed \
/ normalize-scores -c pagerank-precomputed \
/ check-extra-information \
--sparql-query-endpoint https://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql \
/ string-similarity -i --method levenshtein jaro_winkler needleman soundex metaphone nysiis cosine:tokenizer=ngram:tokenizer_n=3 jaccard:tokenizer=ngram:tokenizer_n=3 hybrid_jaccard:tokenizer=word monge_elkan:tokenizer=word symmetric_monge_elkan:tokenizer=word tfidf:tokenizer=word > new_es_chief3.csv
```

## Visualization
After we get the csv file output from previous step, we can do some visulization analysis with 2 way:
### 1. color the cells base on the scores
```
tl add-color new_es_chief3.csv --all-columns --ground-truth-score-column gt_embed_score_normalized --sort-by-ground-truth --output new_es_chief3.xlsx
```
This command will generate a xlsx file which contains the colors on the score columns:
- the top 5 score cell of each candidate on each method will be colored. The higher the score, the deeper the color will be.
- The Q nodes will become a link and you can click it to redirect to wikidata webpage as references.
- The candidates of each mention will be divided by a thick black line for better searching.

### 2. plot the bar figures
```
tl plot-score-figure new_es_chief3.csv -k 1 2 5 --all-columns --output new_es_chief3 --output-score-table
```
This command will produce 3 parts of output:
- A PNG image file, this figure contains a horizontal bar chart, separate by each method, each method contains couple of bars, each bar corresponding to the accuracy base on different k values 
-- here k means if the ground truth in the top k score candidates, we will treat as correct. For example. if k = 3, we will consider as find the correct answer found if the score of the ground turth score is in top 3 scores,). 
-- The blue score on the bar indicates the `score : normalized score`.  Where the left `score` is the accuracy correspond to the count of all mentions, right `normalized` is the normalized score calculated by the count of correct divided by the `count of all mentions that contains ground-truth as candidates`.
-- There is also a vertical red line which indicates the maximum possible score. This scores indicate the most ideal score we can achieve (find all correct answers from those candidates).
- A html web page, this is an interactive page that allow users to to server opeartions.
-- By clicking the color blocks on the bottom of the page, users can choose which score column to display. It enable users to choose displaying some good features or some intersting features only.
-- The vertical bar on the right part of the page can be moved, shortened or extended, to adjust the display range of displaying mentioned. 
-- It is also possible get the detail values of each bar if moved cursor over the bars.
-- There are some other feature tools on the right top side of the page for fine tuning.

## Future TODO
Currently there is no final decision make functions, which means now we can only produce those candidates and features but no proper way to find the correct answer among those candidates.