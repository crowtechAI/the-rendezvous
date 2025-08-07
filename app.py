import streamlit as st
from streamlit_calendar import calendar
import datetime
import json
import pytz
from collections import Counter

# --- App Configuration ---
st.set_page_config(
    page_title="The Rendezvous",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Database Connection ---
try:
    conn = st.connection("turso", type="sql")
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# --- Database Setup ---
def setup_database():
    with conn.session as s:
        s.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                title TEXT,
                start_time TEXT NOT NULL,
                backgroundColor TEXT,
                borderColor TEXT,
                booker TEXT,
                is_urgent BOOLEAN,
                attended BOOLEAN DEFAULT FALSE
            );
        """)
        s.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        if not s.execute("SELECT value FROM app_state WHERE key = 'partner_names';").fetchone():
            s.execute("INSERT INTO app_state (key, value) VALUES ('partner_names', ?);", (json.dumps(["Partner 1", "Partner 2"]),))
            s.commit()
setup_database()

# --- Data Helpers ---
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
        s.execute("""
            INSERT INTO events (title, start_time, backgroundColor, borderColor, booker, is_urgent)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (title, start_time.isoformat(), color, color, booker, is_urgent))
        s.commit()

def get_events():
    with conn.session as s:
        results = s.execute("SELECT id, title, start_time, backgroundColor, borderColor, booker, is_urgent, attended FROM events;").fetchall()
        return [
            {"id": r[0], "title": r[1], "start": r[2], "backgroundColor": r[3], "borderColor": r[4], "booker": r[5], "is_urgent": r[6], "attended": r[7]}
            for r in results
        ]

def mark_attended(event_id):
    with conn.session as s:
        s.execute("UPDATE events SET attended = 1 WHERE id = ?;", (event_id,))
        s.commit()

def delete_event(event_id):
    with conn.session as s:
        s.execute("DELETE FROM events WHERE id = ?;", (event_id,))
        s.commit()

# --- Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400;700&display=swap');
    .stApp { background-color: #FDF8F5; color: #34495E; font-family: 'Lato', sans-serif; }
    .block-container { max-width: 1200px; margin: auto; }
    h1 { font-family: 'Playfair Display', serif; color: #B05A5A; text-align: center; }
    .button-urgent button { background-color: #E74C3C; color: white; border: none; font-weight: bold; }
    .button-urgent button:hover { background-color: #C0392B; }
</style>
""", unsafe_allow_html=True)

# --- Navigation ---
if 'page' not in st.session_state: st.session_state.page = "Dashboard"
def navigate_to(page): st.session_state.page = page

# --- Sidebar ---
with st.sidebar:
    st.title("The Rendezvous")
    partner_names = get_partner_names()
    if st.button("Dashboard"): navigate_to("Dashboard")
    if st.button("Calendar"): navigate_to("Calendar")
    with st.expander("Partner Names"):
        p1 = st.text_input("Partner 1", partner_names[0])
        p2 = st.text_input("Partner 2", partner_names[1])
        if st.button("Save Names"): update_partner_names(p1, p2); st.rerun()

# --- Pages ---
if st.session_state.page == "Dashboard":
    st.title("Our Dashboard")

    if st.button("Book a Fuck 🔥"):
        st.session_state.show_urgent_booking = not st.session_state.get('show_urgent_booking', False)

    if st.session_state.get('show_urgent_booking', False):
        with st.form("urgent_form"):
            booker = st.selectbox("Who's booking this?", get_partner_names())
            col1, col2 = st.columns(2)
            date = col1.date_input("Date", value=datetime.date.today())
            time = col2.time_input("Time", value=datetime.time(21, 0))
            if st.form_submit_button("Confirm Booking 🔥"):
                dt = datetime.datetime.combine(date, time)
                add_event("Urgent Rendezvous 🔥", dt, booker, True)
                st.success("It's booked!")
                st.rerun()

    all_events = get_events()
    now = datetime.datetime.now()
    upcoming = [e for e in all_events if datetime.datetime.fromisoformat(e['start']) > now and not e['attended']]
    urgent = [e for e in upcoming if e['is_urgent']]
    planned = [e for e in upcoming if not e['is_urgent']]

    st.subheader("🔥 Urgent Bookings")
    for e in urgent:
        st.markdown(f"**{e['booker']}** booked for **{e['start']}**")
        if st.button(f"Mark Attended ({e['id']})", key=f"attend_{e['id']}"):
            mark_attended(e['id'])
            st.rerun()
        if st.button(f"Delete ({e['id']})", key=f"del_{e['id']}"):
            delete_event(e['id'])
            st.rerun()

    st.subheader("📅 Planned Dates")
    for e in planned:
        st.markdown(f"**{e['title']}** on {e['start']} by {e['booker']}")
        if st.button(f"Mark Attended ({e['id']})", key=f"attend_p_{e['id']}"):
            mark_attended(e['id'])
            st.rerun()
        if st.button(f"Delete ({e['id']})", key=f"del_p_{e['id']}"):
            delete_event(e['id'])
            st.rerun()

    st.subheader("📊 Stats")
    counter = Counter([e['booker'] for e in all_events])
    for k, v in counter.items():
        st.markdown(f"**{k}** booked {v} times")

if st.session_state.page == "Calendar":
    st.title("Our Calendar")

    with st.form("plan_form", clear_on_submit=True):
        booker = st.selectbox("Who's booking this?", get_partner_names())
        col1, col2 = st.columns(2)
        title = col1.text_input("Date Idea")
        date = col1.date_input("Date")
        time = col2.time_input("Time")
        if st.form_submit_button("Add to Calendar"):
            dt = datetime.datetime.combine(date, time)
            add_event(title, dt, booker, False)
            st.success("Date added!")
            st.rerun()

    calendar(events=get_events())
