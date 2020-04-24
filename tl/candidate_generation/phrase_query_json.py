query = {
    "query": {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": "",
                        "type": "most_fields",
                        "fields": [
                            "labels^2",
                            "aliases"
                        ]
                    }
                }
            ]
        }
    },
    "size": 50
}
