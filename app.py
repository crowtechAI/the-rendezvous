import streamlit as st
from streamlit_calendar import calendar
import datetime
import json

# --- App Configuration ---
st.set_page_config(
    page_title="The Rendezvous",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Database Connection & Initialization ---
# This establishes a connection to the Turso database defined in your Streamlit Secrets.
try:
    conn = st.connection("turso", type="sql")
except Exception as e:
    st.error(f"Failed to connect to the database. Please check your Streamlit Secrets. Error: {e}")
    st.stop()


def setup_database():
    """Creates the necessary tables if they don't already exist."""
    with conn.session as s:
        s.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                title TEXT,
                start_time TEXT NOT NULL,
                backgroundColor TEXT,
                borderColor TEXT,
                booker TEXT,
                is_urgent BOOLEAN
            );
        """)
        s.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Check if partner names are set, if not, insert defaults
        partner_names = s.execute("SELECT value FROM app_state WHERE key = 'partner_names';").fetchone()
        if not partner_names:
            default_partners = json.dumps(["Partner 1", "Partner 2"])
            s.execute("INSERT INTO app_state (key, value) VALUES ('partner_names', ?);", (default_partners,))
            s.commit()

# Run the setup once at the start
setup_database()

# --- Data Helper Functions (to interact with the database) ---
def get_partner_names():
    with conn.session as s:
        result = s.execute("SELECT value FROM app_state WHERE key = 'partner_names';").fetchone()
        return json.loads(result[0]) if result else ["Partner 1", "Partner 2"]

def update_partner_names(p1, p2):
    with conn.session as s:
        s.execute("REPLACE INTO app_state (key, value) VALUES ('partner_names', ?);", (json.dumps([p1, p2]),))
        s.commit()

def add_event(title, start_time, booker, is_urgent):
    color = "#E74C3C" if is_urgent else "#D98880"
    with conn.session as s:
        s.execute(
            "INSERT INTO events (title, start_time, backgroundColor, borderColor, booker, is_urgent) VALUES (?, ?, ?, ?, ?, ?);",
            (title, start_time.isoformat(), color, color, booker, is_urgent)
        )
        s.commit()

def get_events():
    with conn.session as s:
        results = s.execute("SELECT title, start_time, backgroundColor, borderColor, booker, is_urgent FROM events;").fetchall()
        return [
            {"title": r[0], "start": r[1], "backgroundColor": r[2], "borderColor": r[3], "booker": r[4], "is_urgent": r[5]}
            for r in results
        ]

# --- Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400;700&display=swap');
    .stApp { background-color: #FDF8F5; color: #34495E; font-family: 'Lato', sans-serif; }
    .block-container { max-width: 1200px; padding-top: 2rem; padding-bottom: 2rem; margin: auto; }
    h1 { font-family: 'Playfair Display', serif; color: #B05A5A; text-align: center; }
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
    st.title("The Rendezvous")
    st.markdown("---")
    partner_names = get_partner_names() # Fetch names for the sidebar
    if st.button("Dashboard", use_container_width=True, type="secondary" if st.session_state.page != "Dashboard" else "primary"): navigate_to("Dashboard")
    if st.button("Calendar", use_container_width=True, type="secondary" if st.session_state.page != "Calendar" else "primary"): navigate_to("Calendar")
    st.markdown("---")
    with st.expander("Partner Names"):
        p1 = st.text_input("Partner 1", value=partner_names[0])
        p2 = st.text_input("Partner 2", value=partner_names[1])
        if st.button("Save Names", use_container_width=True):
            update_partner_names(p1, p2)
            st.toast("Names updated!")
            st.rerun()

# --- Main App Logic ---

if st.session_state.page == "Dashboard":
    st.title("Our Dashboard")
    st.markdown("---")

    # URGENT BOOKING
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
                add_event(title="Urgent Rendezvous 🔥", start_time=final_dt, booker=booker, is_urgent=True)
                st.success(f"It's a date! 🔥")
                st.session_state.show_urgent_booking = False
                st.rerun()

    st.markdown("---")

    # SPLIT RENDEZVOUS DISPLAY
    now = datetime.datetime.now()
    all_events = get_events()
    all_upcoming = sorted([e for e in all_events if datetime.datetime.fromisoformat(e['start']) > now], key=lambda x: x['start'])
    
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
        booker = st.selectbox("Who's booking this?", get_partner_names())
        col1, col2 = st.columns(2)
        title = col1.text_input("Date Idea", placeholder="e.g., Dinner at our spot")
        date = col1.date_input("Date")
        start_time = col2.time_input("Time")
        if st.form_submit_button("Add to Calendar", use_container_width=True):
            if title:
                final_dt = datetime.datetime.combine(date, start_time)
                add_event(title=title, start_time=final_dt, booker=booker, is_urgent=False)
                st.toast(f"'{title}' added!")
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    calendar_events = get_events() # Fetch events for the calendar component
    # The calendar component needs 'start' not 'start_time'
    for event in calendar_events:
        event['start'] = event.pop('start_time')
    calendar(events=calendar_events)
