


# [« Home](https://github.com/usc-isi-i2/table-linker) / Command Line Interface

Table-Linker: this is an entity linkage tool which links the given string to wikidata Q nodes. 
This document describes the command-line interface for the <code>Table Linker (tl)</code> system.


## Installation Instructions

Run the following commands in order in a terminal,
```
git clone https://github.com/usc-isi-i2/table-linker
cd table-linker

python3 -m venv tl_env
source tl_env/bin/activate
pip install -r requirements.txt

pip install -e .
```
If python3 is not installed, find out what version of python 3 is installed and use that instead

## Pipelines
The `tl` CLI works by pushing CSV data through a series of commands, starting with a single input on `stdin` and ending with a single output on `stdout`. This pipeline feature allows construction of pipelines for linking table cells to a knowledge graph (KG).

### `Usage:  tl [OPTIONS] COMMAND [ / COMMAND]* `

**Table of Contents:**
- [`add-color`](#command_add-color)<sup>*</sup>: Add some color on the specified score columns for better visualization.
- [`add-text-embedding-feature`](#command_add-text-embedding-feature)<sup>*</sup>: computes text embedding vectors of the candidates and similarity to rank candidates.
- [`canonicalize`](#command_canonicalize)<sup>*</sup>: translate an input CSV or TSV file to [canonical form](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.wn7c3l1ngi5z)
- [`check-extra-information`](#command_check-extra-information)<sup>*</sup> : Check if the given extra information exists in the given kg node and corresponding wikipedia page (if exists).
- [`clean`](#command_clean)<sup>*</sup> : clean the values to be linked to the KG.
- [`combine-linearly`](#command_combine-linearly)<sup>*</sup>: linearly combines two or more columns with scores for candidate knowledge graph objects for each input cell value.
- [`drop-by-score`](#command_drop-by-score)<sup>*</sup>: Remove rows of each candidates according to specified score column from higher to lower.
- [`drop-duplicate`](#command_drop-duplicate)<sup>*</sup>: Remove duplicate rows of each candidates according to specified column and keep the one with higher score on specified column.
- [`get-exact-matches`](#command_get-exact-matches)<sup>*</sup>: retrieves the identifiers of KG entities whose label or aliases match the input values exactly.
- [`get-kg-links`](#command_get-kg-links): outputs the top `k` candidates from a sorted list as linked knowledge graph objects for an input cell in [KG Links](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.ysslih9i88l5) format.
- [`ground-truth-labeler`](#command_ground-truth-labeler)<sup>*</sup>: compares each candidate for the input cells with the ground truth value for that cell and adds an evaluation label
- [`join`](#command_join): outputs the top `k` candidates from a sorted list as linked knowledge graph objects for an input cell in [Output](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.6rlemqh56vyi) format
- [`merge-columns`](#command_merge-columns): merges values from two or more columns and outputs the concatenated value in the output column
- [`metrics`](#command_metrics): Calculate the F1-score on the candidates tables. Only works on the dataset after ran with  `ground-truth-labeler`.
- [`normalize-scores`](#command_normalize-scores)<sup>*</sup>: normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval method for all input cells.
- [`plot-score-figure`](#command_plot-score-figure)<sup>*</sup>: visulize the score of the input data with 2 different kind of bar charts.
- [`run-pipeline`](#command_run-pipeline)<sup>*</sup>: runs a pipeline on a collection of files to produce a single CSV file with the results for all the files.
- [`string-similarity`](#command_string-similarity)<sup>*</sup>: compares the cell values in two input columns and outputs a similarity score for each pair of participating strings 
- [`tee`](#command_tee)<sup>*</sup>: saves the input to disk and echoes the input to the standard output without modification.


**Note: only the commands marked with <sup>*</sup> are currently implemented**

**Options:**
- `-e, --examples` -- Print some examples and exit
- `-h, --help` -- Print this help message and exit
- `-v, --version` -- Print the version info and exit
- `--url {url}`:  URL of the Elasticsearch server containing the items in the KG
- `--index {index}`: name of the Elasticsearch index 
- `-U {user id}`: the user id for authenticating to the ElasticSearch index
- `-P {password}`: the password for authenticating to the ElasticSearch index

## Common Options
These are options that can appear in different commands. We list them here so that options with the same meaning use the same character.

- `-c`: specifies columns to operate on. Columns can be specified using column headers or indices; indices are zero-based; multiple columns are comma-separated.
- `-o`: specifies the output column of a command.
- `-p`: specifies names of properties in the KG
- `--url {url}`:  URL of the ElasticSearch index containing the items in the KG.
- `-U {user id}`: the user id for authenticating to the ElasticSearch index.
- `-P {password}`: the password for authenticating to the ElasticSearch index.
- `-i`: case insensitive operation.
- `-n {number}`: controls the number of items processed, e.g., the number of candidates retrieved during candidate generation.
- `-f {path}`: specifies auxiliary file path as input to commands

## Error handling
In case of an error in any of the commands in the `tl` pipeline, the responsible command will print out 
the error details, an error code and, the pipeline will halt.

**Error details**

Error details will contain the following information
- `name of the command`: the command where this error occurred
- `error message`: a stacktrace of the error message describing the exception
- `error code`: a number corresponding to the error. Default is `-1`

**Example**
```bash
Command: get-exact-matches
Error Message:
 Traceback (most recent call last):
  File "get_candidates.py", line 7, in <module>
    raise HTTPUnAuthorizedError(msg)
  HTTP 403: Unauthorized attempt to connect to Elasticsearch
Error Code: 403
```

## Commands On Raw Input Files

<a name="command_canonicalize" />

### [`canonicalize`](#command_canonicalize)` [OPTIONS]`
translate an input CSV or TSV file to [canonical form](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.wn7c3l1ngi5z)

**Options:**
- `-c {a,b,...}`: the columns in the input file to be linked to KG entities. Multiple columns are specified as a comma separated string. 
- `-o a`: specifies the name of a new column to be added. Default output column name is `label`
- `--tsv`:  the delimiter of the input file is TAB.
- `--csv`: the delimiter of the input file is comma.
- `--add-other-information`: append information from other columns as an extra column of output canonical file.

**Examples:**
   ```bash
   # Build a canonical file to link the 'people' and 'country' columns in the input file
   $ tl canonicalize -c people,country < input.csv > canonical-input.csv
   $ cat input.csv | tl canonicalize -c people,country > canonical-input.csv

   # Same, but using column as index to specify the country column
   $ tl canonicalize -c people,3 < input.csv > canonical-input.csv
   ```

**File Example:**
```bash
# Consider the following input file, 
$ cat countries.csv

country        capital_city phone_code
Hungary        Buda’pest    +49
Czech Republic Prague       +420
United Kingdom London!      +44

# canonicalize the input file and process columns country and capital_city
$ tl canonicalize -c capital_city --csv countries.csv > countries_canonical.csv
$ cat countries_canonical.csv

column row label
1      0   Buda’pest
1      1   Prague
1      2   London!

$ cat chief_subset.tsv

col0  col1  col2
Russia  Pres. Vladimir Vladimirovich PUTIN
Russia  Premier Dmitriy Anatolyevich MEDVEDEV
Russia  First Dep. Premier  Anton Germanovich SILUANOV
Russia  Dep. Premier  Maksim Alekseyevich AKIMOV
Russia  Dep. Premier  Yuriy Ivanovich BORISOV
Russia  Dep. Premier  Konstatin Anatolyevich CHUYCHENKO
Russia  Dep. Premier  Tatyana Alekseyevna GOLIKOVA

# canonicalize the input file and process col2 with adding extra information
$ tl canonicalize -c col2  --add-other-information chief_subset.tsv > organizations_subset_col0_canonicalized.csv

# note that we get an extra column here, which is the information from the input file, combined by `|`
$ cat organizations_subset_col0_canonicalized.csv

column,row,label,||other_information||
2,0,Vladimir Vladimirovich PUTIN,Russia|Pres.
2,1,Dmitriy Anatolyevich MEDVEDEV,Russia|Premier
2,2,Anton Germanovich SILUANOV,Russia|First Dep. Premier
2,3,Maksim Alekseyevich AKIMOV,Russia|Dep. Premier
2,4,Yuriy Ivanovich BORISOV,Russia|Dep. Premier
2,5,Konstatin Anatolyevich CHUYCHENKO,Russia|Dep. Premier
2,6,Tatyana Alekseyevna GOLIKOVA,Russia|Dep. Premier
```

### Implementation
Assign zero based indices to the input columns and corresponding rows. 
The columns are indexed from left to right and rows from top to bottom. The first row is column header, the first data row is
assigned index 0.

## Commands On Canonical Files
[Canonical Cell files](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.wn7c3l1ngi5z) contain one row per cell to be linked. 

<a name="command_clean" />

### [`clean`](#command_clean)` [OPTIONS]`
The `clean` command cleans the cell values in a column, creating a new column with the clean values.
 The `clean` command performs two types of cleaning:

- Invokes the [ftfy](https://pypi.org/project/ftfy/) library to fix broken unicode characters and html tags.
- Removes or replaces symbols by space.

The `clean` command produces a file in the [Canonical Cells](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.wn7c3l1ngi5z) format

**Options:**
- `-c a`: the column to be cleaned.
- `-o a`: the name of the column where cleaned column values are stored. If not provided, the name of the new column is the name of the input column with the suffix `_clean`.
- `--symbols {string}`: a string containing the set of characters to be removed: default is “!@#$%^&*()+={}[]:;’\”/<>”
- `--replace-by-space {yes/no}`: when `yes` (default) all instances of the symbols are replaced by a space. In case of removal of multiple consecutive characters, they’ll be replaced by a single space. The value `no` causes the symbols to be deleted.
- `--keep-original {yes/no}` : when `yes`, the output column will contain the original value and the clean value will be appended, separated by `|`. Default is `no`
 
**Examples:**
```bash
   # Clean the values in column 'label' using the default settings, 
   # creating a column 'label_clean' with the clean values.
   $ tl clean -c label < canonical-input.csv

   # Remove all types of parenthesis from the label.
   $ tl clean -c label -o clean --symbols "(){}[]" --replace-by-space no < canonical-input.csv
    
    # Clean the values in column 'label', output column 'clean_labels', keeping the original values
    $ tl clean -c label -o clean_labels --keep-original yes canonical_input.csv
```

**File Example:**
```bash
# Consider the canonical file, countries_canonical.csv
$ cat countries_canonical.csv
    
column row label
1      0   Buda’pest
1      1   Prague
1      2   London!

# clean the column label and delete the default characters
$ tl clean -c label -o clean_labels --replace-by-space no countries_canonical.csv

column row label          clean_labels
1      0   Buda’pest      Budapest
1      1   Prague         Prague
1      2   London!        London
```


## Candidate Generation Commands
Candidate Generation commands use external indices or APIs to retrieve candidate links for cells in a column. `tl` supports several strategies for generating candidates.  

All candidate generation commands take a column in a [Canonical Cells](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.wn7c3l1ngi5z) file as input and
 produce a set of KG identifiers for each row in a canonical file and candidates are stored one per row. A `method` column records the name of the strategy that produced a candidate.

When a cell contains a |-separated string (e.g., `Pedro|Peter`, the string is split by `|` and candidates are fetched for each of the resulting values.

Candidate Generation commands output a file in [Candidates](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.j9cdkygbzzq7) format


<a name="command_get-exact-matches" />

### [`get-exact-matches`](#command_get-exact-matches)` [OPTIONS]`
This command retrieves the identifiers of KG entities whose label or aliases match the input values exactly.

**Options:**
- `-c a`: the column used for retrieving candidates.
- `-p {a,b,c}`:  a comma separated names of properties in the KG to search for exact match query: default is `labels,aliases`. 
- `-i`: case insensitive retrieval, default is case sensitive.
- `-n {number}`: maximum number of candidates to retrieve, default is 50.

This command will add the column `kg_labels` to record the labels and aliases of the candidate knowledge graph object. In case of missing
labels or aliases, an empty string "" is recorded. A `|` separated string represents multiple labels and aliases. 
The values to be added in the  column `kg_labels` are retrieved from the Elasticsearch index based on the `-p` option as 
defined above.

The string `exact-match` is recorded in the column `method` to indicate the source of the candidates.

The Elasticsearch queries return a score which is recorded in the column `retrieval_score`. The scores are stored in 
the field `_score` in the retrieved Elasticsearch objects.

The identifiers for the candidate knowledge graph objects returned by Elasticsearch are recorded in the column `kg_id`. The identifiers
 are stored in the field `_id` in the retrieved Elasticsearch objects.

**Examples:**

```bash
   # generate candidates for the cells in the column 'label_clean'
   $ tl --url http://blah.com --index kg_labels_1 -Ujohn -Ppwd  get-exact-matches -c label_clean  < canonical-input.csv

   # clean the column 'label' and then generate candidates for the resulting column 'label_clean' with case insensitive matching
   $ tl --url http://blah.com --index kg_labels_1 -Ujohn -Ppwd clean -c label / get-exact-matches -c label_clean -i  < canonical-input.csv

```

**File Example:**

```
# generate candidates for the canonical file, countries_canonical.csv
$ tl --url http://blah.com --index kg_labels_1 -Ujohn -Ppwd  get-exact-matches -c clean_labels  < countries_canonical.csv > countries_candidates.csv
$ cat countries_candidates.csv

column row label     clean_labels kg_id     kg_labels                             method      retrieval_score
1      0   Buda’pest Budapest     Q1781     Budapest|Buda Pest|Buda-Pest|Buda     exact-match 15.43
1      0   Buda’pest Budapest     Q16467392 Budapest (chanson)                    exact-match 14.07
1      0   Buda’pest Budapest     Q55420238 Budapest|Budapest, a song             exact-match 13.33
1      1   Prague    Prague       Q1085     Prague|Praha|Praha|Hlavní město Praha exact-match 15.39
1      1   Prague    Prague       Q1953283  Prague, Oklahoma                      exact-match 14.44
1      1   Prague    Prague       Q2084234  Prague, Nebraska                      exact-match 13.99
1      1   Prague    Prague       Q5969542  Prague                                exact-match 14.88
1      2   London!   London       Q84       London|London, UK|London, England     exact-match 13.88
1      2   London!   London       Q92561    London ON                             exact-match 12.32
```

### Implementation

The `get-exact-matches` command will be implemented using an ElasticSearch index built using an Edges file in KGTK format.
Two ElasticSearch term queries are defined, one for exact match retrieval and one for case-insensitive exact match retrieval.

-   Exact match query: In Elasticsearch language, this will be a terms query. Terms query allows search for multiple terms. This query retrieves documents which have the exact search term as label or aliases.
-   Exact match lowercase query: Same as Exact match query but with lowercase search terms.

<a name="command_get-phrase-matches" />

### [`get-phrase-matches`](#command_get-phrase-matches)` [OPTIONS]`
retrieves the identifiers of KG entities base on phrase match queries.

**Options:**
- `-c a`: the column used for retrieving candidates.
- `-p {a,b,c}`:  a comma separated names of properties in the KG to search for phrase match query with boost for each property.
 Boost is specified as a number appended to the property name with a caret(^). default is `labels^2,aliases`. 
- `-n {number}`: maximum number of candidates to retrieve, default is 50.
- `--filter {str}`: a string indicate the filtering requirement.

This command will add the column `kg_labels` to record the labels and aliases of the candidate knowledge graph object. In case of missing
labels or aliases, an empty string "" is recorded. A `|` separated string represents multiple labels and aliases. 
The values to be added in the  column `kg_labels` are retrieved from the Elasticsearch index based on the `-p` option as 
defined above.

The string `phrase-match` is recorded in the column `method` to indicate the source of the candidates.

The Elasticsearch queries return a score which is recorded in the column `retrieval_score`. The scores are stored in 
the field `_score` in the retrieved Elasticsearch objects.

The identifiers for the candidate knowledge graph objects returned by Elasticsearch are recorded in the column `kg_id`. The identifiers
 are stored in the field `_id` in the retrieved Elasticsearch objects.
 
The `filter` arg is optional, if given, it will execute the operation specified in the string and remove the rows which not fit the requirement. If after removing, no candidates for this `(column, row)` pair left, it will append the phrase match results generated, otherwise nothing will be appended.
 **Examples:**

```bash
   # generate candidates for the cells in the column 'label_clean'
   $ tl --url http://blah.com --index kg_labels_1 -Ujohn -Ppwd  get-phrase-matches -c label_clean  < canonical-input.csv

   # generate candidates for the resulting column 'label_clean' with property alias boosted to 1.5 and fetch 20 candidates per query
   $ tl --url http://blah.com --index kg_labels_1 -Ujohn -Ppwd get-phrase-matches -c label_clean -p "alias^1.5"  -n 20 < canonical-input.csv

   # generate candidates for the cells in the column 'label_clean' with exact-match method and normalized the score
   # then filter the results of exact-match with score less than 0.9 and add candaites found from phrase-match
   $ tl --url http://blah.com --index kg_labels_1 -Ujohn -Ppwd clean -c label \
     / get-exact-matches -c label_clean / normalize-scores -c retrieval_score \
     / get-phrase-matches -c label_clean -n 5 --filter "retrieval_score_normalized > 0.9"
```

**File Example:**

```
# generate candidates for the canonical file, countries_canonical.csv
$ tl --url http://blah.com --index kg_labels_1 -Ujohn -Ppwd  get-phrase-matches -c clean_labels  < countries_canonical.csv > countries_candidates.csv
$ cat countries_candidates.csv

column  row  label      clean_labels  kg_id      kg_labels                                        method        retrieval_score
1       0    Buda’pest  Budapest      Q603551    Budapest|Budapest Georgia                        phrase-match  42.405098
1       0    Buda’pest  Budapest      Q20571386  .budapest|dot budapest                           phrase-match  42.375305
1       1    Prague     Prague        Q2084234   Prague|Prague  Nebraska                          phrase-match  37.18586
1       1    Prague     Prague        Q1953283   Prague|Prague Oklahoma                           phrase-match  36.9689
1       2    London!    London        Q261303    London|London                                    phrase-match  33.492584
1       2    London!    London        Q23939248  London|Greater London|London region              phrase-match  33.094616
0       0    Hungary    Hungary       Q5943060   Hungary|European Parliament election in Hungary  phrase-match  33.324196
0       0    Hungary    Hungary       Q40662208  CCC Hungary|Cru Hungary                          phrase-match  30.940805
```

### Implementation
Details to follow

## Adding Features Commands

Add-Feature commands add one or more features for the candidate knowledge graph objects for the input cells.
All Add-Feature commands take a column in a [Candidate](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.j9cdkygbzzq7) 
or a [Feature](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.meysv8c8z2mt) file 
and output a [Feature](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.meysv8c8z2mt) file. 

<a name="command_add-text-embedding-feature" />

### [`add-text-embedding-feature`](#command_add-text-embedding-feature)` [OPTIONS]`

The `add-text-embedding-feature` command computes text embedding vectors of the candidates and similarity to rank candidates. 
The basic idea is to compute a vector for a column in a table and then rank the candidates for each cell by measuring 
similarity between each candidate vector and the column vector.

**Options:**
- `--sparql-query-endpoint`: The sparql query endpoint the sysetm should query to. Default is  offical wikidata query endpoint https://query.wikidata.org/sparql. Note: The official wikidata query endpoint has frequency and timeout limit.
- `--output-column-name`: The output scoring column name. If not provided, the name of the embedding model will be used.
- `--generate-projector-file`: If given, the function will generate the files needed to run the Google Project visualization.
###### Following options are wrapped from kgtk, please refer to [here](https://github.com/usc-isi-i2/kgtk/blob/feature/embedding/kgtk/cli/text_embedding_README.md "here") for details.
- `--column-vector-strategy {string}`: The centroid choosing method.
- `--embedding-model {string}`: The pre-fitted models used for generating the vectors.
- `--distance-function {string}`: The distance measurement function to used for scoring.
- `--centroid-sampling-amount {int}`: The number of cells used to estimate the vector for a column.
- `--label-properties {string}`: The names of the properties(P nodes) for `label` properties. If pass with `None`, this part will not be used. Default is `label` property.
- `--description-properties list{string}`: The names of the properties(P nodes) for `description` properties. If pass with `None`, this part will not be used. Default is `description` property.
- `--isa-properties list{string}`: The names of the properties(P nodes) for `isa` properties. If pass with `None`, this part will not be used. Default is `P31`.
- `--has-properties list{string}`: The names of the properties(P nodes) for `has` properties. If pass with `None`, this part will not be used. Default is all P nodes except `P31`.
- `--property-value list{string}`: For those edges found in `has` properties, the nodes specified here will display with  corresponding edge(property) values. instead of edge name.
- `--dimensional-reduction {string}`: Whether to run dimensional reduction algorithm or not after the embedding vectors is generated.
- `--dimension {int}`: The specific target dimensions required to reduce to. Default is `2`.
- `--ignore-empty-sentences`: If send with this flag, the nodes (usually they are some recently added nodes) which does not existed in the given wikidata query endpoint but found from elastic search index will be ignored and removed.
- `--use-default-file {bool}`: If set to `False`, the system will use all properties found from the query endpoint. If set to `True`, the system will use a special-config file which remove some useless properties like `ID` and check some more details property values like `gender`.

**Detail explainations:**
 - column-vector-strategy
Currently 3 modes of strategies are supported: `ground-truth`, `page-rank` and `page-rank-precomputed`.
 -- `ground-truth`: Only works after running with `ground-truth-labeler`. It will compute the  score base on the distance to the centroid point.
 -- `page-rank`: Based on the given candidate nodes, it will compute a page-rank score. The idea is adapt from this [paper](http://mgrani.github.io/media/papers/16zwi.sei.gra-DoSeR-A-Knowledge.pdf).
 -- `page-rank-precomputed`: This page rank is different from previous one. The page rank here used the page rank calculation method from [graph-tool](https://graph-tool.skewed.de/static/doc/centrality.html?highlight=pagerank#graph_tool.centrality.pagerank). All nodes existed in wikidata will be considered and computed, then stored in the index and we will retrieve those node's pagerank when needed.


**Examples:**
```bash
# run text embedding command to add an extra column `embed-score` with ground-truth strategy and use all nodes to calculate centroid
$ tl add-text-embedding-feature input_file.csv \
  --column-vector-strategy ground-truth \
  --centroid-sampling-amount 0 \
  --output-column-name embed-score

# run text embedding command to add an extra column `embed-score` with ground-truth strategy and use up to 5 nodes to calculate centroid, the generated sentence only contains label and description information. Also, apply TSNE on the embedding vectors after generated. Also, the corresponding detail vectors file will be saved to `vectors.tsv`
$ tl add-text-embedding-feature input_file.csv \
  --embedding-model bert-base-nli-mean-tokens \
  --column-vector-strategy ground-truth \
  --centroid-sampling-amount 5 \
  --isa-properties None \
  --has-properties None \
  --run-TSNE true \
  --generate-projector-file vectors.tsv

```

**File Example:**
```
    column  row                                          label  ...                                    GT_kg_label evaluation_label embed-score
0        0    2                        Trigeminal nerve nuclei  ...                        Trigeminal nerve nuclei                1    0.925744
1        0    3                       Trigeminal motor nucleus  ...                       Trigeminal motor nucleus                1    0.099415
2        0    4                          Substantia innominata  ...                          Substantia innominata                1    0.070117
3        0    6                                    Rhombic lip  ...                                    Rhombic lip                1    1.456694
4        0    7                                 Rhinencephalon  ...                                 Rhinencephalon                1    0.471636
5        0    9  Principal sensory nucleus of trigeminal nerve  ...  Principal sensory nucleus of trigeminal nerve                1    1.936707
6        0   12                     Nucleus basalis of Meynert  ...                     Nucleus basalis of Meynert                1    0.130171
7        0   14      Mesencephalic nucleus of trigeminal nerve  ...      Mesencephalic nucleus of trigeminal nerve                1    1.746346
8        0   17                         Diagonal band of Broca  ...                         Diagonal band of Broca                1    0.520857
9        0    1                                 Tuber cinereum  ...                                 tuber cinereum                1    0.116646
10       0    1                                 Tuber cinereum  ...                                 tuber cinereum               -1    0.192494
11       0    1                                 Tuber cinereum  ...                                 tuber cinereum               -1    0.028620
```

#### Implementation
This command mainly wrap from kgtk's text-embedding functions.
please refer to kgtk's readme page [here](https://github.com/usc-isi-i2/kgtk/blob/feature/embedding/kgtk/cli/text_embedding_README.md "here") for details.

<a name="command_check-extra-information" />

### [`check-extra-information`](#command_check-extra-information)` [OPTIONS]`

The `check-extra-information` add a feature column by checking if any extra information from the original file get hitted and return a score base on the hitted information amount. 

The program will check each node's property values and corresponding wikipedia page if exists. If any labels found there are same as the provieded extra information treat as hitted, otherwise not hitted. Usually there would be multiple columns for each input original file, we treat each coulmn as one part, the score is `count(hitted_part)/ count(all_parts)`. Maximum score is 1 for hit all extra information provided.

**Options:**
- `--sparql-query-endpoint {string}`: The sparql query endpoint the sysetm should query to. Default is  offical wikidata query endpoint https://query.wikidata.org/sparql. Note: The official wikidata query endpoint has frequency and timeout limit.
- `--extra-information-file {string}`: If the input canonical format file do not contains the column `||other_information||` genreated by command `canonicalize`, this extra information file path is necessary. Otherwise it is optional.
- `--score-column {string}`: The name of the column used for the scoring to determine the prediction results.

**Examples:**
```bash
# add the extra-information feature column with external extra information file
$ tl check-extra-information input_file.csv \
  --extra-information-file extra_info.csv \
  --output-column-name extra_information_score > output_file.csv
```

**File Example:**
```bash
# add the extra-information feature column
$ tl check-extra-information input_file.csv \
  --output-column-name extra_information_score > output_file.csv
  column  row  label  ||other_information||  label_clean  ...  GT_kg_id  GT_kg_label evaluation_label  gt_embed_score  extra_information_score

2  0 Vladimir Vladimirovich PUTIN Russia|Pres. Vladimir Vladimirovich PUTIN  ... Q7747 Vladimir Putin  1  1.297309  0.5

2  0 Vladimir Vladimirovich PUTIN Russia|Pres. Vladimir Vladimirovich PUTIN  ... Q7747 Vladimir Putin -1  1.290919  0.0

2  0 Vladimir Vladimirovich PUTIN Russia|Pres. Vladimir Vladimirovich PUTIN  ... Q7747 Vladimir Putin -1  0.651267  0.0

2  0 Vladimir Vladimirovich PUTIN Russia|Pres. Vladimir Vladimirovich PUTIN  ... Q7747 Vladimir Putin -1  0.815978  0.0

2  0 Vladimir Vladimirovich PUTIN Russia|Pres. Vladimir Vladimirovich PUTIN  ... Q7747 Vladimir Putin -1  0.778838  0.0

...  ...  ...  ...  ...  ...  ... ...  ...  ... ...  ...

2 40  Vasiliy Alekseyevich NEBENZYA  Russia|Permanent Representative to the UN, New...  Vasiliy Alekseyevich NEBENZYA  ...  Q1000053  Vasily Nebenzya -1  0.950004  0.0

2 40  Vasiliy Alekseyevich NEBENZYA  Russia|Permanent Representative to the UN, New...  Vasiliy Alekseyevich NEBENZYA  ...  Q1000053  Vasily Nebenzya -1  0.763486  0.0

2 40  Vasiliy Alekseyevich NEBENZYA  Russia|Permanent Representative to the UN, New...  Vasiliy Alekseyevich NEBENZYA  ...  Q1000053  Vasily Nebenzya -1  1.219794  0.5

2 40  Vasiliy Alekseyevich NEBENZYA  Russia|Permanent Representative to the UN, New...  Vasiliy Alekseyevich NEBENZYA  ...  Q1000053  Vasily Nebenzya -1  1.225877  0.0

2 40  Vasiliy Alekseyevich NEBENZYA  Russia|Permanent Representative to the UN, New...  Vasiliy Alekseyevich NEBENZYA  ...  Q1000053  Vasily Nebenzya -1  1.185123  0.5
$ cat output_file.csv

```

#### Implementation
Wikidata part: achieved with the wikidata sparql query to get all properties of the Q nodes.
Wikipedia part: achieved with the python pacakge `wikipedia-api`

<a name="command_string-similarity" />

### [`string-similarity`](#command_string-similarity)` [OPTIONS]`
The `string-similarity` command compares the cell values in two input columns and outputs a similarity score for
 each pair of participating strings in the output column. 
 
The `string-similarity` command supports the following tokenizer, some of the string similarity may require to specify one of them during calculating.
- `word`: This is a simple tokenizer, it will split the input string by white space `/s`.
- `ngram`: This is a ngram tokenizer, it will generate ngram candidates of each input string, user can specify the value of n. For example, the jaccard similarity with ngram tokenizer and n=3: `jaccard:tokenizer=ngram:tokenizer_n=3`.

The `string-similarity` command supports the following string similarity algorithms, all of those similarity functions are implemented from [RLTK]([https://github.com/usc-isi-i2/rltk](https://github.com/usc-isi-i2/rltk)). These similarity methods are ordered in alphabet.

- [cosine](https://sites.temple.edu/tudsc/2017/03/30/measuring-similarity-between-texts-in-python/#:~:text=The%20cosine%20similarity%20is%20the,the%20similarity%20between%20two%20documents.
) (`tokenizer` needed)
The similarity between the two strings is the cosine of the angle between these two vectors representation.
- [hybrid_jaccard]()  (`tokenizer` needed)
The jaccard similarity hybird with `jaro_winkler_similarity`.
- [jaccard](https://en.wikipedia.org/wiki/Jaccard_index) (`tokenizer` needed)
The Jaccard Index Similarity is then computed as intersection(set1, set2) / union(set1, set2).
- [jaro_winkler](https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance#Jaro%E2%80%93Winkler_Similarity) (no parameters needed)
Jaro Winkler is a string edit distance designed for short strings. In Jaro Winkler, substitution of 2 close characters is considered less important than the substitution of 2 characters that are far from each other. 
The similarity is computed as `1 - Jaro-Winkler distance`. The value is between `[0.0, 1.0]`.
- [levenshtein](https://en.wikipedia.org/wiki/Levenshtein_distance) (no parameters needed)
The levenshtein distance between two words in the minimum number single-character edits needed to change one word into the other. Normalized levenshtein is computed as the levenshtein distance divided by the length of the longest string.
 The similarity is computed as `1 - normalized distance`.  The value is between `[0.0, 1.0]`.
 - [metaphone](https://en.wikipedia.org/wiki/Metaphone) (no parameters needed)
Metaphone fundamentally improves on the Soundex algorithm by using information about variations and inconsistencies in English spelling and pronunciation to produce a more accurate encoding, which does a better job of matching words and names which sound similar. As with Soundex, similar-sounding words should share the same keys. Metaphone is available as a built-in operator in a number of systems.
- [monge_elkan]() (`tokenizer` needed)
monge elkan score implement similarity.
- [needleman](https://en.wikipedia.org/wiki/Needleman%E2%80%93Wunsch_algorithm#Similarity_matrix
) (no parameters needed)
This Needleman Wunsch Similarity is computed as needlman_wunsch_score over maximum score of s1 and s2.
- [nysiis](https://en.wikipedia.org/wiki/New_York_State_Identification_and_Intelligence_System) (no parameters needed)
New York State Immunization Information System (NYSIIS) Phonetic Code is a phonetic algorithm. 1 for same NYSIIS code, 0 for different.
- [soundex](https://en.wikipedia.org/wiki/Soundex) (no parameters needed)
soundex score implement similarity.
- [symmetric_monge_elkan]() (`tokenizer` needed)
symmetric monge elkan score implement similarity.
- [tfidf](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) (`tokenizer` needed)
tf-idf score implement similarity.



In future, more string similarity algorithms will be supported
 
**Options:**
- `-c {a,b}`: input columns containing the cells to be compared. The two columns are represented as a comma separated string. Default value is set as `a=label_clean` and `b=kg_labels`. Column `b` could have multiple labels splitted by `|` while column `a` could have only 1 label.
- `--method list{string}`: the string similarity method to use, please refer to the introduction parts above for details. Mutiple method values is accepted here. You can send multiple methods in one time.
- `-i`: case insensitive comparison. Default is case sensitive

The string similarity scores are added to a output columns. 
If the specific columns (not `["label_clean", "kg_labels"]`)is given, the compared column names will be added to the column name whose name will be in the format `<col_1>\_<col_2>\_\<algorithm>`.
Otherwise the column name will only be in the format `<algorithm>`.
 

**Examples:**

```bash
# compute similarity score for the columns 'clean_labels' and 'kg_label', use Normalized Levenshtein, case sensitive comparison
$ tl string-similarity --method levenshtein < countries_candidates.csv

# compute similarity score for the columns 'doc_labels' and 'doc_aliases', use Jaccard similarity based on ngram=3 tokenizer, tf-idf score with word tokenizer and Needleman similarity, case insensitive comparison
$ tl string-similarity -c doc_labels,doc_aliases  --method jaccard:tokenizer=ngram:tokenizer_n=3 tfidf:tokenizer=word needleman countries_candidates.csv
```

**File Example:**
```
# compute string similarity between the columns 'clean_labels' and 'kg_labels', using case sensitive Normalized Levenshtein 
# for the file countries_candidates.csv, exclude columns 'label','method' and 'retrieval_score' while printing
$ tl string-similarity -c clean_labels,kg_labels --lev < countries_candidates.csv > countries_ss_features.csv \
&& mlr --opprint cut -f label,method,retrieval_score -x countries_ss_features.csv

column row clean_labels kg_id     kg_labels                             clean_labels_kg_labels_LevenshteinSimilarity()
1      0   Budapest     Q1781     Budapest|Buda Pest|Buda-Pest|Buda     1
1      0   Budapest     Q16467392 Budapest (chanson)                    0.44
1      0   Budapest     Q55420238 Budapest|Budapest, a song             1
1      1   Prague       Q1085     Prague|Praha|Praha|Hlavní město Praha 1
1      1   Prague       Q1953283  Prague, Oklahoma                      0.375
1      1   Prague       Q2084234  Prague, Nebraska                      0.375
1      1   Prague       Q5969542  Prague                                1
1      2   London       Q84       London|London, UK|London, England     1
1      2   London       Q92561    London ON                             0.66
```

#### Implementation
For any input cell value, s and  a candidate c, String similarity outputs a score computed as follows,

<code> stringSimilarity(s, c) := max(similarityFunction(s, l)) ∀ l ∈ { labels(c) } </code> 


<a name="command_merge-columns" />

### [`merge-columns`](#command_merge-columns)` [OPTIONS]`
The `merge-columns` command merges values from two or more columns and outputs the concatenated value in the output column. 
 
 **Options:**
- `-c {a,b,...}`: a comma separated string with columns names, values of which are to be concatenated together.
- `-o a`: the output column name where the concatenated values will be stored. Multiple values are represented by a `|` separated string. 
- `--remove-duplicates {yes/no}`: remove duplicates or not. Default is `yes` 
 
 
 **Examples:**
```
# merge the columns 'doc_label' and 'doc_aliases' in the doc_details.csv and store the output in the column 'doc_label_aliases' and keep duplicates
$ tl merge-columns -c doc_label,doc_aliases -o doc_label_aliases --remove-duplicates no doc_details.csv

# same as above but remove duplicates
$ tl merge-columns -c doc_label,doc_aliases -o doc_label_aliases --remove-duplicates yes < doc_details.csv
``` 

**File Example:**
```
$ tl merge-columns -c kg_label,kg_aliases -o kg_label_aliases --remove-duplicates yes < countries_candidates_v2.csv

column row label     clean_labels kg_id     kg_label           kg_aliases                 kg_label_aliases
1      0   Buda’pest Budapest     Q1781     Budapest           Buda Pest|Buda-Pest|Buda   Budapest|Buda Pest|Buda-Pest|Buda
1      0   Buda’pest Budapest     Q16467392 Budapest (chanson) ""                         Budapest (chanson)
1      0   Buda’pest Budapest     Q55420238 Budapest           Budapest, a song           Budapest|Budapest, a song
1      1   Prague    Prague       Q1085     Prague|Praha       Praha|Hlavní město Praha   Prague|Praha|Hlavní město Praha
1      1   Prague    Prague       Q1953283  Prague, Oklahoma   ""                         Prague, Oklahoma
1      1   Prague    Prague       Q2084234  Prague, Nebraska   ""                         Prague, Nebraska
1      1   Prague    Prague       Q5969542  Prague             ""                         Prague
1      2   London!   London       Q84       London             London, UK|London, England London|London, UK|London, England
1      2   London!   London       Q92561    London ON          ""                         London ON

```

<a name="command_normalize-scores" />

### [`normalize-scores`](#command_normalize-scores)` [OPTIONS]`
The `normalize-score` command normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval method for all input cells in a column.
This command will find the maximum retrieval score for candidates generated by a retrieval method, 
and then divide the individual candidate retrieval scores by the maximum retrieval score for that method for each input column.

Note that the column containing the retrieval method names is `method`, added by the [get-exact-matches](#command_get-exact-matches) command.

**Options:**
- `-c a`: column name which has the retrieval scores. Default is `retrieval_score`
- `-o a`: the output column name where the normalized scores will be stored. Default is input column name appended with the suffix `_normalized`
- `-w|--weights`: a comma separated string of the format `<retrieval_method_1:<weight_1>, <retrieval_method_2:<weight_2>,...>`
 specifying the weights for each retrieval method. By default, all retrieval method weights are set to 1.0

**Examples:**
```bash
# compute normalized scores with default options
$ tl normalize-scores < countries_candidates.csv > countries_candidates_normalized.csv

# compute normalized scores for the column 'es_score', output in the column 'normalized_es_scores' with specified weights
$ tl normalize-scores -c es_score -o normalized_es_scores -w 'es_method_1:0.4,es_method_2:0.92' countries_candidates.csv
```

**File Example:**
```bash
# compute normalized score for the column 'retrieval_score', output in the column 'normalized_retrieval_scores' with specified weights
$ tl normalize-scores -c retrieval_score -o normalized_retrieval_scores -w 'phrase-match:0.5' < countries_candidates.csv | mlr --opprint cut -f kg_label,kg_aliases -x

column row label     clean_labels kg_id     method       retrieval_score normalized_retrieval_scores
1      0   Buda’pest Budapest     Q1781     phrase-match 20.43           0.316155989
1      0   Buda’pest Budapest     Q16467392 phrase-match 12.33           0.190807799
1      0   Buda’pest Budapest     Q55420238 phrase-match 18.2            0.281646549
1      1   Prague    Prague       Q1085     phrase-match 15.39           0.23816156
1      1   Prague    Prague       Q1953283  phrase-match 14.44           0.223460229
1      1   Prague    Prague       Q2084234  phrase-match 13.99           0.216496441
1      1   Prague    Prague       Q5969542  phrase-match 9.8             0.151655834
1      2   London!   London       Q84       phrase-match 32.31           0.5
1      2   London!   London       Q92561    phrase-match 25.625          0.396549056             
```

#### Implementation
For each retrieval method `m` and the candidate set `C` for a column,

<code>maxRetrievalScore(m) := max(retrievalScore(C))</code>

Then, for all candidates `c`, in the candidates set `C`, generated by retrieval method `m`,

<code>normalizedRetrievalScore(c) := (retrievalScore(c) / maxRetrievalScore(m)) * weight(m)</code>

Where `weight(m)` is specified by users, defaulting to `1.0`



## Ranking Candidate Commands
Ranking Candidate commands rank the candidate for each input cell. All Ranking Candidate commands takes as input a file in [Feature](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.meysv8c8z2mt)
format and output a file in [Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr)
format.

<a name="command_combine-linearly" />

### [`combine-linearly`](#command_combine-linearly)` [OPTIONS]`

Linearly combines two or more score-columns for candidate knowledge graph objects
for each input cell value. Takes as input `weights` for columns being combined to adjust influence. 

**Options:**
- `-w | --weights`: a comma separated string, in the format `<score-column-1>:<weight-1>,<score-column-2>:<weight-2>,...` representing weights for each score-column. Default weight for each score-column is `1.0`. 
- `-o a`: the output column name where the linearly combined scores will be stored. Default is `ranking_score`

**Examples:**
```bash
# linearly combine the columns 'normalized_score' and 'clean_labels_kg_labels_lev' with respective weights as '1.5' and '2.0'
$ tl combine_linearly -w normalized_score:1.5,clean_labels_kg_labels_lev:2.0 -o ranking_score < countries_features.csv > countries_features_ranked.csv
```

**File Examples:**
```bash
# consider the features file, countries_features.csv (some columns might be missing for simplicity)
$ cat countries_features.csv

column row clean_labels kg_id     kg_labels                             clean_labels_kg_labels_lev normalized_score 
1      0   Budapest     Q1781     Budapest|Buda Pest|Buda-Pest|Buda     1                          0.316155989      
1      0   Budapest     Q16467392 Budapest (chanson)                    0.44                       0.190807799      
1      0   Budapest     Q55420238 Budapest|Budapest, a song             1                          0.281646549      
1      1   Prague       Q1085     Prague|Praha|Praha|Hlavní město Praha 1                          0.23816156       
1      1   Prague       Q1953283  Prague, Oklahoma                      0.375                      0.223460229      
1      1   Prague       Q2084234  Prague, Nebraska                      0.375                      0.216496441      
1      1   Prague       Q5969542  Prague                                1                          0.151655834      
1      2   London       Q84       London|London, UK|London, England     1                          0.5              
1      2   London       Q92561    London ON                             0.66                       0.396549056      

# linearly combine the columns 'normalized_score' and 'clean_labels_kg_labels_lev' with respective weights as '1.5' and '2.0'
$ tl combine_linearly -w normalized_score:1.5,clean_labels_kg_labels_lev:2.0 -o ranking_score < countries_features.csv > countries_features_ranked.csv
$ cat countries_features_ranked.csv

column row clean_labels kg_id     kg_labels                             clean_labels_kg_labels_lev normalized_score ranking_score
1      0   Budapest     Q1781     Budapest|Buda Pest|Buda-Pest|Buda     1                          0.316155989      2.474233984
1      0   Budapest     Q16467392 Budapest (chanson)                    0.44                       0.190807799      1.166211699
1      0   Budapest     Q55420238 Budapest|Budapest, a song             1                          0.281646549      2.422469824
1      1   Prague       Q1085     Prague|Praha|Praha|Hlavní město Praha 1                          0.23816156       2.35724234
1      1   Prague       Q1953283  Prague, Oklahoma                      0.375                      0.223460229      1.085190344
1      1   Prague       Q2084234  Prague, Nebraska                      0.375                      0.216496441      1.074744662
1      1   Prague       Q5969542  Prague                                1                          0.151655834      2.227483751
1      2   London       Q84       London|London, UK|London, England     1                          0.5              2.75
1      2   London       Q92561    London ON                             0.66                       0.396549056      1.914823584
```

#### Implementation
Multiply the values in the input score-columns with their corresponding weights and add them up to get a ranking score for each candidate. 

For each candidate `c` and the set of score-columns `S`,

<code> rankingScore(c) := ∑(value(s) * weight(s)) ∀ s ∈ S </code>


## Commands on Ranking Score File

[Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr) files have a column which ranks the candidates for each input cell.

This commands in this module takes as input a [Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr)  file and outputs a file in [KG Links](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.ysslih9i88l5) format.


<a name="command_drop-by-score" />

### [`drop-by-score`](#command_drop-by-score)` [OPTIONS]`

The `drop-by-score` command outputs the top `k` score candidates for each `column, row` pair of the input file. The other candidates whose score is out of those will be removed.

**Options:**
- `-c a`: column name with ranking scores.
- `-k {number}`: desired number of output candidates per input cell.Defaut is `k=20`. 
- 

**Examples:**
```bash
# read the ranking score file test_file.csv and keep only the highest score on embed-score column
$ tl drop-by-score test_file.csv -c embed-score -k 1 > output_file.csv

# same example but with default options 
$ tl drop-by-score test_file.csv -c embed-score > output_file.csv
```

**File Example:**
```bash
# read the ranking score file countries_features_ranked.csv and ouput top 2 candidates, column 'clean_labels' have the cleaned input labels
# original file
      column  row                          label      kg_id  retrieval_score_normalized
        2    0   Vladimir Vladimirovich PUTIN      Q7747                    0.999676
        2    0   Vladimir Vladimirovich PUTIN  Q12554172                    0.405809
        2    0   Vladimir Vladimirovich PUTIN   Q1498647                    0.466929
        2    0   Vladimir Vladimirovich PUTIN  Q17052997                    0.404006
        2    0   Vladimir Vladimirovich PUTIN  Q17195494                    0.500758
      ...  ...                            ...        ...                         ...
        2   40  Vasiliy Alekseyevich NEBENZYA  Q64456113                    0.287849
        2   40  Vasiliy Alekseyevich NEBENZYA  Q65043723                    0.319638
        2   40  Vasiliy Alekseyevich NEBENZYA   Q7916774                    0.316741
        2   40  Vasiliy Alekseyevich NEBENZYA   Q7916778                    0.316741
        2   40  Vasiliy Alekseyevich NEBENZYA   Q7972769                    0.262559

$ tl drop-by-score test_file.csv -c embed-score -k 1 > output_file.csv
# output result, note than only 1 candidates remained for each (column, row) pair
$ cat output_file.csv
    column  row                                label      kg_id  retrieval_score_normalized
        2    0         Vladimir Vladimirovich PUTIN      Q7747                    0.999676
        2    1        Dmitriy Anatolyevich MEDVEDEV     Q23530                    0.999676
        2    2           Anton Germanovich SILUANOV    Q589645                    0.999740
        2    3           Maksim Alekseyevich AKIMOV   Q2587075                    0.619504
        2    4              Yuriy Ivanovich BORISOV   Q4093892                    0.688664
        2    5    Konstatin Anatolyevich CHUYCHENKO   Q4517811                    0.455497
        2    6         Tatyana Alekseyevna GOLIKOVA    Q260432                    0.999676
        2    7               Olga Yuryevna GOLODETS   Q3350421                    0.999676
        2    8         Aleksey Vasilyevich GORDEYEV    Q478290                    1.000000
        2    9           Dmitriy Nikolayevich KOZAK    Q714330                    0.601561
        2   10           Vitaliy Leyontyevich MUTKO   Q1320362                    0.666055
```

#### Implementation
Group by  column and row indices and pick the top `k` candidates for each input cell. Then drop the remained part of the files and output the result.


<a name="command_drop-duplicate" />

### [`drop-duplicate`](#command_drop-duplicate)` [OPTIONS]`

The `drop-duplicate` command outputs the duplicate rows based on the given column information and keep the one with a higher score on the specified score column. This comamnd usually will be used when multiple candidates generating methods was called, those different method may generate same candidates multiple times which may influence future processes.

**Options:**
- `-c a`: column name with duplicate things, usually it should be `kg_id` column.
- `--score-column {string}`: the reference score column for deciding which row to drop.
- 

**Examples:**
```bash
# read the ranking score file test_file.csv and keep the higher score on `retrieval_score_normalized` column if duplicate found on (column, row, kg_id) pairs.
$ tl drop-duplicate test_file.csv -c kg_id --score-column retrieval_score_normalized
```

**File Example:**
```bash
# read the ranking score file countries_features_ranked.csv and ouput top 2 candidates, column 'clean_labels' have the cleaned input labels
# original file
    column  row                                label      kg_id        method  retrieval_score_normalized
      2    0         Vladimir Vladimirovich PUTIN      Q7747   exact-match                    0.999676
      2    0         Vladimir Vladimirovich PUTIN      Q7747  phrase-match                    0.456942
      2    1        Dmitriy Anatolyevich MEDVEDEV     Q23530   exact-match                    0.999676
      2    2           Anton Germanovich SILUANOV    Q589645   exact-match                    0.999740
      2    3           Maksim Alekseyevich AKIMOV   Q2587075  phrase-match                    0.619504
      2    4              Yuriy Ivanovich BORISOV   Q4093892  phrase-match                    0.688664

$ tl drop-duplicate test_file.csv -c kg_id --score-column retrieval_score_normalized > output_file.csv
# output result, note than the duplicate row for column, row pair (2,0) was removed and the one with higher retrieval_score_normalized was kept.
$ cat output_file.csv
    column  row                                label      kg_id        method  retrieval_score_normalized
      2    0         Vladimir Vladimirovich PUTIN      Q7747   exact-match                    0.999676
      2    1        Dmitriy Anatolyevich MEDVEDEV     Q23530   exact-match                    0.999676
      2    2           Anton Germanovich SILUANOV    Q589645   exact-match                    0.999740
      2    3           Maksim Alekseyevich AKIMOV   Q2587075  phrase-match                    0.619504
      2    4              Yuriy Ivanovich BORISOV   Q4093892  phrase-match                    0.688664

```

#### Implementation
Group by  column and row and specified column pairs indices and pick the higher score one.

<a name="command_get-kg-links" />

### [`get-kg-links`](#command_get-kg-links)` [OPTIONS]`

The `get-kg-links` command outputs the top `k` candidates from a sorted list, 
as linked knowledge graph objects for an input cell.
The candidate with the highest score is ranked highest, ties are broken alphabetically.

**Options:**
- `-c a`: column name with ranking scores.
- `-l a`: column name with input cell labels. Default is `label`. These values will be stored in the output column `label` in the output file for this command.
- `-k {number}`: desired number of output candidates per input cell.Default is `k=1`. Multiple values are represented by a `|` separated string

**Examples:**
```bash
# read the ranking score file countries_features_ranked.csv and output top 2 candidates, use the column clean_labels for cleaned input cell labels
$ tl get-kg-links -c ranking_score -l clean_labels -k 2 countries_features_ranked.csv > countries_kg_links.csv

# same example but with default options 
$ tl get-kg-links -c ranking_score < countries_features_ranked.csv > countries_output.csv
```

**File Example:**
```bash
# read the ranking score file countries_features_ranked.csv and ouput top 2 candidates, column 'clean_labels' have the cleaned input labels
$ tl get-kg-links -c ranking_score -l clean_labels -k 2 countries_features_ranked.csv > countries_kg_links.csv
$ cat countries_links.csv

column row label        kg_id           kg_labels         ranking_score
1      0   Budapest     Q1781|Q55420238 Budapest|Budapest 2.474233984|2.422469824
1      1   Prague       Q1085|Q5969542  Prague|Prague     2.35724234|2.227483751
1      2   London       Q84|Q92561      London|London ON  2.75|1.914823584
```

#### Implementation
Group by  column and row indices and pick the top `k` candidates for each input cell to produce an output file in [KG Links](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.ysslih9i88l5) format. 

Pick the preferred labels for candidate KG objects from the column `kg_labels`, which is added by the [`get-exact-matches`](#command_get-exact-matches) command.
In case of more than one  preferred label for a candidate, the first label is picked.



<a name="command_join" />

### [`join`](#command_join)` [OPTIONS]`

The `join` command outputs the top `k` candidates from a sorted list as linked knowledge graph objects for an input cell. 
This command takes as input a [Input](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.7pj9afmz3h1t)
 file and a file in [Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr) format and outputs a file in [Output](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.6rlemqh56vyi) format.
 
 The candidate with the highest score is ranked highest, ties are broken alphabetically.

**Options:**
- `-f {path}`: the original input file path.
- `-c a`: column name with ranking scores.
- `-k {number}`: desired number of output candidates per input cell.Defaut is `k=1`. Multiple values are represented by `|` separated string

**Examples:**
```bash
# read the input file countries.csv and the ranking score file countries_features_ranked.csv and output top 2 candidates
$ tl join -f countries.csv -c ranking_score -k 2 countries_features_ranked.csv > countries_output.csv

# same example but with default options 
$ tl join -f countries.csv -c ranking_score < countries_features_ranked.csv > countries_output.csv
```

**File Example:**
```bash
# read the input file countries.csv and the ranking score file countries_features_ranked.csv and ouput top 2 candidates
$ tl join -f countries.csv -c ranking_score -k 2 countries_features_ranked.csv > countries_output.csv
$ cat countries_output.csv

country        capital_city phone_code capital_city_kg_id capital_city_kg_label capital_city_score
Hungary        Buda’pest    +49        Q1781|Q55420238    Budapest|Budapest     2.474233984|2.422469824
Czech Republic Prague       +420       Q1085|Q5969542     Prague|Prague         2.35724234|2.227483751
United Kingdom London!      +44        Q84|Q92561         London|London ON      2.75|1.914823584
```

#### Implementation
Join the input file and the ranking score file based on column and row indices to produce an output file. In case of more than one  preferred label
for a candidate, the first label is picked. The corresponding values in each output column have the same index, in case of `k > 1`

This command will add the following three columns to the input file to produce the output file.
- `<input_column_name>_kg_id`: stores the KG object identifiers. Multiple values represented as a `|` separated string.
- `<input_column_name>_kg_label`: if the column `kg_labels` is available(added by the [`get-exact-matches`](#command_get-exact-matches) command), stores the KG object preferred labels. Each KG object will contribute one preferred label. In case of multiple preferred labels per KG object, pick the first one. 
Multiple values are represented as `|` separated string. If the column `kg_labels` is not available, empty string "" is added
- `<input_column_name>_score`: stores the ranking score for KG objects. Multiple values are represented by a `|` separated string.


## Evaluation Commands
Evaluation commands take as input a [Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr) file
and a [Ground Truth](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.63n3hyogxr1e) file and output a file in the 
[Evaluation File](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.vurz5diqkuf7) format.
These commands help in calculating `precision` and `recall` of the table linker `(tl)` pipeline.


<a name="command_ground-truth-labeler" />

###  [`ground-truth-labeler`](#command_ground-truth-labeler)` [OPTIONS]`
The `ground-truth-labeler` command compares each candidate for the input cells with the ground truth value for that cell and
adds an evaluation label.

**Options:**
- `-f {path}`: ground truth file path.
- `-c a`:  column name with ranking scores

**File Examples:**
```bash
# the ground truth file, countries_gt.csv
$ cat countries_gt.csv

column row kg_id
1      0   Q1781
1      2   Q84

# add evaluation label to the ranking score file countries_features_ranked.csv, having the column 'ranking_score', using the ground truth file countries_gt.csv
$ tl ground-truth-labeler -f countries_gt.csv -c ranking_score  < countries_features_ranked.csv > countries_evaluation.csv
$ cat countries_evaluation.csv

column row clean_labels kg_id     ranking_score evaluation_label GT_kg_id GT_kg_label
1      0   Budapest     Q1781     8.01848598     1               Q1781    Budapest
1      0   Budapest     Q16467392 4.152548805   -1               Q1781    Budapest
1      0   Budapest     Q55420238 7.65849315    -1               Q1781    Budapest
1      1   Prague       Q1085     7.00211745     0                        
1      1   Prague       Q1953283  4.19621823     0                        
1      1   Prague       Q2084234  4.029960225    0                        
1      1   Prague       Q5969542  5.81884368     0                        
1      2   London       Q84       9.02968554     1               Q84      London
1      2   London       Q92561    5.757565725   -1               Q84      London
```

#### Implementation

Join the ranking score file and the ground truth file based on column and row indices and add the following columns,
- `evaluation_label`: The permissible values for the evaluation label are in range `{-1, 0, 1}`. The value `1` means the cell is present in the Ground Truth file and the candidate is same as  knowledge graph object in the Ground Truth File.  

The value `0` means the cell is not present in the Ground Truth File. The value `-1` means the cell is present 
in the Ground Truth File and the candidate is different from the corresponding knowledge graph object in the Ground Truth File.
- `GT_kg_id`: identifier of the knowledge graph object in the ground truth
- `GT_kg_label`: preferred label of the knowledge graph object in the ground truth. The labels for the candidates are
 added by the [get-exact-matches](#command_get-exact-matches) command and are stored in the column `kg_labels`. 
 If the column is not present or in case of missing preferred label, empty string "" is added.

## Utility Commands

<a name="command_add-color" />

### [`add-color`](#command_add-color)` [OPTIONS]`

The `add-color` command is a special command that can only run as the last step of the pipeline / run separately because the generated file is a `xlsx` file but not a `csv` file. This command can be used to marked the `top-k` score of specified score columns for better visualization.
It also support with a `ground-truth` format which can only run on a file after running with `add-text-embedding-feature` function and `ground-truth` column-vector-strategy. The rows for each candidate will then be ordered descending by gt score,  except that the first row is the ground truth candidate regardless of  whether it didn't get the highest gt cosine score

**Options:**

- `-c`: The score columns need to be colored.
- `-k`: The amount of highest scores need to be colored.
- `--output`: The output path to save the output xlsx file.
- `--sort-by-ground-truth`: A flag option, pass with flag only to set to sort by ground truth score.
- `--ground-truth-score-column`:  Only valid when pass with `--sort-by-ground-truth`, the column name of the ground truth score.
**Examples:**
```bash
# color the `test.csv` file on column `evaluation_label` and `retrieval_score_normalized` 
# then save to desktop
# run with sort by ground turth condition.
$ tl add-color ~/Desktop/test.csv -k 5 \
-c retrieval_score_normalized evaluation_label \
--sort-by-ground-truth \
--ground-truth-score-column gt_embed_score_normalized \
--output ~/Desktop/test_colored.xlsx

# run color only
$ tl add-color ~/Desktop/test.csv -k 5 \
-c retrieval_score_normalized evaluation_label \
--output ~/Desktop/test_colored.xlsx
```

**File Example:**
```bash
# the output is same as the input file if not sort
   column  row  retrieval_score_normalized  evaluation_label  gt_embed_score_normalized
0       2    0                    0.999676                 1                   0.398855
1       2    0                    0.405809                -1                   0.403718
2       2    0                    0.466929                -1                   0.203675
3       2    0                    0.404006                -1                   0.255186
4       2    0                    0.500758                -1                   0.243571
5       2    0                    0.541115                -1                   0.675757
6       2    0                    0.417415                -1                   0.231361
7       2    0                    0.752838                -1                   0.540415
8       2    0                    0.413938                -1                   0.220305
9       2    0                    0.413938                -1                   0.228466
```

#### Implementation
By using pandas's xls writer function, add some special format to some cells.


<a name="command_plot-score-figure" />

### [`plot-score-figure`](#command_plot-score-figure)` [OPTIONS]`

The `plot-score-figure` command is a special command that can only run as the last step of the pipeline / run separately because the generated file is a `png` file or a `html` file but not a `csv` file. This command can be used to evaulate the predictions results and generated scores of the table linker.
It only support the plot on the results after running with `ground-truth-labler` as ground truth information is needed for evaluation. 
The first plot will be a `png` image, which includes the top `k` scores of the specified score columns in accuracy and corresponding normalized score.
The second plot will be a `html` page, which includes the scores of specified columns on correct candidates and some high score wrong candidates if required. This page allow users to do interaction operations like remove the view of the score on specific columns, enlarge and many other choices...

**Options:**

- `-c list{string}`: The score columns need to be colored.
- `-k list{int}`: The amount of highest scores need to be colored.
- `--output`: The output path to save the output file, please do not add the suffix of the file name.
- `--add-wrong-candidates`: A flag option, pass with flag only to add the wrong candidates on second plot.
- `--wrong-candidates-score-column {string}`:  Only valid when pass with `--add-wrong-candidates`, the column name of the wrong candidates column need to display.

**Examples:**
```bash
# plot the figures for `test.csv` file on column `evaluation_label` and `retrieval_score_normalized` 
# then save to desktop, also add the evaluation wrong candidates on second graph
$ tl plot-score-figure ~/Desktop/test.csv -k 1 2 5 \
-c retrieval_score_normalized evaluation_label \
--add-wrong-candidates retrieval_score_normalized \
--output ~/Desktop/output_figure

# run default plot
$ tl plot-score-figure ~/Desktop/test.csv -k 1 2 5 \
-c retrieval_score_normalized evaluation_label \
--output ~/Desktop/output_figure
```

**File Example:**
The output is not a table, please refer to [here](https://drive.google.com/drive/u/2/folders/14YCA2cWhARr6GMS0KDmCiV-uw7r4AwfE) (access needed).

#### Implementation
By using python package `seaborn` and `pyecharts`, we plotted the output figures.

<a name="command_run-pipeline" />

### [`run-pipeline`](#command_run-pipeline)` [OPTIONS]`

The `run-pipeline` command is a batch running command that enable users to run same pipelines on a batch of files automatically and then evaluate the pipeline running results if possible.

**Options:**

- `--ground-truth-directory`: The ground truth directory.
- `--ground-truth-file-pattern`: the pattern used to create the name of the ground truth file from the name of an input file. 
The pattern is any string where the characters {} are substituted by the name of the input file minus the extension. 
For example “{}_gt.csv” specifies that the ground truth file for input file abc.csv is abc_gt.csv. The default is “{}_gt.csv”
- `--pipeline`: the pipeline to run.
- `--score-column`: The column name with scores for evaluation
- `--gpu-resources`: Optional, if given, the system will use only the specified GPU ID for running.
- `--tag`: a tag to use in the output file to identify the results of running the given pipeline
- `--parallel-count`: Optional, if specified, the system will run `n`processes in parallel. Default is `1`.
- `--output`: optional, defines a name for the output file for each input file. The pattern is a string where {} gets substituted by the name of the input file, minus the extension.
Default is `output_{}`
- `--output-folder`: optional, if given, the system will save the output file of each pipeline to given folder with given file naming pattern from `--output`.
- `--omit-headers`:  if this option is present, no headers will be output. If the option is omitted, the default, the first line will contain headers.
- `--debug`: if this flag is present, system will print all the table-linker commands which are running for debugging purpose.

**Examples:**
```bash
# run a pipeline on all files starting with `v15_68` and ends with `.csv` on folder `iswc_challenge_data/round4/canonical/`
# clean -> get exact-matches candidates -> normalize score -> get phase-matches -> normalize score -> add ground truths -> get embedding scores 
# Set to output with a tag gt-embed and score the output base on column `embed-score`, and run 4 processes parallelly. Also, turn on the debug mode.
$ tl run-pipeline \
  --tag gt-embed \
  --gpu-resources 1 \
  --parallel-count 4 \
  --score-column embed-score \
  --debug \
  --ground-truth-directory iswc_challenge_data/round4/gt \
  --ground-truth-file-pattern {}.csv \
  --pipeline 'clean -c label / get-exact-matches -c label_clean / normalize-scores -c retrieval_score \
    / get-phrase-matches -c label_clean -n 5 --filter "retrieval_score_normalized > 0.9" / normalize-scores -c retrieval_score \
    / ground-truth-labeler -f iswc_challenge_data/round4/gt/{}.csv \
    / add-text-embedding-feature --column-vector-strategy ground-truth -n 0 --run-TSNE True \
    --distance-function cosine -o embed-score \
    iswc_challenge_data/round4/canonical/v15_68*.csv
```

**File Example:**
```
tag         file      precision recall      f1
gt-embed  v15_685.csv 0.473684211 0.473684211 0.473684211
gt-embed  v15_686.csv 0.115384615 0.115384615 0.115384615
```

#### Implementation
This command used python's subprocess to call shell functions then execute the corresponding shell codes.

<a name="command_tee" />

### [`tee`](#command_tee)` [OPTIONS]`

The `tee` command saves the input to disk and echoes the input to the standard output without modification. The command can be put anywhere in a pipeline to save the input to a file.
This command is a wrap of the linux command `tee`

**Options:**
- `--output`: the path where the file should be saved.

**Examples:**
```bash
# After performing the expensive operations to get candidates and compute embeddings, save the file to disk and continue the pipeline.
$ tl clean / 
    / get-exact-matches -c label \
    / ground-truth-labeler -f “./xxx_gt.csv” \
    / add-text-embedding-feature --column-vector-strategy ground-truth -n 3 \
      --generate-projector-file xxx-google-projector -o embed 
    / tee --output xxx-features.csv \
    / normalize-scores \
    / metrics
```


