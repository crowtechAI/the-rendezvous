import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
import datetime

# Page config
st.set_page_config(page_title="Rendezvous", layout="centered")
st.title("🌹 Rendezvous: Couple Event Scheduler")

# MongoDB Connection
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client.get_database("rendezvous")
events_collection = db["events"]

# Utilities
def get_events():
    return list(events_collection.find().sort("date", 1))

def add_event(title, date, partner):
    events_collection.insert_one({
        "title": title,
        "date": date,
        "partner": partner,
        "attended": False
    })

def delete_event(event_id):
    events_collection.delete_one({"_id": ObjectId(event_id)})

def mark_attended(event_id, attended):
    events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": {"attended": attended}})

def get_stats():
    pipeline = [
        {"$match": {"attended": True}},
        {"$group": {"_id": "$partner", "count": {"$sum": 1}}}
    ]
    return {doc["_id"]: doc["count"] for doc in events_collection.aggregate(pipeline)}

# Tabs
tabs = st.tabs(["📅 Schedule", "📈 Stats"])

with tabs[0]:
    st.subheader("Schedule a Rendezvous")
    with st.form("event_form"):
        title = st.text_input("Event Title")
        date = st.date_input("Date", min_value=datetime.date.today())
        partner = st.radio("Who planned this?", ["You", "Partner"], horizontal=True)
        submitted = st.form_submit_button("➕ Add Event")
        if submitted:
            add_event(title, date.isoformat(), partner)
            st.success("Event added!")
            st.experimental_rerun()

    st.markdown("---")
    st.subheader("Upcoming Events")
    events = get_events()
    if not events:
        st.info("No upcoming events.")
    for event in events:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{event['title']}** — {event['date']}")
            st.caption(f"Planned by: {event['partner']}")
        with col2:
            attended = st.checkbox("Attended", value=event.get("attended", False), key=str(event['_id']))
            mark_attended(event['_id'], attended)
        with col3:
            if st.button("🗑️", key=f"delete_{event['_id']}"):
                delete_event(event['_id'])
                st.experimental_rerun()

with tabs[1]:
    st.subheader("Who planned more events?")
    stats = get_stats()
    col1, col2 = st.columns(2)
    col1.metric("🎯 Your Events Attended", stats.get("You", 0))
    col2.metric("❤️ Partner's Events Attended", stats.get("Partner", 0))
