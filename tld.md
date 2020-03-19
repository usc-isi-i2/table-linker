# [« Home](https://github.com/usc-isi-i2/table-linker) / Command Line Interface

  This document describes the command-line interface for the <code>Table Linker (tl)</code> system.


## Installation Instructions



## Pipelines
The `tl` CLI works by pushing CSV data through a series of [commands](#commands), starting with a single input on `stdin` and ending with a single output on `stdout`. This pipeline feature allows construction of pipelines for linking table cells to a knowledge graph (KG).

### `Usage:  tl [OPTIONS] COMMAND [ / COMMAND]* `

**Table of Contents:**
- [`canonicalize`](#command_canonicalize): translate an input CSV or TSV file to [canonical form](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.wn7c3l1ngi5z)
- [`clean`](#command_clean) : clean the values to be linked to the KG   
- [`generate-candidates`](#command_generate-candidates): retrieves the identifiers of KG entities whose label or aliases match the input values exactly.
- [`string-similarity`](#command_string-similarity): command compares the cell values in two input columns and outputs a similarity score for each pair of participating strings 
- [`merge-columns`](#command_merge-columns): merges values from two or more columns and outputs the concatenated value in the output column
- [`normalize-scores`](#command_normalize-scores): normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval method for all input cells
- [`combine-linearly`](#command_combine-linearly): combines the two or more columns with scores for candidate knowledge graph objects for each input cell value
- [`outputter`](#command_outputter): outputs the top k candidates from a sorted list of ranking scores, as linked knowledge graph object for input cell values
- [`ground-truth-labeler`](#command_ground-truth-labeler): compares each candidate for the input cells with the ground truth value for that cell and adds an evaluation label


**Options:**
- `-e, --examples` -- Print some examples and exit
- `-h, --help` -- Print this help message and exit
- `-v, --version` -- Print the version info and exit
- `--url {url}`:  URL of the ElasticSearch index containing the items in the KG.
- `-U {user id}`: the user id for authenticating to the ElasticSearch index.
- `-P {password}`: the password for authenticating to the ElasticSearch index.

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
- `-f {path}`: specified auxiliary file path as input to commands

## Commands On Raw Input Files

<a name="command_canonicalize" />

### [`canonicalize`](#command_canonicalize)` [OPTIONS]`
translate an input CSV or TSV file to [canonical form](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.wn7c3l1ngi5z)

**Options:**
- `-c {a,b,c}`: the columns in the input file to be linked to KG entities. Multiple columns are specified as a comma separated string. 
- `-o {string}`: specifies the name of a new column to be added. Default output column name is `label`
- `--tsv`:  the delimiter of the input file is TAB.
- `--csv`: the delimiter of the input file is comma.
 
### Implementation
Assign zero based indices to the input columns and corresponding rows. 
The columns are indexed from left to right and rows from top to bottom. The first row is column header, the first data row is
assigned index 0.

**Examples:**
   ```bash
   # Build a canonical file to link the 'people' and 'country' columns in the input file
   $ tl canonicalize -c people,country < input.csv > canonical-input.csv
   $ cat input.csv | tl canonicalize -c people,country > canonical-input.csv

   # Same, but using column an indice to specify the country column
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
```

## Commands On Canonical Files
[Canonical files](link) contain one row per cell to be linked. 

<a name="command_clean" />

### [`clean`](#command_clean)` [OPTIONS]`
The `clean` command cleans the cell values in a column, creating a new column with the clean values.
 The `clean` command performs two types of cleaning:

- Invokes the [ftfy](https://pypi.org/project/ftfy/) library to fix broken unicode characters and html tags.
- Removes or replaces symbols by space.

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

All candidate generation commands take a column in a canonical file as input and produce a set of KG identifiers for each row in a canonical file and candidates are stored one per row. A `method` column records the name of the strategy that produced a candidate.

When a cell contains a |-separated string (e.g., `Pedro|Peter`, the string is split by `|` and candidates are fetched for each of the resulting values.

<a name="command_get-exact-matches" />

### [`get-exact-matches`](#command_get-exact-matches)` [OPTIONS]`
This command retrieves the identifiers of KG entities whose label or aliases match the input values exactly.

**Options:**
- `-c a`: the column used for retrieving candidates.
- `-p {a,b,c}`:  names of properties in the KG to search for exact match query: default is `label` and `alias`. 
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

### Implementation

The `get-exact-matches` command will be implemented using an ElasticSearch index built using an Edges file in KGTK format.
Two ElasticSearch term queries are defined, one for exact match retrieval and one for case-insensitive exact match retrieval.

-   Exact match query: In Elasticsearch language, this will be a terms query. Terms query allows search for multiple terms. This query retrieves documents which have the exact search term as label or aliases.
-   Exact match lowercase query: Same as Exact match query but with lowercase search terms.

**Examples:**

```bash
   # generate candidates for the cells in the column 'label_clean'
   $ tl --url http://blah.com -Ujohn -Ppwd  get-exact-matches -c label_clean  < canonical-input.csv

   # clean the column 'label' and then generate candidates for the resulting column 'label_clean' with case insensitive matching
   $ tl --url http://blah.com -Ujohn -Ppwd clean -c label / get-exact-matches -c label_clean -i  < canonical-input.csv

```

**File Example:**

```
# generate candidates for the canonical file, countries_canonical.csv
$ tl --url http://blah.com -Ujohn -Ppwd  get-exact-matches -c clean_labels  < countries_canonical.csv > countries_candidates.csv
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

## Adding Features Commands

Add-Feature commands add one or more features for the candidate knowledge graph objects for the input cells.
All Add-Feature commands take a column in a [candidate](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.j9cdkygbzzq7) 
or a [feature](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.meysv8c8z2mt) file 
and output a [feature](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.meysv8c8z2mt) file. 

<a name="command_string-similarity" />

### [`string-similarity`](#command_string-similarity)` [OPTIONS]`
The `string-similarity` command compares the cell values in two input columns and outputs a similarity score for
 each pair of participating strings in the output column. 
 
The `string-similarity` command supports the following string similarity algorithms,

- [Normalized Levenshtein](https://en.wikipedia.org/wiki/Levenshtein_distance): The levenshtein distance between two words in the minimum number single-character edits needed to change one word into the other. Normalized levenshtein is computed as the levenshtein distance divided by the length of the longest string.
 The similarity is computed as `1 - normalized distance`.  The value is between `[0.0, 1.0]`.
- [Jaro Winkler](https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance#Jaro%E2%80%93Winkler_Similarity): Jaro Winkler is a string edit distance designed for short strings. In Jaro Winkler, substitution of 2 close characters is considered less important than the substitution of 2 characters that are far from each other. 
String similarity is computed as `1 - Jaro-Winkler distance`. The value is between `[0.0, 1.0]`

In future, more string similarity algorithms will be supported
 
**Options:**
- `-c {a,b}`: input columns containing the cells to be compared. The two columns are represented as a comma separated string.
- `--lev`: Use Normalized Levenshtein 
- `--jw`: Use Jaro Winkler
- `-i`: case insensitive comparison. Default is case sensitive

The string similarity scores are added to a output column, whose name will be in the format <col_1>\_<col_2>\_\<algorithm>.
 
If none of `--lev` or `--jw` options are specified, `--lev` is used. In case both `--lev` and `--jw` options are specified, 
two output columns will be added as described above, recording string similarity scores using both algorithms.

#### Implementation
For any input cell value, s and  a candidate c, String similarity outputs a score computed as follows,

<code> stringSimilarity(s, c) := max(similarityFunction(s, l)) ∀ l ∈ { labels(c) } </code> 

**Examples:**

```bash
# compute similarity score for the columns 'clean_labels' and 'kg_label', use Normalized Levenshtein, case sensitive comparison
$ tl string-similarity -c clean_labels,kg_label --lev < countries_candidates.csv

# compute similarity score for the columns 'doc_labels' and 'doc_aliases', use Jaro Winkler, case insensitive comparison
$ tl string-similarity -c doc_labels,doc_aliases  --jw -i countries_candidates.csv
```

**File Example:**
```
# compute string similarity between the columns 'clean_labels' and 'kg_labels', using case sensitive Normalized Levenshtein 
# for the file countries_candidates.csv, exclude columns 'label','method' and 'retrieval_score' while printing
$ tl string-similarity -c clean_labels,kg_labels --lev < countries_candidates.csv > countries_ss_features.csv \
&& mlr --opprint cut -f label,method,retrieval_score -x countries_ss_features.csv

column row clean_labels kg_id     kg_labels                             clean_labels_kg_labels_lev
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

<a name="command_merge-columns" />

### [`merge-columns`](#command_merge-columns)` [OPTIONS]`
The `merge-columns` command merges values from two or more columns and outputs the concatenated value in the output column. 
 
 **Options:**
- `-c {a,b,...}`: a comma separated string with columns names, values of which are to be concatenated together.
- `-o a`: the output column name where the concatenated values will be stored.
- `--remove-duplicates {yes/no}`: remove duplicates across or not. Default is `yes` 
 Multiple values in the output column are represented by a `|` separated string.
 
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

column row label     clean_labels kg_id     kg_label           kg_aliases                 method      retrieval_score kg_label_aliases
1      0   Buda’pest Budapest     Q1781     Budapest           Buda Pest|Buda-Pest|Buda   exact-match 20.43           Budapest|Buda Pest|Buda-Pest|Buda
1      0   Buda’pest Budapest     Q16467392 Budapest (chanson) ""                         exact-match 12.33           Budapest (chanson)
1      0   Buda’pest Budapest     Q55420238 Budapest           Budapest, a song           exact-match 18.2            Budapest|Budapest, a song
1      1   Prague    Prague       Q1085     Prague|Praha       Praha|Hlavní město Praha   exact-match 15.39           Prague|Praha|Hlavní město Praha
1      1   Prague    Prague       Q1953283  Prague, Oklahoma   ""                         exact-match 14.44           Prague, Oklahoma
1      1   Prague    Prague       Q2084234  Prague, Nebraska   ""                         exact-match 13.99           Prague, Nebraska
1      1   Prague    Prague       Q5969542  Prague             ""                         exact-match 9.8             Prague
1      2   London!   London       Q84       London             London, UK|London, England exact-match 32.31           London|London, UK|London, England
1      2   London!   London       Q92561    London ON          ""                         exact-match 25.625          London ON

```

<a name="command_normalize-scores" />

### [`normalize-scores`](#command_normalize-scores)` [OPTIONS]`
The `normalize-score` command normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval method for all input cells in a column.
This command will find the maximum retrieval score for candidates generated by a retrieval method, 
and then divide the individual candidate retrieval scores, generated by this method, by the maximum retrieval score for each input column.

Note that the column containing the retrieval method names is `method`, added by the [generate-candidates](#command_generate-candidates) command.

**Options:**
- `-c a`: column name which has the retrieval scores. Default is `retrieval_score`
- `-o a`: the output column name where the normalized scores will be stored. Default is input column name appended with the suffix `_normalized`
- `-w|--weights`: a comma string of the format `<retrieval_method_1}:<weight_1>, <retrieval_method_2:<weight_2>,...>`
 specifying the weights for each retrieval method.By default, all retrieval method weights are set to 1.0

#### Implementation
For each retrieval method `m` and the candidate set `C` for a column,

<code>maxRetrievalScore(m) := max(retrievalScore(c)) ∀ c ∈ C</code>

Then, for all candidates `c` generated by retrieval method `m`,

<code>normalizedRetrievalScore(c) := (retrievalScore(c) / maxRetrievalScore(m)) * weight(m)</code>

Where `weight(m)` is specified by users, defaulting to `1.0`

**Examples:**
```bash
# compute normalized scores with default options
$ tl normalize-scores < countries_candidates.csv > countries_candidates_normalized.csv

# compute normalized scores the column 'es_score', output in the column 'normalized_es_scores' with specified weights
$ tl normalize-scores -c es_score -o normalized_es_scores -w 'es_method_1:0.4,es_method_2:0.92' countries_candidates.csv
```

**File Example:**
```bash
# compute normalized scores the column 'retrieval_score', output in the column 'normalized_retrieval_scores' with specified weights
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

## Ranking Candidate Commands
Ranking Candidate suite of commands rank the candidate for each input cell. All Ranking Candidate commands takes as input a file in [feature](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.meysv8c8z2mt)
format and output a file in [ranking score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr)
format.

<a name="command_combine-linearly" />

### [`combine-linearly`](#command_combine-linearly)` [OPTIONS]`

Linearly combines the two or more columns with scores  for candidate knowledge graph objects
for each input cell value. Takes as input `weights` for columns being combined to adjust influence. 

**Options:**
- `-w | --weights`: a comma separated string, in the format `<score-column-1>:<weight-1>,<score-column-2>:<weight-2>,...` representing weights for each score column. Default weight for each score column is `1.0`. 
- `-o a`: the output column name where the linearly combined scores will be stored.

#### Implementation
Multiply the values in the input columns with their corresponding weights and adds them up to get a ranking score for each candidate. 

For each candidate `c` and the set of score columns `S`,

<code> rankingScore(c) := ∑(value(s) * weight(s)) ∀ s ∈ S </code>

**Examples:**
```bash
# linearly combine the columns 'normalized_score' and 'levenshtein_similarity' with respective weights as '1.5' and '4.2'
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
$ tl combine_linearly -c normalized_score,clean_labels_kg_labels_lev -w 1.5,4.2 -o ranking_score < countries_features.csv > countries_features_ranked.csv
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

## Commands on Ranking Score File

[Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr) files have a column which ranks 
the candidates for each input cell.

<a name="command_get-kg-links" />

### [`get-kg-links`](#command_get-kg-links)` [OPTIONS]`

The `get-kg-links` command outputs the top `k` candidates from a sorted list of ranking scores, 
as linked knowledge graph objects for an input cell.
The candidate with the highest score is ranked highest, ties are broken alphabetically.

This module takes as input a 
[Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr) 
file and outputs a file in [KG Links](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.ysslih9i88l5) format.

**Options:**
- `-c a`:	column name with ranking scores.
- `-l a`: column name with input cell labels. Default is `label`. These values will be stored in the output column `label` in the output file for this command.
- `-k {number}`: desired number of output candidates per input cell.Defaut is `k=1`. Multiple values are represented by `|` separated string

#### Implementation
Group by  column and row indices and pick the top `k` candidates for each input cell to produce an output file in [KG Links](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.ysslih9i88l5) file format. 
The column `kg_labels` is added by the [`get-exact-matches`](#command_get-exact-matches) command.
In case of more than one  preferred label for a candidate, the first label is picked from the `|` separated string.

**Examples:**
```bash
# read the ranking score file countries_features_ranked.csv and ouput top 2 candidates, use the column clean_labels for cleaned input cell labels
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

<a name="command_join" />

### [`join`](#command_join)` [OPTIONS]`

The `join` command outputs the top `k` candidates from a sorted list of ranking scores, 
as linked kmnowledge graph object for an input cell. This module takes as input a [Input](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.7pj9afmz3h1t)
 file and a file in Ranking Score format and outputs a file in [Output](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.6rlemqh56vyi) format.

**Options:**
- `-f {path}`: the original input file path.
- `-c a`:	column name with ranking scores.
- `-k {number}`: desired number of output candidates per input cell.Defaut is `k=1`. Multiple values are represented by `|` separated string

#### Implementation
Join the input file and the ranking score file based on column and row indices to produce an output file. In case of more than one  preferred label
for a candidate, the first label is picked from the `|` separated string. The corresponsing values in each output column have the same index, in case of `k > 1`

This command will add the following three columns to the input file to produce the output file.
- `<input_column_name>_kg_id`: stores the KG object identifiers. Multiple values represented as a `|` separated string.
- `<input_column_name>_kg_label`: if the column `kg_labels` is available(added by the [`get-exact-matches`](#command_get-exact-matches) command), stores the KG object preferred labels. Each KG object will contribute one preferred label. In case of multiple preferred labels per KG object, pick the first one. 
Multiple values are represented as `|` separated string. If not available, empty string "" is added
- `<input_column_name_score`: stores the ranking score for KG objects. Multiple values are represented by a `|` separated string.

**Examples:**
```bash
# read the input file countries.csv and the ranking score file countries_features_ranked.csv and ouput top 2 candidates
$ tl outputter -f countries.csv -c ranking_score -k 2 countries_features_ranked.csv > countries_output.csv

# same example but with default options 
$ tl outputter -f countries.csv -c ranking_score < countries_features_ranked.csv > countries_output.csv
```

**File Example:**
```bash
# read the input file countries.csv and the ranking score file countries_features_ranked.csv and ouput top 2 candidates
$ tl outputter -f countries.csv -c ranking_score -k 2 countries_features_ranked.csv > countries_output.csv
$ cat countries_output.csv

country        capital_city phone_code capital_city_kg_id capital_city_kg_label capital_city_score
Hungary        Buda’pest    +49        Q1781|Q55420238    Budapest|Budapest     2.474233984|2.422469824
Czech Republic Prague       +420       Q1085|Q5969542     Prague|Prague         2.35724234|2.227483751
United Kingdom London!      +44        Q84|Q92561         London|London ON      2.75|1.914823584
```

## Evaluation Commands
Evaluation commands take as input a [Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr)
and a [Ground Truth](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.63n3hyogxr1e) and output a file in the 
[Evaluation File](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.vurz5diqkuf7) format.
These commands help in calculating `precision` and `recall` of the table linker `(tl)` pipeline.

<a name="command_ground-truth-labeler" />

###  [`ground-truth-labeler`](#command_ground-truth-labeler)` [OPTIONS]`
The `ground-truth-labeler` command is an evaluation module which compares each candidate for the input cells with the ground truth value for that cell and
adds an evaluation label.

**Options:**
- `-f {path}`: ground truth file path.
- `-c a`:  column name with ranking scores

#### Implementation

Join the ranking score file and the ground truth file based on column and row indices and add the following columns,
- `evaluation_label`: The permissible values for the evaluation label are in range {-1, 0, 1}. The value `1` means the cell is present in the Ground Truth file and the highest ranked candidate is the same as the corresponding knowledge graph object in the Ground Truth File, 
the value `0` means the cell is not present in the Ground Truth File and the value `-1` means the cell is present 
in the Ground Truth File and the highest ranked candidate is different from the corresponding knowledge graph object in the Ground Truth File.
- `GT_kg_id`: identifier of the knowledge graph object in the ground truth
- `GT_kg_label`: preferred label of the knowledge graph object in the ground truth

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
