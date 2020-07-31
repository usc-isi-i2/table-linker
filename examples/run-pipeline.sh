tl run-pipeline \
--tag gt-embed --gpu-resources 3 \
--parallel-count 4 --score-column embed-score \
--ground-truth-directory iswc_challenge_data/round4/gt \
--ground-truth-file-pattern {}.csv \
--pipeline '--url http://kg2018a.isi.edu:9200 --index wiki_labels_aliases_1 \
clean -c label \
/ get-exact-matches -c label_clean \
/ normalize-scores -c retrieval_score \
/ get-phrase-matches -c label_clean -n 10 --filter "retrieval_score_normalized > 0.9" \
/ ground-truth-labeler -f iswc_challenge_data/round4/gt/{}.csv / \
add-text-embedding-feature \
--column-vector-strategy ground-truth --centroid-sampling-amount 0 --run-TSNE false \
--sparql-query-endpoint https://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql \
--distance-function euclidean \
--output-column-name embed-score \
/ tee --output iswc_challenge_data/round4/output_v2_index_mix_match_n_10_eculidean/{}_exact_match_euclidean_gt_0.csv' \
iswc_challenge_data/round4/canonical/v*.csv

# explain:
# run pipeline on all csv files starting with v in iswc_challenge_data/round4/canonical folder.
# FOr each file, run the pipeline as specified: 
# input -> clean -> get exact matches and phrase matches -> normalize the retrieval score \
#       -> apply ground truth -> add text embedding feature -> \
#       -> output the file here to iswc_challenge_data/round4/output_v2_index_mix_match_n_10_eculidean 
# During running those pipelines, allow up to 4 pipelines running together in the same time, 
# only run on gpu No.3.