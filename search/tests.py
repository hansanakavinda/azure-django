from django.test import TestCase

from django.conf import settings

def sample_connection_test():
    """
    Sample function to test Cosmos DB connectivity and basic read operation.
    """
    from azure.cosmos import CosmosClient

    url = settings.COSMOS_URI
    key = settings.COSMOS_KEY
    db = settings.COSMOS_DATABASE
    container_name = settings.COSMOS_CONTAINER
    partition_key_path = settings.PARTITION_KEY_PATH  

    client = CosmosClient(url, credential=key)  

    database = client.get_database_client(db)
    container = database.get_container_client(container_name)

    # container_properties = container.read()
    # partition_key_path = container_properties['partitionKey']['paths'][0]

    # print(f"Partition Key Path: {partition_key_path}")  

    # Query all items
    query = "SELECT * FROM c"
    items = container.query_items(
        query=query,
        enable_cross_partition_query=True
    )

    results = list(items)
    print(f"Total items retrieved: {len(results)}")
    print("results: ", results)

class MyTestCase(TestCase):
    def test_my_function(self):
        result = sample_connection_test()
        return result