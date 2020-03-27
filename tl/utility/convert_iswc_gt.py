import pandas as pd
from tl.candidate_generation.get_exact_matches import ExactMatches
from SPARQLWrapper import SPARQLWrapper, JSON
import json


class ConvertISWC(object):
    def __init__(self):
        self.es_url = 'http://kg2018a.isi.edu:9200'
        self.es_index = 'wikidata_dbpedia_joined_3'
        self.db_sparql_url = 'http://dbpedia.org/sparql'
        self.wiki_sparql_url = 'http://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql'
        self.em = ExactMatches(self.es_url, self.es_index)

    def convert_iswc_gt(self, output_directory, file_path=None, df=None, dburi_to_qnode_path=None):
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
        while (db_uris):
            batch = db_uris[:500]
            query = {"_source": ["dbpedia_urls"],
                     "query": {
                         "terms": {
                             "dbpedia_urls.keyword": batch
                         }
                     }
                     }
            hits = self.em.search_es(query)

            if hits:
                dburi_to_qnode.update(self.convert_es_docs_to_dict(hits))

            print('queried {} uris'.format(counter))
            counter += len(batch)
            db_uris = db_uris[500:]

        df['kg_id'] = df['db_uris'].map(lambda x: ConvertISWC.find_qnode(x, dburi_to_qnode))

        print('Number of db uris which could not be converted to qnodes: {}'.format(len(df[df['kg_id'] == 'None'])))

        print('Running some SPARQL queries, here we go... ')

        remaining_db_uris = df[df['kg_id'] == 'None']['db_uris'].values
        db_uris_list = [x.split(' ') for x in remaining_db_uris]
        db_uris = set()

        for x in db_uris_list:
            db_uris.update(x)

        db_uris = list(db_uris)
        while (db_uris):
            remaining_uris = db_uris[:50]
            dburi_to_qnode = self.qnode_from_sparql(remaining_uris, dburi_to_qnode)
            db_uris = db_uris[50:]

        open('{}_{}'.format(file_path.split('/')[-1], 'dburi_to_qnode.json'), 'w').write(json.dumps(dburi_to_qnode))

        df['kg_id'] = df['db_uris'].map(lambda x: ConvertISWC.find_qnode(x, dburi_to_qnode))

        print('Number of dbpedia urls which have to corresponding qnode: {}'.format(len(df[df['kg_id'] == 'None'])))

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

    def qnode_from_sparql(self, uris, dburi_to_qnode):
        dburi_to_qnode = self.qnode_from_uri_sameas(uris, dburi_to_qnode)
        remaining_uris = [x for x in uris if x not in dburi_to_qnode]
        dburi_to_qnode = self.qnode_from_uri_wiki(remaining_uris, dburi_to_qnode)
        return dburi_to_qnode

    def qnode_from_uri_sameas(self, uris, dburi_to_qnode):

        sparqldb = SPARQLWrapper(self.db_sparql_url)

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
            gdf.to_csv('{}/{}'.format(output_directory, i), index=False)


# c = ConvertISWC()
# c.convert_iswc_gt('/Users/amandeep/Github/table-linker/data/CEA_Round2_gt.csv')
