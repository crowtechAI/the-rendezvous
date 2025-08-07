import streamlit as st
from streamlit_calendar import calendar
import datetime
import json
from pymongo import MongoClient
from bson import ObjectId
import os
import certifi

# --- App Configuration ---
st.set_page_config(
    page_title="The Rendezvous",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- LOGO CONFIGURATION ---
LOGO_IMAGE = "logo.png"

# --- Database Connection ---
try:
    client = MongoClient(st.secrets["mongo_uri"], tlsCAFile=certifi.where())
    db = client.get_database("rendezvous")
    events_collection = db["events"]
    blockouts_collection = db["blockouts"]
    notes_collection = db["love_notes"]
    app_state_collection = db["app_state"]
except Exception as e:
    st.error(f"Failed to connect to MongoDB. Check your secrets and IP Access List. Error: {e}")
    st.stop()

# --- One-Time Database Setup ---
def setup_database():
    if app_state_collection.count_documents({"key": "partner_names"}) == 0:
        app_state_collection.insert_one({"key": "partner_names", "value": ["Partner 1", "Partner 2"]})
    notes_collection.create_index([("timestamp", -1)])

setup_database()

# --- Data Helper Functions ---
def get_partner_names():
    doc = app_state_collection.find_one({"key": "partner_names"})
    return doc['value'] if doc else ["Partner 1", "Partner 2"]

def update_partner_names(p1, p2):
    app_state_collection.update_one({"key": "partner_names"}, {"$set": {"value": [p1, p2]}}, upsert=True)

def add_event(title, start_time, booker, is_urgent):
    color = "#E74C3C" if is_urgent else "#D98880"
    events_collection.insert_one({
        "title": title, "start": start_time.isoformat(), "backgroundColor": color,
        "borderColor": color, "booker": booker, "is_urgent": is_urgent
    })

def add_blockout(title, start_time, end_time, all_day):
    blockouts_collection.insert_one({
        "title": title, "start": start_time.isoformat(), "end": end_time.isoformat(),
        "allDay": all_day, "backgroundColor": "#808B96", "borderColor": "#5D6D7E",
        "display": "background"
    })

def get_events():
    """Fetches events and makes them JSON-safe."""
    events = list(events_collection.find())
    for event in events:
        event['_id'] = str(event['_id']) # FIX: Convert ObjectId to string
    return events

def get_blockouts():
    """Fetches blockouts and makes them JSON-safe."""
    blockouts = list(blockouts_collection.find())
    for blockout in blockouts:
        blockout['_id'] = str(blockout['_id']) # FIX: Convert ObjectId to string
    return blockouts

def add_love_note(author, message):
    notes_collection.insert_one({
        "author": author, "message": message, "timestamp": datetime.datetime.now(),
        "read": False, "type": "note"
    })

def add_booking_notification(message):
    notes_collection.insert_one({
        "message": message, "timestamp": datetime.datetime.now(),
        "read": False, "type": "booking"
    })

def get_unread_notifications():
    notifications = list(notes_collection.find({"read": False}).sort("timestamp", -1))
    for notif in notifications:
        notif['_id'] = str(notif['_id']) # FIX: Convert ObjectId to string
    return notifications

def get_all_love_notes():
    notes = list(notes_collection.find({"type": "note"}).sort("timestamp", -1))
    for note in notes:
        note['_id'] = str(note['_id']) # FIX: Convert ObjectId to string
    return notes

def mark_notification_as_read(note_id):
    notes_collection.update_one({"_id": ObjectId(note_id)}, {"$set": {"read": True}})


# --- Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400;700&display=swap');
    .stApp { background-color: #FDF8F5; color: #34495E; font-family: 'Lato', sans-serif; }
    .block-container { max-width: 1200px; padding-top: 2rem; padding-bottom: 2rem; margin: auto; }
    h1, .sidebar-title { font-family: 'Playfair Display', serif; color: #B05A5A; text-align: center; }
    h2, h3 { font-family: 'Playfair Display', serif; color: #34495E; }
    .stButton>button { border: 2px solid #D98880; border-radius: 8px; background-color: transparent; color: #D98880; padding: 10px 24px; font-weight: 700; transition: all 0.3s ease-in-out; text-transform: uppercase; letter-spacing: 1px; }
    .stButton>button:hover { background-color: #D98880; color: #FFFFFF; transform: translateY(-2px); }
    .button-urgent button { background-color: #E74C3C; color: white; border: none; font-weight: bold; }
    .button-urgent button:hover { background-color: #C0392B; }
    .stSidebar { background-color: #F4ECE6; }
    .stForm, .fc { background-color: #FFFFFF; border-radius: 10px; padding: 25px; border: 1px solid #EAE0DA; }
</style>
""", unsafe_allow_html=True)


# --- Page Navigation ---
if 'page' not in st.session_state: st.session_state.page = "Dashboard"
def navigate_to(page_name): st.session_state.page = page_name

# --- Sidebar ---
with st.sidebar:
    if os.path.exists(LOGO_IMAGE):
        st.image(LOGO_IMAGE, use_column_width=True)
    else:
        st.markdown('<h1 class="sidebar-title">The Rendezvous</h1>', unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("Dashboard", use_container_width=True, type="secondary" if st.session_state.page != "Dashboard" else "primary"): navigate_to("Dashboard")
    if st.button("Calendar", use_container_width=True, type="secondary" if st.session_state.page != "Calendar" else "primary"): navigate_to("Calendar")
    if st.button("Love Notes", use_container_width=True, type="secondary" if st.session_state.page != "Love Notes" else "primary"): navigate_to("Love Notes")

    st.markdown("---")
    with st.expander("Partner Names"):
        partner_names = get_partner_names()
        p1 = st.text_input("Partner 1", value=partner_names[0])
        p2 = st.text_input("Partner 2", value=partner_names[1])
        if st.button("Save Names", use_container_width=True):
            update_partner_names(p1, p2)
            st.toast("Names updated!")
            st.rerun()

# --- Main App Logic ---

if st.session_state.page == "Dashboard":
    st.title("Our Dashboard")

    unread_notifications = get_unread_notifications()
    if unread_notifications:
        st.subheader("🔔 New Alerts")
        for notif in unread_notifications:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"{notif['message']}")
            with col2:
                target_page = "Love Notes" if notif.get("type") == "note" else "Calendar"
                button_text = "Read Note" if target_page == "Love Notes" else "View Calendar"
                if st.button(button_text, key=f"view_{notif['_id']}", use_container_width=True):
                    mark_notification_as_read(ObjectId(notif['_id']))
                    navigate_to(target_page)
                    st.rerun()
        st.markdown("---")

    st.markdown('<div class="button-urgent">', unsafe_allow_html=True)
    if st.button("Book a Fuck", use_container_width=True):
        st.session_state.show_urgent_booking = not st.session_state.get('show_urgent_booking', False)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get('show_urgent_booking', False):
        with st.form("urgent_form"):
            st.subheader("Quick & Urgent Booking")
            booker = st.selectbox("Who's booking this?", get_partner_names())
            col1, col2 = st.columns(2)
            date = col1.date_input("Date", value=datetime.date.today())
            time = col2.time_input("Time", value=datetime.time(21, 0))
            if st.form_submit_button("Confirm Booking 🔥", use_container_width=True):
                final_dt = datetime.datetime.combine(date, time)
                add_event("Urgent Rendezvous 🔥", final_dt, booker, is_urgent=True)
                add_booking_notification(f"{booker} booked an Urgent Rendezvous!")
                st.success("It's a date! Your partner will be alerted. 🔥")
                st.session_state.show_urgent_booking = False
                st.rerun()

    st.markdown("---")

    now = datetime.datetime.now()
    all_events = get_events()
    all_upcoming = sorted(
        [e for e in all_events if 'start' in e and datetime.datetime.fromisoformat(e['start']) > now], 
        key=lambda x: datetime.datetime.fromisoformat(x['start'])
    )
    
    urgent_events = [e for e in all_upcoming if e.get("is_urgent")]
    planned_events = [e for e in all_upcoming if not e.get("is_urgent")]

    st.subheader("🍆 Fucks Booked")
    if not urgent_events:
        st.info("No urgent bookings. Maybe it's time to make one?")
    else:
        for event in urgent_events:
            with st.container(border=True):
                event_date = datetime.datetime.fromisoformat(event['start'])
                booker_name = event.get('booker', 'Someone')
                st.markdown(f"**{booker_name}** Booked a fuck on _{event_date.strftime('%A, %b %d at %I:%M %p')}_")

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("📅 Planned Dates")
    if not planned_events:
        st.info("No planned dates on the calendar.")
    else:
        for event in planned_events:
            with st.container(border=True):
                event_date = datetime.datetime.fromisoformat(event['start'])
                st.markdown(f"**{event['title']}** on _{event_date.strftime('%A, %b %d at %I:%M %p')}_")
                st.markdown(f"<small>Booked by: {event.get('booker', 'Unknown')}</small>", unsafe_allow_html=True)

elif st.session_state.page == "Calendar":
    st.title("Our Calendar")
    
    with st.expander("Plan a New Date", expanded=True):
        with st.form("new_rendezvous", clear_on_submit=True):
            booker = st.selectbox("Who's booking this?", get_partner_names())
            col1, col2 = st.columns(2)
            title = col1.text_input("Date Idea", placeholder="e.g., Dinner at our spot")
            date = col1.date_input("Date")
            start_time = col2.time_input("Time")
            if st.form_submit_button("Add to Calendar", use_container_width=True):
                if title:
                    final_dt = datetime.datetime.combine(date, start_time)
                    add_event(title, final_dt, booker, is_urgent=False)
                    add_booking_notification(f"{booker} planned '{title}'!")
                    st.toast(f"'{title}' added! Your partner will be alerted.")
                    st.rerun()
    
    with st.expander("Block Out Time"):
        with st.form("blockout_form", clear_on_submit=True):
            title = st.text_input("Reason", placeholder="e.g., Work, Period, Family visit")
            all_day = st.checkbox("All-day event")
            
            col1, col2 = st.columns(2)
            if all_day:
                date = col1.date_input("Date")
                start_dt = datetime.datetime.combine(date, datetime.time.min)
                end_dt = datetime.datetime.combine(date, datetime.time.max)
            else:
                start_date = col1.date_input("Start Date")
                start_time = col2.time_input("Start Time", value=datetime.time(9,0))
                end_date = col1.date_input("End Date")
                end_time = col2.time_input("End Time", value=datetime.time(17,0))
                start_dt = datetime.datetime.combine(start_date, start_time)
                end_dt = datetime.datetime.combine(end_date, end_time)

            if st.form_submit_button("Block Out Period", use_container_width=True):
                if title:
                    add_blockout(title, start_dt, end_dt, all_day)
                    st.toast("Time blocked out on the calendar.")
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    all_calendar_items = get_events() + get_blockouts()
    calendar(events=all_calendar_items)

elif st.session_state.page == "Love Notes":
    st.title("Our Love Notes")
    with st.form("love_note_form", clear_on_submit=True):
        author = st.selectbox("From", get_partner_names())
        message = st.text_area("Message", placeholder="Thinking of you...")
        if st.form_submit_button("Send Note", use_container_width=True):
            if message:
                add_love_note(author, message)
                st.toast("Note sent! Your partner will be alerted.")
                st.rerun()
    
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    all_notes = get_all_love_notes()
    if not all_notes:
        st.info("The first note is yet to be written...")
    else:
        st.subheader("Our Message Board")
        for note in all_notes:
            with st.container(border=True):
                # Ensure timestamp is a datetime object before formatting
                ts = note['timestamp'] if isinstance(note['timestamp'], datetime.datetime) else datetime.datetime.fromisoformat(note['timestamp'])
                st.markdown(f"**From: {note['author']}** | <small>{ts.strftime('%b %d, %Y at %I:%M %p')}</small>", unsafe_allow_html=True)
                st.write(f"> *{note['message']}*")
