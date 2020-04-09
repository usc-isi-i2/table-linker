# [« Home](https://github.com/usc-isi-i2/table-linker) / Table Linker Utility Commands

  This document describes the [utility commands](#command_utility-commands) for the <code>Table Linker (tl)</code> system. 

### `Usage: tl [OPTIONS] COMMAND`

**Table of Contents:**
- [`build-elasticsearch-file`](#command_build-elasticseach-file): builds a json lines file and a mapping file to support retrieval of candidates.
- [`load-elasticsearch-index`](#command_load-elasticsearch-index): loads a json lines file to elasticsearch index
- [`convert-iswc-gt`](#command_convert-iswc-gt): converts the ISWC Ground Truth file to [TL Ground Truth](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.63n3hyogxr1e) file
- [`metrics`](#command_metrics): computes the `precision`, `recall` and `f1 score` for the `tl` pipeline

**Options:**
- `-e, --examples` -- Print some examples and exit
- `-h, --help` -- Print this help message and exit
- `-v, --version` -- Print the version info and exit
- `--url {url}`:  URL of the ElasticSearch server.
- `--index {name}`: Name of the elasticsearch index
- `-U {user id}`: the user id for authenticating to the ElasticSearch index.
- `-P {password}`: the password for authenticating to the ElasticSearch index.


<a name="command_utility-commands" />

## [`Utility Commands`](#command_utility-commands)

utility commands for `tl`

<a name="command_build-elasticseach-file" />

### [`build-elasticsearch-file`](#command_build-elasticseach-file)
builds a json lines file and a mapping file to support retrieval of candidates. 
This command takes as input an Edges file in KGTK format, which must be sorted by subject and property so that this script can generate the JSON file for the index in a streaming fashion.

Note: as described, this tool builds an index of labels and aliases, and does not index any other information about nodes. A future implementation will index additional information about nodes.

**Options:**

- `--labels {a,b,...}`: The names of properties in the Edges file that contain the node labels used for building the index.
- `--aliases {a,b,...}`: The names of properties in the Edges file that contain the node aliases or alternate labels used for building the index.
- `--mapping {path}`: The output mapping file path for custom mapping for the Elasticsearch index.

**Example:**

Consider the following three-stooges Edges file in KGTK format. 
It uses two properties to define labels for nodes, `preflabel` and `label`, 
and one property to define aliases, `alias`.
```bash

node1 label     node2
N1    isa       Person
N1    preflabel “Moe”
N1    label     “‘Moeh’@fr”
N2    alias     “Lawrence|Lorenzo”
N2    isa       Person
N2    preflabel “Larry”
N3    isa       Person
N3    preflabel “Curly”
```

The following command will build a json line file and a mapping file using the properties `preflabel` and `label` to define the labels and `alias` to
 define the aliases of nodes.

```
$ tl  build-elasticsearch-file --labels preflabel,label --aliases alias \ 
 --mapping nodes_mapping.json nodes.tsv
```
This command will map nodes as follows:

- N1: `labels: “Moe”, “Moeh”`
- N2: `labels: “Larry”, aliases:“Lawrence”, “Lorenzo”` 
- N3: `labels: “Curly”`

The following command will build a json line file and a mapping file using the properties `label` to define the labels and `alias` to define
the aliases of nodes.

```
$ tl  build-elasticsearch-file --labels label --aliases alias \
--mapping nodes_mapping.json nodes.json
```
This command will map nodes as follows:

- N1: `labels: “Moeh”`
- N2: `aliases: “Lawrence”, “Lorenzo”` 
- N3: ` `
	
**Implementation**

The algorithm uses the properties listed in the labels option to collect the set of strings to be indexed. The following cleaning operations are made on each value: 

- When the value contains |-separated values, these will be split into multiple phrases, and each one will be indexed separately. For example, if the value is  “’Curly’@en|’Moe’@sp”, it is split into the set containing “’Curly’@en” and “’Moe’@sp”
- If a value contains a language tag, e.g,  “’Curly’@en”, the language tag is dropped and the value becomes “Curly”.

The set of all values for each of the label properties specified in the `labels` option are collected into one set, and indexed as the `labels` of the node.
Similar operation is done for all values specified in the`aliases` option.

The command will follow these steps,
- The Elasticsearch document format is JSON, so convert the input KGTK file to JSON documents with the following fields,
   - `id`: the identifier for the node. This will be computed from the column `node1` in the input KGTK file.
   - `labels`: a list of values specified using the `--labels` option.
   - `aliases`: a list of aliases specified using the `--aliases` option.
- Build a mapping file as defined in the next section.

**Elasticsearch Index Mapping**

The mapping of the  fields `id`, `labels` and `aliases` stored in the Elasticsearch index is as follows,
- `id`: stored with default Elasticsearch analyzer
- `id.keyword`: stored as is for exact matches
- `labels`: default elasticsearch analyzer
- `labels.keyword`: stored as is for exact matches
- `labels.keyword_lower`: stored lowercase for exact matches
- `aliases`: default with elasticsearch analyzer
- `aliases.keyword`: stored as is for exact matches
- `aliases.keyword_lower`: stored lowercase for exact matches

The mapping file is a JSON document. A sample mapping file is [here](tl/helper_files/kg_labels_aliases_mapping.json)

<a name="command_load-elasticsearch-index" />

### [`load-elasticsearch-index`](#command_load-elasticsearch-index)

loads a jsonlines file to Elasticsearch index.

**Options:**
- `--mapping {path}`: The mapping file path used to create custom mapping for the Elasticsearch index.

**Examples:**
```bash
# load the file docs.jl to the Elasticsearch index docs_1, create index first using specified docs_1_mapping.json
$ tl -U smith -P my_pwd --url http:/bah.com --index docs_1 load-elasticsearch-index \
--mapping docs_1_mapping.json docs.jl

# same as above, but don't create index using the mapping file
$ tl -U smith -P my_pwd --url http:/bah.com --index docs_1 load-elasticsearch-index docs.jl 
```
**Implementation**

This command has the following steps,
- Check if the index to be created already exists.
   - if the index exists, do nothing and move to the next step.
   - if the index does not exist, create the index first with the mapping file, if specified, otherwise with default mapping. Then move to the next step.
- Batch load the documents into the Elasticsearch index.  

<a name="command_convert-iswc-gt" />

### [`convert-iswc-gt`](#command_convert-iswc-gt) 

converts the ISWC Ground Truth file to [TL Ground Truth](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.63n3hyogxr1e) file.
This is a one time operation, listed here for completion.

**Options:**
 - `-d`: output directory where the files in TL GT will be created
 
 This command uses the following constants,
 - `dbpedia_sparql_url`: "http://dbpedia.org/sparql"
 - `elasticsearch_url`: "http://kg2018a.isi.edu:9200"
 - `elasticsearch_index`: "wikidata_dbpedia_joined_3" 
 - `wikidata_sparql_url`: "http://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql"

**Examples**
```
tl convert-iswc-gt -d my-output-path iswc_gt.csv 
```

**File Example:**

```bash
# consider the ISWC GT File
$ cat iswc_gt.csv

v15_1   1   5   http://dbpedia.org/resource/Sachin_Tendulkar http://dbpedia.org/resource/Sachin_r_Tendulkar 
v15_1   2   5   http://dbpedia.org/resource/Virat_Kohli
v15_1   3   5   http://dbpedia.org/resource/Rishabh_Pant
v15_1   4   5   http://dbpedia.org/resource/Ishant_Sharma
v15_3   0   1   http://dbpedia.org/resource/Royal_Challengers_Bangalore
v15_3   1   1   http://dbpedia.org/resource/Mumbai_Indians

$ tl convert-iswc-gt -d my-output-path ../o_path iswc_gt.csv 
$ cat ../o_path/*csv 

v15_1.csv
column  row     kg_id
1       5       Q9488
2       5       Q213854 
3       5       Q21622311
4       5       Q3522062

v15_3.csv
column  row     kg_id
0       1       Q1156897
1       1       Q1195237

```

**Implementation**

The ISWC GT files have four columns with no column headers. The columns in order are:
- `file name`: name of the input file for which the current row has GT KG id
- `column`: zero based column index in the input file
- `row`: zero based row index in the input file
- `dbpedia urls`: a `space` separated string of dbpedia urls as correct urls linking the input cell

This command has the following steps in order:
- split the dbpedia urls in the ISWC ground truth file by space
- for each of the dbpedia urls, do the following,
    - run a term query to the elasticsearch index `wikidata_dbpedia_joined_3` and the field `dbpedia_urls.keyword`.
     If a match is found, use the `Qnode` from the returned document and record the
     dbpedia to Qnode mapping. If there is no match, move to the next step.
    - run a sparql query to dbpedia sparql endpoint to fetch the relevant Qnode. This query gets the `<http://www.w3.org/2002/07/owl#sameAs>` links for the dbpedia url, filtering in the Wikidata Qnodes.
     If a match is found, use the `Qnode` from the returned result and record the
     dbpedia to Qnode mapping. If there is no match, move to the next step.
     Example query,
     ```bash
     select ?item ?qnode where {
        VALUES (?item) { (<http://dbpedia.org/resource/Virat_Kohli>) } 
        ?item <http://www.w3.org/2002/07/owl#sameAs> ?qnode .
            FILTER (SUBSTR(str(?qnode),1, 24) = "http://www.wikidata.org/") 
     ```
    -convert the dbpedia url to wikipedia url by replacing `http://dbpedia.org/resource/` with `https://en.wikipedia.org/wiki/`.
    Run a sparql query to wikidata sparql endpoint.  If a match is found, use the `Qnode` from the returned result and record the
    dbpedia to Qnode mapping. If there is no match, move to the next step.
    Example query,
    ```bash
    SELECT ?item ?article WHERE {
        VALUES (?article) { (<https://en.wikipedia.org/wiki/Virat_Kohli>) } 
        ?article schema:about ?item .                 
        }            
    ``` 
      
- output a file with the name `file name`  from the ISWC file in the output directory as specified by the option `-d`. The output file has the following
columns,
    - `column`: the column index from the ISWC GT file.
    - `row`: the row index from the ISWC GT file
    - `kg_id`: a `|` separated string of Qnodes, corresponding to the dbpedia urls.

If the mapping from a dbpedia url to Qnode is not found, delete that row from the TL GT file.

<a name="command_metrics" />

### [`metrics`](#command_metrics)

computes the `precision`, `recall` and `f1 score` for the `tl` pipeline. Takes as input a [Evaluation File](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.vurz5diqkuf7)
file  and output a file in [Metrics File](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.if3pcq7n8wz6) format.

**Options:**
- `-c a`:  column name with ranking scores
- `-k {number}: default, k=1. recall is calculated considering candidates with rank upto k
- `--tag: a tag to use in the output file to identify the results of running the given pipeline

**Examples:**

```bash
$ tl metrics -c ranking_score <  cities_evaluation.csv > cities_metrics.csv

# same as above but calculate recall at 5
$ tl metrics -c ranking_score -k 5 <  cities_evaluation.csv > cities_metrics.csv

```

**Implementation**

Discard the rows with `evaluation_label=0`. Sort all the candidates for an input cell by ranking score, breaking ties alphabetically.
If the top ranked candidate has `evalution_label=1`, it is counted as true positive, otherwise false positive.

Compute `precision`, `recall` and `f1 score`

