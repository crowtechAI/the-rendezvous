import streamlit as st
from streamlit_calendar import calendar
import datetime
from datetime import timedelta
import json
from pymongo import MongoClient
from bson import ObjectId
import os
import certifi

# --- App Configuration ---
st.set_page_config(
    page_title="The Rendezvous",
    page_icon="💋",
    layout="wide",
    initial_sidebar_state="collapsed",
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
    color = "#E74C3C" if is_urgent else "#941a1d"
    events_collection.insert_one({
        "title": title, "start": start_time.isoformat(), "backgroundColor": color,
        "borderColor": color, "booker": booker, "is_urgent": is_urgent
    })

def update_event(event_id, new_title, new_start_time):
    events_collection.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {"title": new_title, "start": new_start_time.isoformat()}}
    )

def delete_event(event_id):
    events_collection.delete_one({"_id": ObjectId(event_id)})

def add_blockout(title, start_time, end_time, all_day):
    blockouts_collection.insert_one({
        "title": title, "start": start_time.isoformat(), "end": end_time.isoformat(),
        "allDay": all_day, "backgroundColor": "#444444", "borderColor": "#333333",
        "display": "background"
    })

def get_events():
    events = list(events_collection.find())
    for event in events:
        event['_id'] = str(event['_id'])
    return events

def get_event_by_id(event_id):
    return events_collection.find_one({"_id": ObjectId(event_id)})

def get_blockouts():
    blockouts = list(blockouts_collection.find())
    for blockout in blockouts:
        blockout['_id'] = str(blockout['_id'])
    return blockouts

def check_for_overlap(new_start, new_end, event_id_to_ignore=None):
    all_blockouts = get_blockouts()
    for blockout in all_blockouts:
        block_start = datetime.datetime.fromisoformat(blockout['start'])
        block_end = datetime.datetime.fromisoformat(blockout['end'])
        if new_start < block_end and new_end > block_start:
            return blockout
    return None

def get_last_urgent_rendezvous():
    now = datetime.datetime.now()
    past_fucks = events_collection.find({
        "is_urgent": True,
        "start": {"$lt": now.isoformat()}
    }).sort("start", -1).limit(1)
    try:
        return next(past_fucks, None)
    except StopIteration:
        return None

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
        notif['_id'] = str(notif['_id'])
    return notifications

def get_all_love_notes():
    notes = list(notes_collection.find({"type": "note"}).sort("timestamp", -1))
    for note in notes:
        note['_id'] = str(note['_id'])
    return notes

def mark_notification_as_read(note_id):
    notes_collection.update_one({"_id": ObjectId(note_id)}, {"$set": {"read": True}})

# --- Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400;700&display=swap');
    :root { --primary-color: #941a1d; --background-color: #121212; --secondary-background-color: #1E1E1E; --text-color: #E0E0E0; --urgent-color: #E74C3C; }
    .stApp { background-color: var(--background-color); color: var(--text-color); font-family: 'Lato', sans-serif; }
    .block-container { padding: 1rem 1rem 2rem 1rem; }
    h1, h2, h3 { font-family: 'Playfair+Display', serif; color: var(--text-color); }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: var(--secondary-background-color); }
    .stButton>button { border: none; border-radius: 8px; background-color: var(--primary-color); color: #FFFFFF; padding: 10px 24px; font-weight: 700; transition: all 0.3s ease-in-out; }
    .stButton>button:hover { box-shadow: 0 0 15px var(--primary-color); transform: translateY(-2px); }
    .button-urgent button { background-color: var(--urgent-color); }
    .button-urgent button:hover { box-shadow: 0 0 15px var(--urgent-color); }
    [data-testid="stForm"], [data-testid="stExpander"], .fc, .metric-container { background-color: var(--secondary-background-color); border-radius: 10px; padding: 25px; border-top: 3px solid var(--primary-color); }
    .st-emotion-cache-1r6slb0 { border: none; border-top: 2px solid var(--primary-color); }
</style>
""", unsafe_allow_html=True)


# --- HEADER & NAVIGATION ---
if os.path.exists(LOGO_IMAGE):
    st.image(LOGO_IMAGE, width=150)
else:
    st.title("The Rendezvous")
tabs = st.tabs(["🔥 The Boudoir", "📅 Our Agenda", "💌 Whispers"])

# --- EDITING & DELETING LOGIC ---
# This block runs before the main UI to handle edit/delete states
if 'deleting_event_id' in st.session_state:
    with st.container(border=True):
        st.warning("Are you sure you want to cancel this rendezvous?")
        col1, col2 = st.columns(2)
        if col1.button("Yes, Cancel It", use_container_width=True):
            delete_event(st.session_state.deleting_event_id)
            del st.session_state.deleting_event_id
            st.toast("Rendezvous cancelled.")
            st.rerun()
        if col2.button("No, Keep It", use_container_width=True):
            del st.session_state.deleting_event_id
            st.rerun()

elif 'editing_event_id' in st.session_state:
    st.header("Edit Rendezvous")
    event_to_edit = get_event_by_id(st.session_state.editing_event_id)
    if event_to_edit:
        with st.form("edit_form"):
            original_start = datetime.datetime.fromisoformat(event_to_edit['start'])
            
            new_title = st.text_input("Title", value=event_to_edit['title'])
            new_date = st.date_input("Date", value=original_start.date())
            new_time = st.time_input("Time", value=original_start.time())
            
            col1, col2 = st.columns(2)
            if col1.form_submit_button("Save Changes", use_container_width=True):
                new_start_dt = datetime.datetime.combine(new_date, new_time)
                new_end_dt = new_start_dt + timedelta(hours=1)
                
                conflicting_block = check_for_overlap(new_start_dt, new_end_dt)
                if conflicting_block:
                    st.error(f"Cannot update! This time conflicts with: '{conflicting_block['title']}'")
                else:
                    update_event(st.session_state.editing_event_id, new_title, new_start_dt)
                    del st.session_state.editing_event_id
                    st.toast("Rendezvous updated!")
                    st.rerun()
            
            if col2.form_submit_button("Cancel", type="secondary", use_container_width=True):
                del st.session_state.editing_event_id
                st.rerun()
else:
    # --- DASHBOARD TAB ---
    with tabs[0]:
        # --- NEW: Days Since Last Fuck Counter ---
        st.subheader("Intimacy Check-in")
        with st.container(border=True, css_class="metric-container"):
            last_fuck = get_last_urgent_rendezvous()
            if last_fuck:
                days_since = (datetime.datetime.now() - last_fuck['start']).days
                st.metric(label="Days Since Last Fuck", value=f"{days_since} day(s)")
            else:
                st.metric(label="Days Since Last Fuck", value="N/A")
                st.caption("Time to make the first memory! 🔥")
        
        st.markdown("---")

        # IN-APP NOTIFICATION SYSTEM
        unread_notifications = get_unread_notifications()
        if unread_notifications:
            st.subheader("🔔 New Alerts")
            # Notification logic... (unchanged)
        
        # URGENT BOOKING
        st.markdown('<div class="button-urgent">', unsafe_allow_html=True)
        if st.button("Book a Fuck", use_container_width=True):
            st.session_state.show_urgent_booking = not st.session_state.get('show_urgent_booking', False)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get('show_urgent_booking', False):
            # Form logic... (unchanged)
            with st.form("urgent_form"):
                st.subheader("Quick & Urgent Booking")
                booker = st.selectbox("Who's booking this?", get_partner_names())
                date = st.date_input("Date", value=datetime.date.today())
                time = st.time_input("Time", value=datetime.time(21, 0))
                if st.form_submit_button("Confirm Booking 🔥", use_container_width=True):
                    final_dt = datetime.datetime.combine(date, time)
                    end_dt = final_dt + timedelta(hours=1)
                    conflicting_block = check_for_overlap(final_dt, end_dt)
                    if conflicting_block:
                        st.error(f"Cannot book! Conflicts with: '{conflicting_block['title']}'")
                    else:
                        add_event("Urgent Rendezvous 🔥", final_dt, booker, is_urgent=True)
                        add_booking_notification(f"{booker} booked an Urgent Rendezvous!")
                        st.success("It's a date! 🔥")
                        st.session_state.show_urgent_booking = False
                        st.rerun()

        st.markdown("---")

        # SPLIT RENDEZVOUS DISPLAY WITH EDIT/DELETE BUTTONS
        now = datetime.datetime.now()
        all_events = get_events()
        all_upcoming = sorted([e for e in all_events if 'start' in e and datetime.datetime.fromisoformat(e['start']) > now], key=lambda x: datetime.datetime.fromisoformat(x['start']))
        
        st.subheader("🍆 Fucks Booked")
        urgent_events = [e for e in all_upcoming if e.get("is_urgent")]
        if not urgent_events:
            st.info("No urgent bookings.")
        for event in urgent_events:
            with st.container(border=True):
                event_date = datetime.datetime.fromisoformat(event['start'])
                st.markdown(f"**{event.get('booker', 'Someone')}** Booked a fuck on _{event_date.strftime('%A, %b %d at %I:%M %p')}_")
                col1, col2 = st.columns(2)
                if col1.button("✏️ Edit", key=f"edit_u_{event['_id']}", use_container_width=True):
                    st.session_state.editing_event_id = event['_id']
                    st.rerun()
                if col2.button("🗑️ Cancel", key=f"del_u_{event['_id']}", use_container_width=True):
                    st.session_state.deleting_event_id = event['_id']
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🌹 Rendezvous")
        planned_events = [e for e in all_upcoming if not e.get("is_urgent")]
        if not planned_events:
            st.info("No planned dates.")
        for event in planned_events:
            with st.container(border=True):
                event_date = datetime.datetime.fromisoformat(event['start'])
                st.markdown(f"**{event['title']}** on _{event_date.strftime('%A, %b %d at %I:%M %p')}_")
                st.markdown(f"<small>Booked by: {event.get('booker', 'Unknown')}</small>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                if col1.button("✏️ Edit", key=f"edit_p_{event['_id']}", use_container_width=True):
                    st.session_state.editing_event_id = event['_id']
                    st.rerun()
                if col2.button("🗑️ Cancel", key=f"del_p_{event['_id']}", use_container_width=True):
                    st.session_state.deleting_event_id = event['_id']
                    st.rerun()

    # --- CALENDAR TAB ---
    with tabs[1]:
        # Calendar logic... (unchanged)
        with st.expander("Plan a Rendezvous", expanded=True):
            with st.form("new_rendezvous", clear_on_submit=True):
                booker = st.selectbox("Who's booking this?", get_partner_names())
                title = st.text_input("Rendezvous Idea", placeholder="e.g., Dinner at our spot")
                date = st.date_input("Date")
                start_time = st.time_input("Time")
                if st.form_submit_button("Add to Agenda", use_container_width=True):
                    if title:
                        final_dt = datetime.datetime.combine(date, start_time)
                        end_dt = final_dt + timedelta(hours=1)
                        conflicting_block = check_for_overlap(final_dt, end_dt)
                        if conflicting_block:
                            st.error(f"Cannot book! Conflicts with: '{conflicting_block['title']}'")
                        else:
                            add_event(title, final_dt, booker, is_urgent=False)
                            add_booking_notification(f"{booker} planned '{title}'!")
                            st.toast(f"'{title}' added!")
                            st.rerun()
        
        with st.expander("Block Out Time"):
            with st.form("blockout_form", clear_on_submit=True):
                # Block out form logic... (unchanged)
                pass

        st.markdown("<br>", unsafe_allow_html=True)
        all_calendar_items = get_events() + get_blockouts()
        calendar(events=all_calendar_items)

    # --- LOVE NOTES TAB ---
    with tabs[2]:
        # Love notes logic... (unchanged)
        pass

    # --- 
