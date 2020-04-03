import pandas as pd
from tl.candidate_generation.get_exact_matches import ExactMatches
from SPARQLWrapper import SPARQLWrapper, JSON
import json
import traceback


class ConvertISWC(object):
    def __init__(self):
        self.es_url = 'http://kg2018a.isi.edu:9200'
        self.es_index = 'wikidata_dbpedia_joined_3'
        self.es_index_1 = 'wiki_labels_aliases_1'
        self.db_sparql_url = 'http://dbpedia.org/sparql'
        self.wiki_sparql_url = 'http://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql'
        self.em = ExactMatches(self.es_url, self.es_index_1)

    def convert_iswc_gt(self, output_directory, file_path=None, df=None, dburi_to_qnode_path=None):
        """
        converts the ISWC Ground Truth file to TL Ground Truth file. This is a one time operation.

        Args:
            output_directory: output directory where the files in TL GT will be created
            file_path: input iswc gt file
            df: or dataframe
            dburi_to_qnode_path: a dictionary to record dburit to qnode map

        Returns:

        """
        if file_path:
            df = pd.read_csv(file_path, header=None, names=['file', 'column', 'row', 'db_uris'], dtype=object)
        print('Total number of rows in the input file: {}'.format(len(df)))

        db_uri_strs = df['db_uris'].values
        db_uris_list = [x.split(' ') for x in db_uri_strs]
        db_uris_all = set()

        for x in db_uris_list:
            db_uris_all.update(x)

        dburi_to_qnode = {}
        if dburi_to_qnode_path:
            o = open(dburi_to_qnode_path)
            dburi_to_qnode = json.load(o)

        db_uris = [x for x in db_uris_all if x not in dburi_to_qnode]

        print('Total number of db uris to be converted to qnodes:{}'.format(len(db_uris)))

        counter = 0
        try:
            while (db_uris):
                batch = db_uris[:500]
                query = {"_source": ["dbpedia_urls"],
                         "query": {
                             "terms": {
                                 "dbpedia_urls.keyword": batch
                             }
                         }
                         }
                hits = self.em.es.search_es(query)

                if hits:
                    dburi_to_qnode.update(self.convert_es_docs_to_dict(hits))

                print('queried {} uris'.format(counter))
                counter += len(batch)
                db_uris = db_uris[500:]
        except:
            open(dburi_to_qnode_path, 'w').write(json.dumps(dburi_to_qnode))
            self.convert_iswc_gt(output_directory, file_path=file_path, df=df, dburi_to_qnode_path=dburi_to_qnode_path)

        df['kg_id'] = df['db_uris'].map(lambda x: ConvertISWC.find_qnode(x, dburi_to_qnode))

        print('Number of rows which have no qnode: {}'.format(len(df[df['kg_id'] == 'None'])))

        print('Running some SPARQL queries, here we go... ')

        remaining_db_uris = df[df['kg_id'] == 'None']['db_uris'].values

        print('Running sparql queries on {} db uris'.format(len(remaining_db_uris)))

        db_uris_list = [x.split(' ') for x in remaining_db_uris]
        db_uris = set()

        for x in db_uris_list:
            db_uris.update(x)

        db_uris = list(db_uris)

        while (db_uris):
            try:
                remaining_uris = db_uris[:100]
                dburi_to_qnode_local = self.qnode_from_sparql(remaining_uris)
                dburi_to_qnode.update(dburi_to_qnode_local)
                db_uris = db_uris[100:]
            except Exception as e:
                open(dburi_to_qnode_path, 'w').write(json.dumps(dburi_to_qnode))
                print(e)

        open(dburi_to_qnode_path, 'w').write(json.dumps(dburi_to_qnode))

        df['kg_id'] = df['db_uris'].map(lambda x: ConvertISWC.find_qnode(x, dburi_to_qnode))

        print('Number of dbpedia urls which have no corresponding qnodes: {}'.format(len(df[df['kg_id'] == 'None'])))

        df = df[df['kg_id'] != 'None']
        self.write_converted_gt_file(output_directory, df)
        print('Done!!!')

    @staticmethod
    def find_qnode(db_uri_str, dburi_qnode_dict):
        dburis = db_uri_str.split(' ')
        qnodes = []
        for db_uri in dburis:
            if db_uri in dburi_qnode_dict and dburi_qnode_dict[db_uri]:
                qnodes.append(dburi_qnode_dict[db_uri])
                break
        return ''.join(qnodes) if len(qnodes) > 0 else "None"

    def qnode_from_sparql(self, uris):
        dburi_to_qnode = self.qnode_from_uri_sameas(uris)
        remaining_uris = [x for x in uris if x not in dburi_to_qnode]
        dburi_to_qnode.update(self.qnode_from_uri_wiki(remaining_uris, dburi_to_qnode))
        return dburi_to_qnode

    def qnode_from_uri_sameas(self, uris):

        sparqldb = SPARQLWrapper(self.db_sparql_url)
        dburi_to_qnode = {}

        ustr = " ".join(["(<{}>)".format(uri) for uri in uris])
        sparqldb.setQuery("""select ?item ?qnode where 
                        {{VALUES (?item) {{ {} }} ?item <http://www.w3.org/2002/07/owl#sameAs> ?qnode .
                        FILTER (SUBSTR(str(?qnode),1, 24) = "http://www.wikidata.org/")
                        }}""".format(ustr))

        sparqldb.setReturnFormat(JSON)
        results = sparqldb.query().convert()

        uri_to_wiki = {}
        for result in results["results"]["bindings"]:
            uri_to_wiki[result['item']['value']] = result['qnode']['value'].split('/')[-1]

        for uri in uris:
            if uri in uri_to_wiki and uri_to_wiki[uri] is not None:
                dburi_to_qnode[uri] = uri_to_wiki[uri]

        return dburi_to_qnode

    def qnode_from_uri_wiki(self, uris, dburi_to_qnode):
        if not uris:
            return []
        wiki_to_uri = {}
        for uri in uris:
            wiki_to_uri[uri.replace('http://dbpedia.org/resource/', 'https://en.wikipedia.org/wiki/')] = uri
        wlinks = list(wiki_to_uri)
        wikistr = ' '.join(["(<{}>)".format(wlink) for wlink in wlinks])
        sparql = SPARQLWrapper(self.wiki_sparql_url)
        sparql.setQuery("""
            SELECT ?item ?article WHERE {{
                VALUES (?article) {{ {} }} 
                ?article schema:about ?item .
            }} 
            """.format(wikistr))

        sparql.setReturnFormat(JSON)

        results = sparql.query().convert()['results']['bindings']

        for result in results:
            wlink = result['article']['value']
            qnode = result['item']['value'].split('/')[-1]
            dburi_to_qnode[wiki_to_uri[wlink]] = qnode

        return dburi_to_qnode

    @staticmethod
    def convert_es_docs_to_dict(es_docs):
        dburi_to_qnode_subset_dict = {}
        for es_doc in es_docs:
            qnode = es_doc['_id']
            dbpedia_urls = es_doc['_source'].get('dbpedia_urls', [])
            for du in dbpedia_urls:
                dburi_to_qnode_subset_dict[du] = qnode
        return dburi_to_qnode_subset_dict

    @staticmethod
    def write_converted_gt_file(output_directory, df):
        grouped = df.groupby(by=['file'])
        for i, gdf in grouped:
            gdf.drop(columns=["file", "db_uris"], inplace=True)
            gdf = gdf[gdf['kg_id'] != 'None']
            gdf.to_csv('{}/{}'.format(output_directory, i), index=False)

    @staticmethod
    def create_gt_es_to_dict(es_docs):
        local_dict = {}
        for es_doc in es_docs:
            qnode = es_doc['_id']
            labels = es_doc['_source'].get('labels', [])
            aliases = es_doc['_source'].get('aliases', [])
            _label = ""
            if labels:
                _label = labels[0]
            if aliases and _label == "":
                _label = aliases[0]
            local_dict[qnode] = _label

        return local_dict

    def add_labels(self, df, f):
        all_qnodes = list(df['kg_id'].unique())
        qnode_to_label_dict = {}
        while (all_qnodes):
            try:
                remaining_qnodes = all_qnodes[:500]
                local_dict = self.labels_for_qnodes(remaining_qnodes)
                if local_dict:
                    qnode_to_label_dict.update(local_dict)
                all_qnodes = all_qnodes[500:]
            except Exception as e:

                traceback.print_exc()
                print(f)
                raise

        df['kg_label'] = df['kg_id'].map(lambda x: qnode_to_label_dict.get(x, ''))
        return df

    def labels_for_qnodes(self, qnodes):
        query = {
            "query": {
                "ids": {
                    "values": qnodes
                }
            },
            "size": 500
        }
        hits = self.em.es.search_es(query)

        if hits:
            return ConvertISWC.create_gt_es_to_dict(hits)
