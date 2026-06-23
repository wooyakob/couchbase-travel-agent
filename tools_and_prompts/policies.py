from services.couchbase_service import CouchbaseService
from services.openai_service import OpenAIService
from couchbase.options import QueryOptions
from agentc.catalog import tool

@tool
def get_travel_policy(city: str) -> str:
    """
    Retrieves the ACME Travel Policy rules (spending limits) for a specific city.
    Use this to verify if a hotel price is allowed by company rules.
    """
    cluster = CouchbaseService.get_cluster()
    bucket = "travel-sample"
    
    query_text = f"What is the max hotel rate per night in the city {city}?"
    embedding = OpenAIService.get_embedding(query_text)
    
    sql = f"""
        SELECT p.`text-to-embed` as snippet
        FROM `{bucket}`.company.policies AS p
        ORDER BY APPROX_VECTOR_DISTANCE(p.`text-embedding`, $embedding, "L2")
        LIMIT 3
    """
    
    try:
        result = cluster.query(sql, QueryOptions(named_parameters={"embedding": embedding}))
        policy_text = "\n\n".join([row["snippet"] for row in result])
        return f"ACME Travel Policy Context for {city}:\n{policy_text}"
    except Exception as e:
        return f"Error retrieving policy: {str(e)}"

if __name__ == "__main__":
    print("Testing Policy Retrieval...\n")
    print(get_travel_policy.invoke({"city": "London"}))