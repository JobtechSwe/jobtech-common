import os

# from valuestore import taxonomy
#
# # Elasticsearch settings
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = os.getenv("ES_PORT", 9200)
ES_USER = os.getenv("ES_USER")
ES_PWD = os.getenv("ES_PWD")
# # API keys settings
ES_SYSTEM_INDEX = os.getenv("ES_SYSTEM_INDEX", "apikeys")

# # Header parameters
APIKEY = 'api-key'
