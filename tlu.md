# [« Home](https://github.com/usc-isi-i2/table-linker) / Table Linker Utility Commands

  This document describes the [utility commands](#command_utility-commands) for the <code>Table Linker (tl)</code> system. 

### `Usage: tl [OPTIONS] COMMAND`

**Table of Contents:**
- [`build-elasticsearch-index`](#command_build-elasticseach-index): builds an Elasticsearch index to support retrieval of candidates.
- [`convert-iswc-gt`](#command_convert-iswc-gt): converts the ISWC Ground Truth file to [TL Ground Truth](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.63n3hyogxr1e) file


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

<a name="command_build-elasticseach-index" />

### [`build-elasticsearch-index`](#command_build-elasticseach-index)
builds an Elasticsearch index to support retrieval of candidates. 
This command takes as input an Edges file in KGTK format, a reference to an ElasticSearch service
 and the name of the index to be created. 
 The Edges file must be sorted by subject and property so that this script can generate the JSON file for the index in a streaming fashion.

Note: as described, this tool builds an index of labels and aliases, and does not index any other information about nodes. A future implementation will index additional information about nodes.

**Options:**

- `--labels {a,b,...}`: The names of properties in the Edges file that contain the node labels used for building the index.
- `--aliases {a,b,...}`: The names of properties in the Edges file that contain the node aliases or alternate labels used for building the index.
- `--mapping {path}`: The mapping file path used to create custom mapping for the Elasticsearch index.

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

The following command will build an index called `kg_labels_aliases_1` using the properties `preflabel` and `label` to define the labels and `alias` to
 define the aliases of nodes.

```
$ tl -U smith -P my_pwd --url http:/bah.com --index kg_labels_aliases_1 build-elasticsearch-index --labels preflabel,label --aliases alias \ 
nodes.tsv
```
This command will map nodes as follows:

- N1: `labels: “Moe”, “Moeh”`
- N2: `labels: “Larry”, aliases:“Lawrence”, “Lorenzo”` 
- N3: `labels: “Curly”`

The following command will build an index called `kg_labels_aliases_2` using the properties `label` to define the labels and `alias` to define
the aliases of nodes and use a custom mapping file.

```
$ tl  -U smith -P my_pwd --url http:/bah.com --index kg_labels_aliases_2  build-elasticsearch-index --labels label --aliases alias \
--mapping my_index_mapping.json nodes.json
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

The command will follow these steps before loading documents into the Elasticsearch index,
- Check if index to be created already exists.
   - if the index exists, do nothing move to next step.
   - if the index does not exist, create the index first with mapping file, if specified, otherwise with default mapping. Then move to next step.
- The Elasticsearch document format is JSON, so convert the input KGTK file to JSON documents with the following fields,
   - `id`: the identifier for the node. This will computed from the the column `node1` in the input KGTK file.
   - `labels`: a list of values specified using the `--labels` option.
   - `aliases`: a list of aliases specified using the `--aliases` option.
- Batch load the documents into the Elasticsearch index.  

**Elasticsearch Index Mapping**

The mapping of the  fields `id`, `labels` and `aliases` stored in the Elasticsearch index is as follows,
- `id`: stored with default Elasticsearch analyzer
- `id.keyword`: stored as is for exact matches
- `labels`: default elasticsearch analyzer
- `labels.keyword`: stored as is for exact matches
- `labels.keyword_lower`: stored lowercased for exact matches
- `aliases`: default with elasticsearch analyzer
- `aliases.keyword`: stored as is for exact matches
- `aliases.keyword_lower`: stored lowercased for exact matches

The mapping file is a JSON document. Mapping file for the index `kg_labels_aliases_1` is [here](tl/helper_files/kg_labels_aliases_mapping.json)

<a name="command_command_convert-iswc-gt" />

### [`convert-iswc-gt`](#command_convert-iswc-gt) 

converts the ISWC Ground Truth file to [TL Ground Truth](https://docs.google.com/document/d/1eYoS47dCryh8XKjWIey7khikkbggvc6IUkdUGrQ9pEQ/edit#heading=h.63n3hyogxr1e) file

**Options:**
- `--dbpedia-sparql-url`: dbpedia sparql url. Default is `http://dbpedia.org/sparql` 
- `-d`: output directory where the files in TL GT will be created

**Examples**
```
tl -U smith -P my_pwd --url http:/bah.com --index wikidata_dbpedia_joined \
 convert-iswc-gt --dbpedia-sparql-url http://dbpedia.org/sparql -d my-output-path iswc_gt.csv 
```
**Implementation**

The ISWC GT files have four columns with no column headers. The columns in order contain:
- `file name`: name of the input file for which the current row has GT KG id
- `column`: zero based column index in the input file
- `row`: zero based row index in the input file
- `dbpedia urls`: a `space` separated string of dbpedia urls as correct urls linking the input cell

This command has the following steps in order:
- split the dbpedia urls in the ISWC ground truth file by space
- for each of the dbpedia urls, do the following,
    - run an exact match query to the elasticsearch index. If a match is found, use the `Qnode` from the returned document and record the
     dbpedia to Qnode mapping. If there is no match, move to the next step.
    - run a sparql query to dbpedia sparql endpoint to fetch the relevant Qnode. If a match is found, use the `Qnode` from the returned result and record the
     dbpedia to Qnode mapping. If there is no match, move to the next step. 
- output a file with the name `file name`  from the ISWC file in the output directory as specified by the option `-d`. The output file has the following
columns,
    - `column`: the column index from the ISWC GT file.
    - `row`: the row index forom the ISWC GT file
    - `kg_id`: a `|` separated string of Qnodes, corresponding to the dbpedia urls.



## Score `tl` Pipeline
