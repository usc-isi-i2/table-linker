ngram_query = {
    "query": {
        "function_score": {
            "query": {
                "bool": {
                    "must": [],
                    "must_not": [
                        {
                            "terms": {
                                "descriptions.en.keyword_lower": [
                                    "wikimedia disambiguation page",
                                    "wikimedia category",
                                    "wikimedia kml file",
                                    "wikimedia list article",
                                    "wikimedia template",
                                    "wikimedia module",
                                    "wikinews article",
                                    "wikimedia template page"
                                ]
                            }
                        }
                    ]
                }
            },
            "boost": 1,
            "field_value_factor": {
                "field": "pagerank",
                "modifier": "none",
                "factor": 10000
            },
            "boost_mode": "multiply"
        }
    }
}
