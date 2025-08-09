import streamlit as st
from streamlit_calendar import calendar
import datetime
from datetime import timedelta, time
from pymongo import MongoClient
from bson import ObjectId
import os
import certifi
import pandas as pd
import altair as alt

# --- App Configuration ---
st.set_page_config(
    page_title="Our Connection Calendar",
    page_icon="💞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 1. CONFIGURATION & STYLING
# ==============================================================================

LOGO_IMAGE = "logo.png"

def get_css_variables():
    """Returns a dictionary of CSS variables based on the current Streamlit theme."""
    try:
        theme_base = st.get_option("theme.base")
    except:
        theme_base = "light"

    if theme_base == "dark":
        return {
            "--primary-color": "#BE9EC9", "--accent-color": "#87CEEB", "--danger": "#FF6B6B",
            "--background": "linear-gradient(135deg, #222222 0%, #333333 100%)",
            "--card-bg": "rgba(30, 30, 30, 0.9)", "--text-primary": "#f0f0f0",
            "--text-secondary": "#cccccc", "--button-bg": "#444444", "--button-hover": "#5A5A5A",
            "--partner1-color": "#FFB6C1", "--partner2-color": "#87CEFA",
        }
    else:  # light theme
        return {
            "--primary-color": "#BE9EC9", "--accent-color": "#87CEEB", "--danger": "#FF6B6B",
            "--background": "linear-gradient(135deg, #FDFBFB 0%, #EBEDEE 100%)",
            "--card-bg": "rgba(255, 255, 255, 0.9)", "--text-primary": "#333333",
            "--text-secondary": "#555555", "--button-bg": "#E8B4CB", "--button-hover": "#D498B5",
            "--partner1-color": "#FFB6C1", "--partner2-color": "#87CEFA",
        }

CALENDAR_OPTIONS = {
    "editable": "true", "navLinks": "true", "selectable": "true", "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,timeGridDay"
    }
}

def apply_global_styles():
    """Applies custom CSS to the entire Streamlit app."""
    css_vars = get_css_variables()
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&family=Playfair+Display:wght@400;700&display=swap');
        :root {{
            --primary-color: {css_vars['--primary-color']}; --accent-color: {css_vars['--accent-color']};
            --danger: {css_vars['--danger']}; --background: {css_vars['--background']};
            --card-bg: {css_vars['--card-bg']}; --text-primary: {css_vars['--text-primary']};
            --text-secondary: {css_vars['--text-secondary']}; --button-bg: {css_vars['--button-bg']};
            --button-hover: {css_vars['--button-hover']}; --partner1-color: {css_vars['--partner1-color']};
            --partner2-color: {css_vars['--partner2-color']};
        }}
        .stApp {{
            background: var(--background); color: var(--text-primary); font-family: 'Montserrat', sans-serif;
        }}
        h1, h2, h3 {{
            font-family: 'Playfair Display', serif; color: var(--text-primary); font-weight: 700;
        }}
        .stButton>button {{
            background-color: var(--button-bg); border: 1px solid var(--button-bg);
            border-radius: 25px; font-weight: 600; transition: all 0.3s ease; color: var(--text-primary);
        }}
        .stButton>button:hover {{
            background-color: var(--button-hover); border-color: var(--button-hover); transform: scale(1.02);
        }}
        .stButton>button:active {{ transform: scale(0.98); }}
        .emergency-button button {{
            background: var(--danger); border-color: #FF4D4D; color: white;
            animation: pulse-red 1.5s infinite; font-weight: bold;
        }}
        @keyframes pulse-red {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.7); }}
            70% {{ box-shadow: 0 0 0 12px rgba(255, 107, 107, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 107, 107, 0); }}
        }}
        .stForm, .stContainer, [data-testid="stDialog"], .card {{
            background: var(--card-bg); border-radius: 20px; padding: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1); color: var(--text-primary);
        }}
        .partner-badge {{
            display: inline-block; padding: 0.15em 0.6em; border-radius: 12px; font-weight: 600;
            font-size: 0.85em; color: var(--card-bg); user-select: none; margin-right: 0.5em;
        }}
        .partner1 {{ background-color: var(--partner1-color); }}
        .partner2 {{ background-color: var(--partner2-color); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

apply_global_styles()

# ==============================================================================
# 2. DATABASE HELPERS (with Caching)
# ==============================================================================

@st.cache_resource
def init_connection():
    """Initializes and returns a connection to MongoDB."""
    try:
        client = MongoClient(st.secrets["mongo_uri"], tlsCAFile=certifi.where())
        return client
    except Exception as e:
        st.error(f"Failed to connect to MongoDB. Check secrets and IP Access List. Error: {e}")
        st.stop()

@st.cache_resource
def get_db():
    """Returns the database instance."""
    return init_connection().get_database("rendezvous")

def setup_database():
    """Sets up initial database state and indexes if they don't exist."""
    db = get_db()
    if db.app_state.count_documents({"key": "partner_names"}) == 0:
        db.app_state.insert_one({"key": "partner_names", "value": ["Partner 1", "Partner 2"]})
    db.love_notes.create_index([("timestamp", -1)])
    db.moods.create_index([("partner", 1), ("date", -1)])

setup_database()

@st.cache_data(ttl=60)
def get_partner_names():
    doc = get_db().app_state.find_one({"key": "partner_names"})
    return doc['value'] if doc else ["Partner 1", "Partner 2"]

def update_partner_names(p1, p2):
    get_db().app_state.update_one({"key": "partner_names"}, {"$set": {"value": [p1, p2]}}, upsert=True)
    st.cache_data.clear()

def add_event(title, start_time, booker, is_spontaneous, event_type, partner_colors):
    base_colors = {
        "intimate": "#E8B4CB" if is_spontaneous else "#D498B5", "date": "#87CEEB",
        "self_care": "#98D8C8", "wellness": "#FFB3BA"
    }
    color = partner_colors.get(booker, base_colors.get(event_type, "#D498B5"))
    get_db().events.insert_one({
        "title": title, "start": start_time.isoformat(), "backgroundColor": color,
        "borderColor": color, "booker": booker, "is_spontaneous": is_spontaneous,
        "event_type": event_type
    })
    st.cache_data.clear()

def add_blockout(title, start_time, end_time, all_day, blockout_type):
    color_map = {"health": "#FF9999", "work": "#B0B0B0", "family": "#D4C5B9", "personal": "#A7C7E7", "general": "#C0C0C0"}
    color = color_map.get(blockout_type, "#C0C0C0")
    get_db().blockouts.insert_one({
        "title": title, "start": start_time.isoformat(), "end": end_time.isoformat(),
        "allDay": all_day, "backgroundColor": color, "borderColor": color,
        "display": "background", "blockout_type": blockout_type
    })
    st.cache_data.clear()

@st.cache_data(ttl=30)
def get_events():
    return [dict(event, _id=str(event['_id'])) for event in get_db().events.find()]

@st.cache_data(ttl=30)
def get_blockouts():
    return [dict(blockout, _id=str(blockout['_id'])) for blockout in get_db().blockouts.find()]

def check_for_overlap(new_start, new_end):
    for blockout in get_blockouts():
        block_start = datetime.datetime.fromisoformat(blockout['start'])
        block_end = datetime.datetime.fromisoformat(blockout['end'])
        if new_start < block_end and new_end > block_start:
            return blockout
    return None

def add_love_note(author, message):
    get_db().love_notes.insert_one({
        "author": author, "message": message, "timestamp": datetime.datetime.now(), "type": "love_note"
    })
    st.cache_data.clear()

@st.cache_data(ttl=10)
def get_all_love_notes():
    return list(get_db().love_notes.find({"type": "love_note"}).sort("timestamp", -1))

def send_emergency_alert(sender, urgency, message):
    get_db().love_notes.insert_one({
        "sender": sender, "timestamp": datetime.datetime.now(), "type": "emergency_alert",
        "urgency": urgency, "message": message, "seen": False
    })
    st.cache_data.clear()

@st.cache_data(ttl=5)
def get_unseen_emergency_alert():
    return get_db().love_notes.find_one({"type": "emergency_alert", "seen": False})

def mark_emergency_as_seen(alert_id):
    get_db().love_notes.update_one({"_id": ObjectId(alert_id)}, {"$set": {"seen": True}})
    st.cache_data.clear()

def log_mood(partner, date, energy, desire, stress, notes):
    get_db().moods.update_one(
        {"partner": partner, "date": date.isoformat()[:10]},
        {"$set": {"energy": energy, "desire": desire, "stress": stress, "notes": notes, "timestamp": datetime.datetime.now()}},
        upsert=True
    )
    st.cache_data.clear()

@st.cache_data(ttl=60)
def get_all_moods():
    return list(get_db().moods.find())

# ==============================================================================
# 3. UI HELPERS
# ==============================================================================

def get_partner_initials(name):
    return "".join([part[0] for part in name.split()]).upper()

def partner_colored_badge(partner_name, all_partner_names):
    initials = get_partner_initials(partner_name)
    color_class = "partner1" if partner_name == all_partner_names[0] else "partner2"
    return f'<span class="partner-badge {color_class}">{initials}</span>'

# ==============================================================================
# 4. MAIN APP LAYOUT & LOGIC
# ==============================================================================

# --- Get Partner Names for entire app ---
partner_names = get_partner_names()
p1_name, p2_name = partner_names
css_vars = get_css_variables()
partner_colors = {
    p1_name: css_vars["--partner1-color"],
    p2_name: css_vars["--partner2-color"]
}

# --- Sidebar for Settings ---
with st.sidebar:
    st.header("⚙️ Settings")
    p1_name_input = st.text_input("Partner 1 Name", value=p1_name)
    p2_name_input = st.text_input("Partner 2 Name", value=p2_name)
    if st.button("Save Names", use_container_width=True):
        update_partner_names(p1_name_input, p2_name_input)
        st.success("Names updated!")
        st.rerun()

# --- Main Header ---
col1, col2 = st.columns([3, 1])
with col1:
    if os.path.exists(LOGO_IMAGE):
        st.image(LOGO_IMAGE, width=180)
    else:
        st.title("Our Connection Calendar")
with col2:
    st.write("")
    st.markdown('<div class="emergency-button">', unsafe_allow_html=True)
    if st.button("Emergency Connect 🔥", use_container_width=True):
        st.session_state.show_emergency_modal = True
    st.markdown('</div>', unsafe_allow_html=True)

# --- Emergency Modal Logic ---
if 'show_emergency_modal' not in st.session_state:
    st.session_state.show_emergency_modal = False
if st.session_state.show_emergency_modal:
    @st.dialog("🚨 Break Glass In Case of Emergency 🚨")
    def show_emergency_dialog():
        st.markdown("Send a **high-priority alert** to your partner when you feel a strong, immediate need to connect.")
        sender = st.selectbox("This alert is from:", partner_names, key="emergency_sender")
        urgency = st.radio("What's the urgency?",
                           ["💕 **Thinking of you...** let's connect soon.", "🔥 **Urgent:** I need you now."], index=1)
        message = st.text_input("Optional message:", placeholder="e.g., 'Had a tough day.'")
        if st.button("SEND ALERT", use_container_width=True, type="primary"):
            send_emergency_alert(sender, urgency, message)
            st.session_state.show_emergency_modal = False
            st.rerun()
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_emergency_modal = False
            st.rerun()
    show_emergency_dialog()

# --- Display Active Emergency Alert Banner ---
active_alert = get_unseen_emergency_alert()
if active_alert:
    sender = active_alert.get('sender', 'Your partner')
    alert_id = active_alert.get('_id')
    urgency_msg = active_alert.get('urgency', 'Your partner wants to connect!')
    st.error(f"🚨 **HIGH PRIORITY ALERT!** {urgency_msg.replace('**', '')} - Sent by {sender}", icon="🔥")
    if st.button(f"I see it! Clear Alert", key=f"clear_alert_{alert_id}", use_container_width=True):
        mark_emergency_as_seen(alert_id)
        st.success("Alert cleared. Time to connect. 😉")
        st.rerun()
    st.markdown("---")

# --- Main App Tabs ---
dashboard_tab, calendar_tab, wellness_tab, notes_tab = st.tabs(
    ["🏡 Dashboard", "📅 Our Calendar", "🌿 Our Wellness", "💌 Messages"]
)

# ==============================================================================
# TAB 1: DASHBOARD
# ==============================================================================
with dashboard_tab:
    st.header("Today's Dashboard")
    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("✨ Feeling Spontaneous?")
        if st.button("Send a Spontaneous Invitation", use_container_width=True):
            st.session_state.show_spontaneous_request = not st.session_state.get('show_spontaneous_request', False)

    if st.session_state.get('show_spontaneous_request', False):
        with st.form("spontaneous_form"):
            st.subheader("Create Your Invitation")
            requester = st.selectbox("This invitation is from", partner_names)
            vibe = st.text_input("What's the vibe?", placeholder="e.g., Passionate & Intense, Playful & Fun")
            timing = st.selectbox("When?", ["Sometime tonight", "Soon", "This afternoon", "Tomorrow evening", "This weekend"])
            if st.form_submit_button("Send Invitation 💕", use_container_width=True):
                planned_time = datetime.datetime.now()
                if "tonight" in timing.lower(): planned_time = planned_time.replace(hour=21, minute=0)
                elif "tomorrow" in timing.lower(): planned_time += timedelta(days=1)
                
                if check_for_overlap(planned_time, planned_time + timedelta(hours=2)):
                    st.error("That time conflicts with a blocked-out period.")
                else:
                    add_event(f"Spontaneous: {vibe}", planned_time, requester, True, "intimate", partner_colors)
                    st.success("Your invitation has been sent! 💕✨")
                    st.session_state.show_spontaneous_request = False
                    st.rerun()

    with col2:
        st.subheader("🗓️ Upcoming Time Together")
        all_upcoming = sorted(
            [e for e in get_events() if datetime.datetime.fromisoformat(e['start']) > datetime.datetime.now()],
            key=lambda x: x['start']
        )
        if not all_upcoming:
            st.info("The calendar is open! Time to plan your next connection.")
        else:
            for event in all_upcoming[:3]:
                with st.container(border=True):
                    event_date = datetime.datetime.fromisoformat(event['start'])
                    icon = "🔥" if event.get("is_spontaneous") else "💕"
                    booker = event.get('booker', 'Unknown')
                    badge = partner_colored_badge(booker, partner_names)
                    st.markdown(
                        f"{badge} **{icon} {event['title']}**<br>"
                        f"_{event_date.strftime('%A, %b %d at %I:%M %p')}_", unsafe_allow_html=True
                    )

# ==============================================================================
# TAB 2: CALENDAR
# ==============================================================================
with calendar_tab:
    st.header("Our Shared Calendar")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("📅 Plan Together Time", expanded=True):
            with st.form("new_date", clear_on_submit=True):
                planner = st.selectbox("Who's planning this?", partner_names)
                event_title = st.text_input("Event Title", placeholder="E.g. Date Night")
                event_type = st.selectbox("Event Type", ["intimate", "date", "self_care", "wellness"])
                start_dt = st.date_input("Date", value=datetime.date.today())
                start_time = st.time_input("Time", value=time(hour=20, minute=0))
                duration = st.slider("Duration (hours)", 0.5, 6.0, 2.0, 0.5)
                if st.form_submit_button("Add Event", use_container_width=True):
                    start_datetime = datetime.datetime.combine(start_dt, start_time)
                    end_datetime = start_datetime + timedelta(hours=duration)
                    if check_for_overlap(start_datetime, end_datetime):
                        st.error("This event conflicts with a blocked-out period.")
                    else:
                        add_event(event_title, start_datetime, planner, False, event_type, partner_colors)
                        st.success("Event added!"); st.rerun()

    with col2:
        with st.expander("📵 Block Out Time", expanded=True):
            with st.form("new_blockout", clear_on_submit=True):
                blockout_title = st.text_input("Blockout Title", placeholder="E.g. Work Project")
                blockout_type = st.selectbox("Blockout Type", ["general", "health", "work", "family", "personal"])
                start_block_date = st.date_input("Start Date", value=datetime.date.today(), key='bsd')
                start_block_time = st.time_input("Start Time", value=time(hour=9), key='bst')
                end_block_date = st.date_input("End Date", value=datetime.date.today(), key='bed')
                end_block_time = st.time_input("End Time", value=time(hour=17), key='bet')
                if st.form_submit_button("Add Blockout", use_container_width=True):
                    start_dt = datetime.datetime.combine(start_block_date, start_block_time)
                    end_dt = datetime.datetime.combine(end_block_date, end_block_time)
                    if start_dt >= end_dt:
                        st.error("End time must be after start time.")
                    else:
                        add_blockout(blockout_title, start_dt, end_dt, False, blockout_type)
                        st.success("Blockout added!"); st.rerun()

    st.markdown("---")
    calendar(events=get_events() + get_blockouts(), options=CALENDAR_OPTIONS)

# ==============================================================================
# TAB 3: WELLNESS
# ==============================================================================
with wellness_tab:
    st.header("🌿 Wellness Hub")
    st.markdown("A space to check in with yourselves and each other.")
    st.markdown("---")
    col1, col2 = st.columns(2)
    for i, partner in enumerate(partner_names):
        with col1 if i == 0 else col2:
            with st.container(border=True):
                st.subheader(f"Log for {partner}")
                today = datetime.date.today()
                with st.form(f"mood_form_{partner}", clear_on_submit=True):
                    energy = st.slider("Energy Level", 0, 10, 5, key=f"en_{partner}")
                    desire = st.slider("Desire Level", 0, 10, 5, key=f"de_{partner}")
                    stress = st.slider("Stress Level (inverted)", 0, 10, 5, key=f"st_{partner}", help="0=high stress, 10=no stress")
                    notes = st.text_area("Notes (optional)", key=f"no_{partner}", placeholder="How are you feeling?")
                    if st.form_submit_button("Save Wellness Data", use_container_width=True):
                        log_mood(partner, today, energy, desire, stress, notes)
                        st.success(f"Wellness data saved for {partner}!"); st.rerun()

    st.markdown("---")
    st.header("Wellness Trends")
    mood_data = get_all_moods()
    if not mood_data:
        st.info("Log some wellness data above to see your trends over time!")
    else:
        df = pd.DataFrame(mood_data)
        df['date'] = pd.to_datetime(df['date'])
        df_melted = df.melt(id_vars=['date', 'partner'], value_vars=['energy', 'desire', 'stress'],
                            var_name='metric', value_name='level')
        chart = alt.Chart(df_melted).mark_line(point=True).encode(
            x=alt.X('date:T', title='Date'), y=alt.Y('level:Q', title='Level (0-10)'),
            color=alt.Color('partner:N', title='Partner'), strokeDash=alt.StrokeDash('metric:N', title='Metric'),
            tooltip=['date:T', 'partner:N', 'metric:N', 'level:Q']
        ).interactive().properties(title='Our Wellness Journey Over Time')
        st.altair_chart(chart, use_container_width=True)

# ==============================================================================
# TAB 4: MESSAGES
# ==============================================================================
with notes_tab:
    st.header("💌 Love Notes & Messages")
    st.markdown("---")
    with st.expander("💌 Send a new message", expanded=True):
        with st.form("new_love_note", clear_on_submit=True):
            author = st.selectbox("Who's writing?", partner_names)
            message = st.text_area("Your Message", max_chars=1500, placeholder="Write something sweet, loving, or spontaneous!")
            if st.form_submit_button("Send Message", use_container_width=True):
                if message.strip():
                    add_love_note(author, message.strip())
                    st.success(f"Message sent!"); st.rerun()
                else:
                    st.error("Message cannot be empty.")

    st.markdown("---")
    st.subheader("Our Message History")
    messages = get_all_love_notes()
    if not messages:
        st.info("No messages yet. Start by sending one above!")
    else:
        for msg in messages:
            with st.container(border=True):
                author = msg.get("author", "Unknown")
                date_str = msg.get("timestamp", datetime.datetime.now()).strftime("%b %d, %Y at %I:%M %p")
                badge = partner_colored_badge(author, partner_names)
                st.markdown(f"{badge} **{author}** _wrote on {date_str}_:", unsafe_allow_html=True)
                st.markdown(f"> {msg.get('message')}")
