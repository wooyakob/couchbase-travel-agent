from services.couchbase_service import CouchbaseService
from services.openai_service import OpenAIService
from agentc.catalog import tool
from couchbase.options import QueryOptions

@tool
def get_hotels_details(hotel_ids: list[str], fields: list[str]) -> str:
    """
    Fetches specific information (e.g., 'price', 'pets_ok','free_breakfast', 'free_internet', 'free_parking') for a list of hotel IDs.
    Use this to get details for multiple hotels in a single call.
    Example: hotel_ids=['hotel_101', 'hotel_102'], fields=['price']
    """
    cluster = CouchbaseService.get_cluster()
    bucket = cluster.bucket("travel-sample")
    collection = bucket.scope("inventory").collection("hotel")
    
    import couchbase.subdocument as SD
    specs = [SD.get(f) for f in fields]
    
    all_details = {}
    
    for hid in hotel_ids:
        try:
            result = collection.lookup_in(hid, specs)
            hotel_data = {}
            for i, field in enumerate(fields):
                hotel_data[field] = result.content_as[str](i)
            all_details[hid] = hotel_data
        except Exception:
            all_details[hid] = "Error: Hotel ID not found or field missing"
            
    return f"Batch Details: {all_details}"

#  It must match hotels to a desired vibe,
#  and locate them in a city near provided GPS coordinates.
@tool
def find_hotels_by_vibe_and_coordinates(location: str, vibe_description: str, lat: float, lon: float) -> str:
    """
    Finds hotels using specific coordinates in a city, based on a 'vibe' (e.g., 'quiet', 'modern').
    Example: location='London', lat=51.500786, lon=-0.124681, vibe_description='a quiet hotel with a garden.'
    """
    cluster = CouchbaseService.get_cluster()
    bucket = "travel-sample"
    
    # 1. Vectorize the 'vibe'
    embedding = OpenAIService.get_embedding(vibe_description)
    
    # 2. Hybrid Search: Structured (city) + Unstructured (vector)
    sql = f"""
        SELECT META(h).id, h.name, h.description
        FROM `{bucket}`.inventory.hotel AS h
        WHERE h.city = $location
        AND SQRT(POWER(h.geo.lat - $lat, 2) + POWER(h.geo.lon - $lon, 2)) < 0.01
        ORDER BY APPROX_VECTOR_DISTANCE(h.v_description, $embedding, "L2")
        LIMIT 3
    """
    
    try:
        params = {"location": location, "lat": lat, "lon": lon, "embedding": embedding}
        result = cluster.query(sql, QueryOptions(named_parameters=params))
        hotels = [f"{row['name']} | ID: {row['id']} | Vibe: {row['description'][:150]}..." for row in result]
        return "\n".join(hotels) if hotels else f"No hotels in {location} match that vibe."
    except Exception as e:
        return f"Search Error: {str(e)}"

@tool
def find_hotels_by_vibe(location: str, vibe_description: str) -> str:
    """
    Finds hotels in a specific city based on a 'vibe' (e.g., 'quiet', 'modern').
    Example: location='London', vibe_description='a quiet hotel with a garden'
    """
    cluster = CouchbaseService.get_cluster()
    bucket = "travel-sample"
    
    # 1. Vectorize the 'vibe'
    embedding = OpenAIService.get_embedding(vibe_description)
    
    # 2. Hybrid Search: Structured (city) + Unstructured (vector)
    sql = f"""
        SELECT META(h).id, h.name, h.description
        FROM `{bucket}`.inventory.hotel AS h
        WHERE h.city = $location
        ORDER BY APPROX_VECTOR_DISTANCE(h.v_description, $embedding, "L2")
        LIMIT 3
    """
    
    try:
        params = {"location": location, "embedding": embedding}
        result = cluster.query(sql, QueryOptions(named_parameters=params))
        hotels = [f"{row['name']} | ID: {row['id']} | Vibe: {row['description'][:150]}..." for row in result]
        return "\n".join(hotels) if hotels else f"No hotels in {location} match that vibe."
    except Exception as e:
        return f"Search Error: {str(e)}"

@tool
def get_hotels_sentiments(hotel_ids: list[str]) -> str:
    """
    Analyzes guest reviews for multiple hotels at once.
    Always use this when a user asks for a 'recommendation' or 'vibe' of a list of hotels.
    """
    cluster = CouchbaseService.get_cluster()
    bucket = "travel-sample"

    query = f"""
        SELECT META(h).id AS id, h.name,
               ARRAY {{
                   "snippet": SUBSTR(r.content, 0, 100),
                   "sentiment": default:ai_sentiment({{"text": r.content}})[0].response
               }}
               FOR r IN h.reviews END AS reviews_analysis
        FROM `{bucket}`.inventory.hotel AS h
        WHERE META(h).id IN $ids and ARRAY_LENGTH(h.reviews) > 0
        LIMIT 15
    """

    try:
        result = cluster.query(query, QueryOptions(named_parameters={"ids": hotel_ids}))

        output = []
        for row in result:
            analysis = row['reviews_analysis']
            if not analysis:
                output.append(f"Hotel: {row['name']} | Status: No reviews available.")
                continue

            hotel_report = f"Hotel: {row['name']}\n"
            for rev in analysis:
                sentiment = (rev["sentiment"] or "unknown").capitalize()
                hotel_report += f"  - Sentiment: {sentiment}\n"
                hotel_report += f"  - Snippet: \"{rev['snippet']}...\"\n"
            output.append(hotel_report)

        return "\n".join(output)
    except Exception as e:
        return f"Sentiment Error: {str(e)}"

@tool
def find_hotels_by_coordinates(location: str, lat: float, lon: float) -> str:
    """
    Finds hotels around specific GPS coordinates within a city.
    Example: location='London', lat=51.500786, lon=-0.124681
    """
    cluster = CouchbaseService.get_cluster()
    bucket_name = "travel-sample"
    
    # We include 'city' to leverage existing indexes and make the search 2x faster!
    sql = f"""
        SELECT META(h).id, h.name, h.address, h.city, h.country, h.geo.lat, h.geo.lon
        FROM `{bucket_name}`.inventory.hotel AS h
        WHERE h.city = $location
        AND SQRT(POWER(h.geo.lat - $lat, 2) + POWER(h.geo.lon - $lon, 2)) < 0.01
        LIMIT 5
    """

    params = {"location": location, "lat": lat, "lon": lon}
    
    try:
        result = cluster.query(sql, QueryOptions(named_parameters=params))
        hotels = []
        for row in result:
            # We explicitly include the ID so the Agent can see it and use it
            hotels.append(f"Name: {row['name']} | ID: {row['id']} | Address: {row['address']}")

        return "\n".join(hotels) if hotels else "No hotels found near those coordinates."
    except Exception as e:
        return f"Database Error: {str(e)}"

@tool
def find_hotels_by_location(location: str) -> str:
    """
    Fetches a list of hotels in a specific city.
    Example: location='London'
    Returns hotel names and IDs for further inspection.
    """
    cluster = CouchbaseService.get_cluster()
    bucket_name = "travel-sample"
    
    # We MUST select the fields we want to use in the return string
    sql = f"""
    SELECT META(h).id, h.name, h.address 
    FROM `{bucket_name}`.inventory.hotel AS h 
    WHERE city = $location LIMIT 5
    """
    
    try:
        result = cluster.query(sql, QueryOptions(named_parameters={"location": location}))
        hotels = []
        for row in result:
            # We explicitly include the ID so the Agent can see it and use it
            hotels.append(f"Name: {row['name']} | ID: {row['id']} | Address: {row['address']}")
            
        return "\n".join(hotels) if hotels else f"No hotels found in {location}."
    except Exception as e:
        return f"Database Error: {str(e)}"

@tool
def get_hotel_sentiment(hotel_name: str) -> str:
    """
    Analyzes guest reviews to determine the sentiment for a specific hotel.
    Always use this when a user asks for a 'recommendation' or 'vibe' of a hotel.
    """
    cluster = CouchbaseService.get_cluster()
    bucket = "travel-sample"

    # This query runs the AI function INSIDE the database
    query = f"""
        SELECT r.content,
               default:ai_sentiment({{"text": r.content}}) AS sentiment
        FROM `{bucket}`.inventory.hotel AS h
        UNNEST h.reviews AS r
        WHERE h.name = $name
        LIMIT 3
    """

    try:
        result = cluster.query(query, QueryOptions(named_parameters={"name": hotel_name}))
        rows = [row for row in result]

        if not rows:
            return f"I found the hotel '{hotel_name}', but there's no guest reviews to analyze."

        report = f"AI Sentiment Analysis for {hotel_name}:\n"
        for row in rows:
            sentiment_val = row['sentiment'][0]['response'] if row['sentiment'] else "unknown"
            snippet = row['content'][:100] + "..."
            report += f"- Sentiment: {sentiment_val} | Review snippet: \"{snippet}\"\n"

        return report
    except Exception as e:
        return f"Database Error: {str(e)}"

# --- UNIT TESTS ---
def test1():
    print("Testing 'find_hotels_by_location' tool...")
    result = find_hotels_by_location.invoke({"location": "London"})
    print(f"Result:\n{result}")

def test2():
    print("Testing 'find_hotels_by_coordinates'...")
    print(find_hotels_by_coordinates.invoke({
        "location": "London", 
        "lat": 51.500786, 
        "lon": -0.124681
    }))

def test3():
    print("\nTesting 'get_hotel_sentiment'...")
    # Test with a hotel known to have reviews in travel-sample
    print(get_hotel_sentiment.invoke({"hotel_id":"hotel_16258","hotel_name": "Park Plaza Riverbank"}))

def test4():
    print("Testing 'get_hotels_sentiments'...")
    # Test with a hotel known to have reviews in travel-sample
    print(get_hotels_sentiments.invoke({
        "hotel_ids": ["hotel_16045","hotel_16169", "hotel_16170", "hotel_16171", "hotel_16172"]
    }))

def test5():
    print("Testing 'find_hotels_by_vibe'...")
    print(find_hotels_by_vibe.invoke({
        "location": "London", 
        "vibe_description": "a quiet, boutique hotel"
    }))

def test6():
    print("Testing 'find_hotels_by_vibe_and_coordinates'...")
    print(find_hotels_by_vibe_and_coordinates.invoke({
        "location": "London", 
        "lat": 51.500786, 
        "lon": -0.124681,
        "vibe_description": "a quiet, boutique hotel"
    }))

def test7():
    print("Testing 'get_hotels_details' ...")
    print(get_hotels_details.invoke({
        "hotel_ids": ["hotel_16045", "hotel_10064"], 
        "fields": ["price", "pets_ok"]
    }))

if __name__ == "__main__":
    #test1()
    #test2()
    test3()
    test4()
    #test5()
    #test6()
    #test7()