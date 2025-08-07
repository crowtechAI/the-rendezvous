import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
import datetime

# --- App Configuration ---
st.set_page_config(
    page_title="Rendezvous",
    page_icon="🌹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Database Connection ---
# This connects to the MongoDB database defined in your Streamlit Secrets.
try:
    client = MongoClient(st.secrets["mongo_uri"])
    db = client.get_database("rendezvous")
    events_collection = db["events"]
except Exception as e:
    st.error(f"Failed to connect to MongoDB. Please check your secrets.toml configuration. Error: {e}")
    st.stop()

# --- Data Helper Functions ---
def get_events():
    """Fetches all events sorted by date."""
    return list(events_collection.find().sort("date", 1))

def add_event(title, date, partner):
    """Adds a new event to the collection."""
    if not title:
        st.warning("Please enter an event title.")
        return
    events_collection.insert_one({
        "title": title,
        "date": date,
        "partner": partner,
        "attended": False
    })
    st.success("Event added!")

def delete_event(event_id):
    """Deletes an event by its ID."""
    events_collection.delete_one({"_id": ObjectId(event_id)})
    st.toast("Event removed.")

def mark_attended(event_id, attended):
    """Updates the attended status of an event."""
    events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": {"attended": attended}})
    st.toast("Status updated!")

def get_stats():
    """Calculates the number of attended events per partner."""
    pipeline = [
        {"$match": {"attended": True}},
        {"$group": {"_id": "$partner", "count": {"$sum": 1}}}
    ]
    return {doc["_id"]: doc["count"] for doc in events_collection.aggregate(pipeline)}


# --- Main App UI ---
st.title("🌹 The Rendezvous")
st.markdown("*Our simple, shared event scheduler*")

# Create two tabs for scheduling and stats
tab1, tab2 = st.tabs(["📅 Schedule Events", "📈 Our Stats"])

with tab1:
    # --- Form for adding new events ---
    with st.form("event_form", clear_on_submit=True):
        st.subheader("Plan a New Rendezvous")
        title = st.text_input("Event Title", placeholder="e.g., Dinner at the new Italian place")
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", min_value=datetime.date.today())
        with col2:
            partner = st.radio("Who planned this?", ["Me", "My Partner"], horizontal=True)
        
        submitted = st.form_submit_button("➕ Add Rendezvous", use_container_width=True)
        if submitted:
            # Convert date to datetime for MongoDB compatibility
            event_datetime = datetime.datetime.combine(date, datetime.datetime.min.time())
            add_event(title, event_datetime, partner)
            # No need for rerun(), form submission handles it.

    st.markdown("---")
    st.subheader("Our Upcoming Events")
    
    # --- Display list of events ---
    all_events = get_events()
    if not all_events:
        st.info("No events scheduled yet. Time to plan something fun!")
    
    for event in all_events:
        event_id_str = str(event['_id'])
        
        # Ensure date is datetime object
        event_date = event['date'] if isinstance(event['date'], datetime.datetime) else datetime.datetime.fromisoformat(event['date'])

        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.markdown(f"**{event['title']}**")
                st.caption(f"On {event_date.strftime('%A, %b %d, %Y')} — Planned by: {event['partner']}")
            with col2:
                # --- CORRECTED: Using on_change for efficient updates ---
                attended = st.checkbox(
                    "Attended", 
                    value=event.get("attended", False), 
                    key=f"attended_{event_id_str}",
                    on_change=mark_attended,
                    args=(event['_id'], not event.get("attended", False))
                )
            with col3:
                # Use a unique key for the delete button
                if st.button("🗑️", key=f"delete_{event_id_str}", use_container_width=True):
                    delete_event(event['_id'])
                    st.rerun()

with tab2:
    st.subheader("Rendezvous Scoreboard")
    stats = get_stats()
    col1, col2 = st.columns(2)
    col1.metric("❤️ My Events Attended", stats.get("Me", 0))
    col2.metric("💖 Partner's Events Attended", stats.get("My Partner", 0))
