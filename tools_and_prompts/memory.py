from couchbase.options import QueryOptions
from services.couchbase_service import CouchbaseService
from datetime import datetime
import uuid
from agentc.catalog import tool

BUCKET = "travel-sample"
SCOPE  = "persistence"

# USER PREFERENCES
@tool
def save_user_preference(user_id: str, category: str, content: str) -> str:
   """
    Saves or updates a travel preference for a user.
    Use this when the user states a preference, constraint, or personal rule.
    Categories: 'budget', 'vibe', 'destination', 'policy_note', 'other'
    Example: user_id='traveler_1', category='vibe', value='modern and vibrant hotels'
    Example: user_id='traveler_1', category='budget', value='max €150 per night'
    """
   cluster = CouchbaseService.get_cluster()
   collection = cluster.bucket(BUCKET).scope(SCOPE).collection("memory")

   doc_id = f"pref_{user_id}_{category}"
   current_date = datetime.now().isoformat()
   doc = {
       "type":       "preference",
        "user_id":    user_id,
        "category":   category,
        "content":    content,
        "updated_at": current_date
       }

   try:
        collection.upsert(doc_id, doc)
        return f"Preference saved: [{category}] = '{content}'"
   except Exception as e:
        return f"Error saving preference: {str(e)}"


@tool
def get_user_preferences(user_id: str) -> str:
    """
    Retrieves all saved travel preferences for a user.
    Always call this at the start of a conversation to personalise responses.
    Example: user_id='traveler_1'
    """
    cluster = CouchbaseService.get_cluster()

    sql = f"""
        SELECT m.category, m.content, m.updated_at
        FROM `{BUCKET}`.{SCOPE}.memory AS m
        WHERE m.user_id = $user_id
        AND m.type = 'preference'
        ORDER BY m.updated_at DESC
    """

    try:
        result = cluster.query(sql, QueryOptions(named_parameters={"user_id": user_id}))
        rows = [row for row in result]

        if not rows:
            return f"No preferences found for user '{user_id}'."

        prefs = "\n".join([f"  - [{r['category']}]: {r['content']}" for r in rows])
        return f"User preferences for '{user_id}':\n{prefs}"

    except Exception as e:
        return f"Error retrieving preferences: {str(e)}"


# TRIP HISTORY
@tool
def book_trip(user_id: str, destination: str, hotel_name: str, 
              within_policy: bool, travel_date: str = "not specified") -> str:
    """
    Saves a confirmed hotel booking for a user.
    Only call this when the user explicitly confirms they want to book a hotel
    (e.g. 'book it', 'I'll take that one', 'go with hotel 2', 'book me this hotel').
    
    For travel_date: extract the date from the user's message if mentioned
    (e.g. 'tomorrow', 'next Monday', 'May 20th'). Use get_current_date() 
    to resolve relative dates. If no date mentioned, use 'not specified'.
    
    Example: user_id='traveler_1', destination='Paris', 
             hotel_name='Campanile Paris XV', within_policy=True,
             travel_date='2026-05-20'
    """
    cluster = CouchbaseService.get_cluster()
    collection = cluster.bucket(BUCKET).scope(SCOPE).collection("memory")

    doc_id = f"trip_{user_id}_{uuid.uuid4().hex[:8]}"
    doc = {
        "type":          "trip",
        "user_id":       user_id,
        "destination":   destination,
        "hotel_name":    hotel_name,
        "within_policy": within_policy,
        "travel_date":   travel_date,        # ← actual travel date from user
        "booked_at":     datetime.now().isoformat()  # ← when booking was made
    }

    try:
        collection.upsert(doc_id, doc)
        status = "Within Policy" if within_policy else "Not Within Policy"
        date_info = f" for {travel_date}" if travel_date != "not specified" else ""
        return f"Trip booked: {hotel_name} in {destination}{date_info} ({status})"
    except Exception as e:
        return f"Error saving trip: {str(e)}"

@tool
def get_trip_history(user_id: str) -> str:
    """
    Retrieves the travel history for a user.
    Use this when the user asks about past trips, previously searched hotels,
    or whether they have travelled to a destination before.
    Example: user_id='traveler_1'
    """
    cluster = CouchbaseService.get_cluster()

    sql = f"""
        SELECT m.destination, m.hotel_name, m.within_policy, 
            m.travel_date, m.booked_at
         FROM `{BUCKET}`.{SCOPE}.memory AS m
        WHERE m.user_id = $user_id
        AND m.type = 'trip'
        ORDER BY m.booked_at DESC
        LIMIT 10
    """

    try:
        result = cluster.query(sql, QueryOptions(named_parameters={"user_id": user_id}))
        rows = [row for row in result]

        if not rows:
            return f"No trip history found for user '{user_id}'."

        lines = []
        for r in rows:
            status = "Within Policy" if r['within_policy'] else "Not Within Policy"
            travel = r.get('travel_date', 'not specified')
            booked = r.get('booked_at', r.get('travel_date', 'unknown'))[:10]
            lines.append(
                  f"  {status} {r['hotel_name']} in {r['destination']} "
                 f"(travel: {travel} | booked: {booked})"
            )

        return f"Trip history for '{user_id}':\n" + "\n".join(lines)

    except Exception as e:
        return f"Error retrieving trip history: {str(e)}"

# UNIT TESTS
def test_preferences():
    print("Testing User Preferences...")
    print(save_user_preference.invoke({
        "user_id":  "traveler_1",
        "category": "budget",
        "content":  "max €150 per night"
    }))
    print(save_user_preference.invoke({
        "user_id":  "traveler_1",
        "category": "vibe",
        "content":  "quiet hotels"
    }))
    print(save_user_preference.invoke({
        "user_id":  "traveler_1",
        "category": "destination",
        "content":  "frequently travels to Paris and London"
    }))

    print("Test: Retrieve preferences")
    print(get_user_preferences.invoke({"user_id": "traveler_1"}))

def test_trips():
    print("Testing Saving Past Trips...")
    
    # Test 1: booking with explicit travel date
    print(book_trip.invoke({
        "user_id":       "traveler_1",
        "destination":   "Paris",
        "hotel_name":    "Campanile Paris XV - Tour Eiffel",
        "within_policy": True,
        "travel_date":   "2026-05-20"
    }))
    
    # Test 2: booking over policy with explicit date
    print(book_trip.invoke({
        "user_id":       "traveler_1",
        "destination":   "Paris",
        "hotel_name":    "Pullman Paris Tour Eiffel",
        "within_policy": False,
        "travel_date":   "2026-05-21"
    }))
    
    # Test 3: booking with no travel date specified
    print(book_trip.invoke({
        "user_id":       "traveler_1",
        "destination":   "London",
        "hotel_name":    "Grantly Hotel",
        "within_policy": True,
        "travel_date":   "not specified"
    }))

    print("Test: Retrieve trip history")
    print(get_trip_history.invoke({"user_id": "traveler_1"}))

if __name__ == "__main__":
    #test_preferences()
    test_trips()
