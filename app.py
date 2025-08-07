
import streamlit as st
from streamlit_calendar import calendar
import datetime
import json
import zlib
import base64
import os

# --- LOGO CONFIGURATION ---
# The app will look for a file named 'logo.png' in the same folder.
LOGO_IMAGE = "logo.png"

# --- App Configuration ---
st.set_page_config(
    page_title="The Rendezvous",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Data Persistence & Backward Compatibility ---
def get_default_data():
    """Return the default structure for the app's data."""
    return {
        "events": [],
        "love_notes": [],
        "partner_names": ["Partner 1", "Partner 2"],
        "notifications": []
    }

def decode_data(encoded_string):
    """Decode, decompress, and validate data from a URL-safe string."""
    try:
        data = json.loads(zlib.decompress(base64.b64decode(encoded_string.encode('utf-8'))).decode('utf-8'))
        defaults = get_default_data()
        for key, default_value in defaults.items():
            data.setdefault(key, default_value)
        return data
    except Exception:
        return get_default_data()

def encode_data(data):
    """Compress and encode data to a URL-safe string."""
    return base64.b64encode(zlib.compress(json.dumps(data).encode('utf-8'))).decode('utf-8')

# Load data from query params or set default
query_params = st.query_params
app_data = decode_data(query_params.get("data", ""))

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
    # Display logo if it exists, otherwise display text title
    if os.path.exists(LOGO_IMAGE):
        st.image(LOGO_IMAGE, use_column_width=True)
    else:
        st.markdown('<h1 class="sidebar-title">The Rendezvous</h1>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation Buttons
    if st.button("Dashboard", use_container_width=True, type="secondary" if st.session_state.page != "Dashboard" else "primary"): navigate_to("Dashboard")
    if st.button("Calendar", use_container_width=True, type="secondary" if st.session_state.page != "Calendar" else "primary"): navigate_to("Calendar")
    if st.button("Love Notes", use_container_width=True, type="secondary" if st.session_state.page != "Love Notes" else "primary"): navigate_to("Love Notes")

    st.markdown("---")
    with st.expander("Partner Names"):
        p1 = st.text_input("Partner 1", value=app_data['partner_names'][0])
        p2 = st.text_input("Partner 2", value=app_data['partner_names'][1])
        if st.button("Save Names", use_container_width=True):
            app_data['partner_names'] = [p1, p2]
            st.query_params["data"] = encode_data(app_data)
            st.toast("Names updated!")

# --- Main App Logic ---

if st.session_state.page == "Dashboard":
    st.title("Our Dashboard")

    # --- NEW: CONTEXT-AWARE NOTIFICATION SYSTEM ---
    unread_notifications = [ (i, notif) for i, notif in enumerate(app_data['notifications']) if not notif.get('read', False) ]

    if unread_notifications:
        st.subheader("🔔 New Alerts")
        for i, notif_tuple in enumerate(unread_notifications):
            original_index, notif = notif_tuple
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"{notif['message']}")
            with col2:
                # Determine button text and navigation target based on notification type
                button_text = ""
                target_page = ""
                if notif.get("type") == "note":
                    button_text = "Read Note"
                    target_page = "Love Notes"
                elif notif.get("type") == "booking":
                    button_text = "View Calendar"
                    target_page = "Calendar"

                if button_text and st.button(button_text, key=f"view_{i}", use_container_width=True):
                    app_data['notifications'][original_index]['read'] = True
                    st.query_params["data"] = encode_data(app_data)
                    navigate_to(target_page)
                    st.rerun()
        st.markdown("---")

    # URGENT BOOKING
    st.markdown('<div class="button-urgent">', unsafe_allow_html=True)
    if st.button("Book a Fuck", use_container_width=True):
        st.session_state.show_urgent_booking = not st.session_state.get('show_urgent_booking', False)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get('show_urgent_booking', False):
        with st.form("urgent_form"):
            st.subheader("Quick & Urgent Booking")
            booker = st.selectbox("Who's booking this?", app_data['partner_names'])
            col1, col2 = st.columns(2)
            date = col1.date_input("Date", value=datetime.date.today())
            time = col2.time_input("Time", value=datetime.time(21, 0))
            if st.form_submit_button("Confirm Booking 🔥", use_container_width=True):
                final_dt = datetime.datetime.combine(date, time)
                app_data['events'].append({ "title": "Urgent Rendezvous 🔥", "start": final_dt.isoformat(), "backgroundColor": "#E74C3C", "borderColor": "#C0392B", "booker": booker, "is_urgent": True })
                app_data['notifications'].append({ "message": f"{booker} booked an Urgent Rendezvous!", "read": False, "type": "booking" })
                st.query_params["data"] = encode_data(app_data)
                st.success(f"It's a date! Your partner will see the alert. 🔥")
                st.session_state.show_urgent_booking = False
                st.rerun()

    st.markdown("---")

    # SPLIT RENDEZVOUS DISPLAY WITH NEW WORDING
    now_str = datetime.datetime.now().isoformat()
    all_upcoming = sorted([e for e in app_data['events'] if e['start'] > now_str], key=lambda x: x['start'])
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
    with st.form("new_rendezvous", clear_on_submit=True):
        st.subheader("Plan a New Date")
        booker = st.selectbox("Who's booking this?", app_data['partner_names'])
        col1, col2 = st.columns(2)
        title = col1.text_input("Date Idea", placeholder="e.g., Dinner at our spot")
        date = col1.date_input("Date")
        start_time = col2.time_input("Time")
        if st.form_submit_button("Add to Calendar", use_container_width=True):
            if title:
                final_dt = datetime.datetime.combine(date, start_time)
                app_data['events'].append({ "title": title, "start": final_dt.isoformat(), "backgroundColor": "#D98880", "booker": booker, "is_urgent": False })
                app_data['notifications'].append({ "message": f"{booker} planned '{title}'!", "read": False, "type": "booking" })
                st.query_params["data"] = encode_data(app_data)
                st.toast(f"'{title}' added! Your partner will see the alert.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    calendar(events=app_data.get('events', []))

elif st.session_state.page == "Love Notes":
    st.title("Our Love Notes")
    with st.form("love_note_form", clear_on_submit=True):
        author = st.selectbox("From", app_data['partner_names'])
        message = st.text_area("Message", placeholder="Thinking of you...")
        if st.form_submit_button("Send Note", use_container_width=True):
            if message:
                app_data['love_notes'].append({"author": author, "message": message, "timestamp": datetime.datetime.now().isoformat()})
                app_data['notifications'].append({ "message": f"{author} left you a love note!", "read": False, "type": "note" })
                st.query_params["data"] = encode_data(app_data)
                st.toast("Note sent!")
    
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    if not app_data['love_notes']:
        st.info("The first note is yet to be written...")
    else:
        for note in reversed(app_data['love_notes']):
            with st.container(border=True):
                ts = datetime.datetime.fromisoformat(note['timestamp'])
                st.markdown(f"**From: {note['author']}** | <small>{ts.strftime('%b %d, %Y at %I:%M %p')}</small>", unsafe_allow_html=True)
                st.write(f"> *{note['message']}*")
