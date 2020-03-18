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
- [`normalize-scores`](#command_normalize_scores): normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval method for all input cells
- [`combine-linearly`](#command_combine-linearly): combines the two or more columns with scores for candidate knowledge graph objects for each input cell value
- [`outputter`](#command_outputter): outputs the top k candidates from a sorted list of ranking scores, as linked kmnowledge graph object
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

All candidate generation command take a column in a canonical file as input and produce a set of KG identifiers for each row in a canonical file and candidates are stored one per row. A `method` column records the name of the strategy that produced a candidate.
This command will add two columns `kg_label` and `kg_aliases` to record the labels and aliases of the candidate knowledge graph object. In case of missing
labels or aliases, an empty string "" is recorded. The retrieval score is recorded in the column `retrieval_score`. The identifiers for the
 candidate knowledge graph objects are recorded in the column `kg_id`.

When a cell contains a |-separated string (e.g., `Pedro|Peter`, the string is split by `|` and candidates are fetched for each of the resulting values.

<a name="command_generate-candidates" />

### [`generate-candidates`](#command_generate-candidates)` [OPTIONS]`
This command retrieves the identifiers of KG entities whose label or aliases match the input values exactly.
 Currently, `tl` supports the candidate generation method, `exact-match`. In future, more candidate generation methods will be implemented.

**Options:**
- `-c a`: the column used for retrieving candidates.
- `-p {a,b,c}`:  names of properties in the KG to search for exact match query: default is `label` and `alias`.
- `--method {string}`: name of the candidate retrieval method. For example, `exact-match`. 
- `-i`: case insensitive retrieval, default is case sensitive.
- `-n {number}`: maximum number of candidates to retrieve, default is 50.

### Implementation

The `generate-candidates` command will be implemented using an ElasticSearch index built using an Edges file in KGTK format.

#### Exact Match
For the `exact-match` method, two ElasticSearch term queries are defined, one for exact match retrieval and one for case-insensitive retrieval.

-   Exact match query: In Elasticsearch language, this will be a terms query. Terms query allows search for multiple terms. This query retrieves documents which have the exact search term as label or aliases.
-   Exact match lowercase query: Same as Exact match query but with lowercase search terms.

**Examples:**

```bash
   # generate candidates for the cells in the column 'label_clean'
   $ tl --url http://blah.com -Ujohn -Ppwd  generate-candidates -c label_clean --method exact-match < canonical-input.csv

   # clean the column 'label' and then generate candidates for the resulting column 'label_clean' with case insensitive matching
   $ tl --url http://blah.com -Ujohn -Ppwd clean -c label / generate-candidates -c label_clean -i --method exact-match < canonical-input.csv

```

**File Example:**

```
# generate candidates for the canonical file, countries_canonical.csv
$ tl --url http://blah.com -Ujohn -Ppwd  generate-candidates -c clean_labels --method exact-match < countries_canonical.csv > countries_candidates.csv
$ cat countries_candidates.csv

column row label     clean_labels kg_id     kg_label           kg_aliases                 method      retrieval_score
1      0   Buda’pest Budapest     Q1781     Budapest           Buda Pest|Buda-Pest|Buda   exact-match 20.43
1      0   Buda’pest Budapest     Q16467392 Budapest (chanson) ""                         exact-match 12.33
1      0   Buda’pest Budapest     Q55420238 Budapest           Budapest, a song           exact-match 18.2
1      1   Prague    Prague       Q1085     Prague|Praha       Praha|Hlavní město Praha   exact-match 15.39
1      1   Prague    Prague       Q1953283  Prague, Oklahoma   ""                         exact-match 14.44
1      1   Prague    Prague       Q2084234  Prague, Nebraska   ""                         exact-match 13.99
1      1   Prague    Prague       Q5969542  Prague             ""                         exact-match 9.8
1      2   London!   London       Q84       London             London, UK|London, England exact-match 32.31
1      2   London!   London       Q92561    London ON          ""                         exact-match 25.625
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

- [Normalized Levenshtein](https://en.wikipedia.org/wiki/Levenshtein_distance): The levenshtein distance between two words in the minimum number single-character edits needed to change one word into the other. Normalized levenshtein is computed as the levenshtein distance divided by the length of the longest string. The value is between [0.0, 1.0]. The similarity is 1 - normalized distance
- [Jaro Winkler](https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance#Jaro%E2%80%93Winkler_Similarity): Jaro Winkler is a string edit distance designed for short strings. In Jaro Winkler, substitution of 2 close characters is considered less important than the substitution of 2 characters that are far from each other. The value is between [0.0, 1.0]

In future, more string similarity algorithms will be supported
 
**Options:**
- `-c {a,b}`: input columns containing the cells to be compared. The two columns are represented as a comma separated string.
- `-o a`: the string similarity  scores will be outputted in this column. By default, 
column names in the format <col_1>\_<col_2>\_\<algorithm> will be used.
- `-a | --algorithm`: String similarity algorithm to be used. By default, Normalized Levenshtein will be used
- `--lev`: Use Normalized Levenshtein 
- `--jw`: Use Jaro Winkler
- `-i`: case insensitive comparison. Default is case sensitive

#### Implementation
For any input cell value, s and  a candidate c, String similarity outputs a score computed as follows,

<code> stringSimilarity(s, c) := max(similarityFunction(s, l)) ∀ l ∈ { labels(c), aliases(c) } </code> 

For example,
```
 if we have a input cell value,
    s = Mohamed Abdullahi Farmajo
And a Candidate c, such that
    labels(c) = {Mohamed Abdullahi Farmajo},
    aliases(c) = {Maxamed Cabdulaahi Maxamed, Said Abdullahi     Mohamed}

Similarity Scores for each comparison pair is ,

Mohamed Abdullahi Farmajo,Mohamed Abdullahi Farmajo     1.0
Mohamed Abdullahi Farmajo,Maxamed Cabdulaahi Maxamed    0.576
Mohamed Abdullahi Farmajo,Said Abdullahi Mohamed        0.52

The output of String Similarity will be the score 1.0, which is the maximum of {1.0, 0.576, 0.53}
```

**Examples:**

```bash
# compute similarity score for the columns 'clean_labels' and 'kg_label', use Normalized Levenshtein, case sensitive, output column: lev_similarity_score
$ tl string-similarity -c clean_labels,kg_label -a --lev -o lev_similarity_score < countries_candidates.csv

# compute similarity score for the columns 'clean_labels' and 'kg_aliases', use Jaro Winkler, case insensitive
$ tl string-similarity -c clean_labels,kg_aliases  -a --jw -i countries_candidates.csv
```

**File Example:**
```
# compute string similarity between the columns 'clean_labels' and 'kg_label', using case sensitive Normalized Levemshtein 
# for the file countries_candidates.csv, exclude columns 'label','method' and 'retrieval_score' while printing
$ tl string-similarity -c clean_labels,kg_label -a --lev -o lev_similarity_score < countries_candidates.csv | mlr --opprint cut -f label,method,retrieval_score -x countries_ss_features.csv

column row clean_labels kg_id     kg_label           kg_aliases                 lev_similarity_score
1      0   Budapest     Q1781     Budapest           Buda Pest|Buda-Pest|Buda   1.0
1      0   Budapest     Q16467392 Budapest (chanson) -                          0.44
1      0   Budapest     Q55420238 Budapest           Budapest, a song           1.0
1      1   Prague       Q1085     Prague|Praha       Praha|Hlavní město Praha   1.0
1      1   Prague       Q1953283  Prague, Oklahoma   -                          0.375
1      1   Prague       Q2084234  Prague, Nebraska   -                          0.375
1      1   Prague       Q5969542  Prague             -                          1.0
1      2   London       Q84       London             London, UK|London, England 1.0
1      2   London       Q92561    London ON          -                          0.66
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
# merge the columns 'kg_label' and 'kg_aliases' in the countries_candidates.csv and store the ouput in the column 'kg_label_aliases' and keep duplicates
$ tl merge-columns -c kg_label,kg_aliases -o kg_label_aliases --remove-duplicates no countries_candidates.csv

# merge the columns 'kg_label' and 'kg_aliases' in the countries_candidates.csv and store the ouput in the column 'kg_label_aliases' and remove duplicates
$ tl merge-columns -c kg_label,kg_aliases -o kg_label_aliases --remove-duplicates yes < countries_candidates.csv
``` 

**File Example:**
```
$ tl merge-columns -c kg_label,kg_aliases -o kg_label_aliases --remove-duplicates yes < countries_candidates.csv

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
Note that the column containing the retrieval method names is `method`, added by the [generate-candidates](#command_generate-candidates) command.

**Options:**
- `-c a`: column name which has the retrieval scores. Default is `retrieval_score`
- `-o a`: the output column name where the normalized scores will be stored. Default is input column name appended with the suffix `_normalized`
- `-w|--weights`: a comma string of the format `<retrieval_method_1}:<weight_1>, <retrieval_method_2:<weight_2>,...>`
 specifying the weights for each retrieval method.By default, all retrieval method weights are set to 1.0

#### Implementation
The `normalize-scores` command will add up the retrieval scores for candidates generated by a retrieval method, 
compute the average and then divide the retrieval scores by that average for each input column.

```
For each retrieval method 'm' and the candidate set 'C' for a column,

average(m) := sum(retrievalScore(C)) / |C|

Then, for all candidates 'c' generated by retrieval method 'm',

normalizedRetrievalScore(c) := retrievalScore(c) / average(m) * weight(m)
 
Where 'weight(m)' is specified by users, defaulting to '1.0'
```

**Examples:**
```bash
# compute normalized scores with default options
$ tl normalize-scores < countries_candidates.csv > countries_candidates_normalized.csv

# compute normalized scores the column 'es_score', output in the column 'normalized_es_scores' with specified weights
$ tl normalize-scores -c es_score -o normalized_es_scores -w 'es_method_1:3.4,es_method_2:0.92' countries_candidates.csv
```

**File Example:**
```bash
# compute normalized scores the column 'retrieval_score', output in the column 'normalized_retrieval_scores' with specified weights
$ tl normalize-scores -c retrieval_score -o normalized_retrieval_scores -w 'exact-match:2.25' < countries_candidates.csv > mlr --opprint cut -f kg_label,kg_aliases -x

column row label     clean_labels kg_id     method      retrieval_score normalized_retrieval_scores
1      0   Buda’pest Budapest     Q1781     exact-match 20.43           2.545657324                
1      0   Buda’pest Budapest     Q16467392 exact-match 12.33           1.536365874                
1      0   Buda’pest Budapest     Q55420238 exact-match 18.2            2.305662104                
1      1   Prague    Prague       Q1085     exact-match 15.39           1.868078301                
1      1   Prague    Prague       Q1953283  exact-match 14.44           1.747478822                
1      1   Prague    Prague       Q2084234  exact-match 13.99           1.63664015                 
1      1   Prague    Prague       Q5969542  exact-match 9.8             1.079229122                
1      2   London!   London       Q84       exact-match 32.31           3.219790359                
1      2   London!   London       Q92561    exact-match 25.625          1.990377147                
```

## Ranking Candidate Commands
Ranking Candidate suite of commands rank the candidate for each input cell. All Ranking Candidate commands takes as input a file in [feature](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.meysv8c8z2mt)
format and output a file in [ranking score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr)
format.

<a name="command_combine-linearly" />

### [`combine-linearly`](#command_combine-linearly)` [OPTIONS]`

Linearly combines the two or more columns with scores  for candidate knowledge graph objects
for each input cell value. Takes as input `weights` for columns being combined to adjust influence. 
The candidate with the highest score is ranked highest, ties are broken alphabetically.

**Options:**
- `c {a,b,...}`: columns which have scores to be linearly combined. Multiple columns are represented as a comma separated string.
- `-w | --weights {w1,w2,..} `: a comma separated string representing weights for each score column. Default weight for each score column is `1.0`. 
The order of weights correspond to the order specified in the `-c` option. In case of a mismatch in number of values in the `-c` and `-w` option, default weight of `1.0` is set to the missing weights.
- `-o a`: the output column name where the linearly combined scores will be stored.

#### Implementation
Multiply the values in the input columns with their corresponding weights and adds them up to get a ranking score for each candidate. 

For each candidate `c` and the set of score columns `S`,

<code> rankingScore(c) := ∑(value(s) * weight(s)) ∀ s ∈ S </code>

**Examples:**
```bash
# linearly combine the columns 'normalized_score' and 'levenshtein_similarity' with respective weights as '1.5' and '4.2'
$ tl combine_linearly -c normalized_score,levenshtein_similarity -w 1.5,4.2 -o ranking_score < countries_features.csv > countries_features_ranked.csv
```

**File Examples:**
```bash
# consider the features file, countries_features.csv (some columns might be missing for simplicity)
$ cat countries_features.csv

column row clean_labels kg_id     kg_label           kg_aliases                 levenshtein_similarity normalized_score
1      0   Budapest     Q1781     Budapest           Buda Pest|Buda-Pest|Buda   1                      2.54565732
1      0   Budapest     Q16467392 Budapest (chanson) -                          0.44                   1.53636587
1      0   Budapest     Q55420238 Budapest           Budapest, a song           1                      2.3056621
1      1   Prague       Q1085     Prague|Praha       Praha|Hlavní město Praha   1                      1.8680783
1      1   Prague       Q1953283  Prague, Oklahoma   -                          0.375                  1.74747882
1      1   Prague       Q2084234  Prague, Nebraska   -                          0.375                  1.63664015
1      1   Prague       Q5969542  Prague             -                          1                      1.07922912
1      2   London       Q84       London             London, UK|London, England 1                      3.21979036
1      2   London       Q92561    London ON          -                          0.66                   1.99037715

# linearly combine the columns 'normalized_score' and 'levenshtein_similarity' with respective weights as '1.5' and '4.2'
$ tl combine_linearly -c normalized_score,levenshtein_similarity -w 1.5,4.2 -o ranking_score < countries_features.csv > countries_features_ranked.csv
$ cat countries_features_ranked.csv

column row clean_labels kg_id     kg_label           kg_aliases                 levenshtein_similarity normalized_score ranking_score
1      0   Budapest     Q1781     Budapest           Buda Pest|Buda-Pest|Buda   1                      2.54565732       8.01848598
1      0   Budapest     Q16467392 Budapest (chanson) -                          0.44                   1.53636587       4.152548805
1      0   Budapest     Q55420238 Budapest           Budapest, a song           1                      2.3056621        7.65849315
1      1   Prague       Q1085     Prague|Praha       Praha|Hlavní město Praha   1                      1.8680783        7.00211745
1      1   Prague       Q1953283  Prague, Oklahoma   -                          0.375                  1.74747882       4.19621823
1      1   Prague       Q2084234  Prague, Nebraska   -                          0.375                  1.63664015       4.029960225
1      1   Prague       Q5969542  Prague             -                          1                      1.07922912       5.81884368
1      2   London       Q84       London             London, UK|London, England 1                      3.21979036       9.02968554
1      2   London       Q92561    London ON          -                          0.66                   1.99037715       5.757565725
```

## Commands on Ranking Score File

[Ranking Score](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.knsxbhi3xqdr) files have a column which ranks 
the candidates for each input cell.

<a name="command_outputter" />

### [`outputter`](#command_outputter)` [OPTIONS]`

The `outputter` command outputs the top `k` candidates from a sorted list of ranking scores, 
as linked kmnowledge graph object for an input cell. This module takes as input a [Input](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.7pj9afmz3h1t)
 file and a file in Ranking Score format and outputs a file in [Output](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.6rlemqh56vyi) format.

**Options:**
- `-f {path}`: input file path.
- `-c a`:	column name with ranking scores.
- `-k {number}`: desired number of output candidates per input cell.Defaut is `k=1`. Multiple values are represented by `|` separated string

#### Implementation
Join the input file and the ranking score file based on column and row indices to produce an output file. In case of more than one  preferred label
for a candidate, the first label is picked from the `|` separated string. The corresponsing values in each output column have the same index, in case of `k > 1`

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
Hungary        Buda’pest    49         Q1781|Q55420238    Budapest|Budapest     8.01|7.65
Czech Republic Prague       420        Q1085|Q5969542     Prague|Prague         7.00|5.88
United Kingdom London!      44         Q84|Q92561         London|London ON      9.02|5.75
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
