"""
Monika's To-Do Lists - a colourful, easy To-Do List app built with Python + Streamlit only.

How to run:
    1) Install once:  pip install --upgrade streamlit   (type it in Command Prompt / Terminal)
    2) Open this file in IDLE and press F5  (or run:  streamlit run todo_app.py)

Your tasks are saved automatically in a file called tasks.json (next to this file).
"""
import calendar
import html
import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from string import Template

import streamlit as st
from streamlit import runtime

# ---------------------------------------------------------------------
# Run from IDLE: press F5 and this block starts Streamlit for you.
# (When Streamlit itself is running the file, this block is skipped.)
# ---------------------------------------------------------------------
if not runtime.exists():
    import subprocess
    import sys
    import webbrowser

    command = [sys.executable, "-m", "streamlit", "run", __file__,
               "--server.headless=true", "--browser.gatherUsageStats=false",
               "--theme.primaryColor=#22c55e"]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    opened = False
    try:
        for line in process.stdout:
            print(line, end="")
            if not opened and "Local URL:" in line:
                webbrowser.open(line.split("Local URL:")[1].strip())
                opened = True
    except KeyboardInterrupt:
        pass
    finally:
        process.terminate()
    raise SystemExit

st.set_page_config(page_title="Monika's To-Do Lists", page_icon="😊", layout="wide")

# =====================================================================
# 1. SETTINGS  (change these lists to customise the app)
# =====================================================================
DATA_FILE = Path(__file__).parent / "tasks.json"
MAX_TITLE_LENGTH = 100

CATEGORIES = {
    "Study": "📚",
    "Personal": "🧑",
    "Work": "💼",
    "Shopping": "🛒",
    "Health": "💪",
    "Other": "📌",
}
CATEGORY_COLORS = {
    "Study": "#3b82f6", "Personal": "#ec4899", "Work": "#6366f1",
    "Shopping": "#f97316", "Health": "#10b981", "Other": "#64748b",
}
PRIORITIES = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}

# Easy choices for the due date, so nobody has to fiddle with a calendar
DUE_CHOICES = ["No due date", "Today", "Tomorrow", "In 3 days", "Next week", "Choose a date"]
DUE_OFFSETS = {"Today": 0, "Tomorrow": 1, "In 3 days": 3, "Next week": 7}

FEATURES = [
    "➕ Add, edit and delete tasks",
    "🎯 Priority: High, Medium, Low",
    "🗂️ Categories: Study, Work, Shopping...",
    "📅 Easy due dates: Today, Tomorrow...",
    "🔍 Search and filter",
    "✔️ Green tick when a task is done",
    "📊 Dashboard and progress bar",
    "⏰ Reminders for tasks that are due",
    "🗓️ Calendar view",
    "🌙 Dark and light mode",
    "💾 Saved automatically",
]
FEATURE_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"]

# =====================================================================
# 2. SAVING AND LOADING DATA  (a simple JSON file, no database needed)
# =====================================================================


def parse_date(text):
    """Turn '2026-10-05' into a date. Return None if it is empty or invalid."""
    try:
        return date.fromisoformat(text) if text else None
    except (ValueError, TypeError):
        return None


def load_tasks():
    """Read tasks.json. If it is missing or damaged, start with an empty list."""
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []

    tasks, seen_ids = [], set()
    for item in data:
        if not isinstance(item, dict) or not str(item.get("title", "")).strip():
            continue
        task_id = str(item.get("id") or uuid.uuid4().hex[:8])
        if task_id in seen_ids:  # every task needs its own id
            task_id = uuid.uuid4().hex[:8]
        seen_ids.add(task_id)
        tasks.append(
            {
                "id": task_id,
                "title": str(item["title"]).strip()[:MAX_TITLE_LENGTH],
                "category": item.get("category") if item.get("category") in CATEGORIES else "Other",
                "priority": item.get("priority") if item.get("priority") in PRIORITIES else "Medium",
                "due": item.get("due") if parse_date(item.get("due")) else None,
                "done": bool(item.get("done", False)),
            }
        )
    return tasks


def save_tasks():
    """Write the current tasks to tasks.json."""
    try:
        DATA_FILE.write_text(json.dumps(st.session_state.tasks, indent=2), encoding="utf-8")
    except OSError:
        st.session_state.flash = ("error", "Could not save your tasks to disk.")


# =====================================================================
# 3. SMALL HELPERS
# =====================================================================


def validate_title(title):
    """Return (clean_title, error_message). Rejects empty or too-long titles."""
    title = (title or "").strip()
    if not title:
        return None, "Please type a task name first. The box is empty."
    if len(title) > MAX_TITLE_LENGTH:
        return None, f"Task name must be {MAX_TITLE_LENGTH} characters or fewer."
    return title, None


def category_label(name):
    return name if name == "All" else f"{CATEGORIES[name]} {name}"


def priority_label(name):
    return name if name == "All" else f"{PRIORITIES[name]} {name}"


def due_from_choice(choice, picked):
    """Turn the 'When is it due?' choice into a date text like '2026-10-05' (or None)."""
    today = date.today()
    if choice in DUE_OFFSETS:
        return (today + timedelta(days=DUE_OFFSETS[choice])).isoformat()
    if choice == "Choose a date":
        return (picked or today).isoformat()
    return None


def find_task(task_id):
    return next((t for t in st.session_state.tasks if t["id"] == task_id), None)


def flash(kind, message):
    """Store a message to show above the 'Add task' box on the next refresh."""
    st.session_state.flash = (kind, message)


def due_badge(task):
    """A small coloured label for the due date (red when overdue, orange when due today)."""
    due = parse_date(task["due"])
    if not due:
        return ""
    text = f"📅 {due.strftime('%d %b %Y')}"
    color = "#64748b"
    if not task["done"]:
        if due < date.today():
            text, color = text + " · Overdue!", "#dc2626"
        elif due == date.today():
            text, color = text + " · Due today", "#ea580c"
    return f'<span class="badge" style="background:{color}">{text}</span>'


def task_card_html(task):
    """The pretty card for one task (used in the task list, reminders and calendar)."""
    title = html.escape(task["title"])
    category, priority = task["category"], task["priority"]
    if task["done"]:
        border = "#22c55e"
        heading = f'<span class="tick">✔</span><span class="title-done">{title}</span>'
    else:
        border = PRIORITY_COLORS[priority]
        heading = title
    return (
        f'<div class="task-card" style="border-left-color:{border};'
        f'background:linear-gradient(90deg,{border}30,transparent 55%),var(--card)">'
        f'<div class="task-title">{heading}</div>'
        f'<div class="badges">'
        f'<span class="badge" style="background:{CATEGORY_COLORS[category]}">{CATEGORIES[category]} {category}</span>'
        f'<span class="badge" style="background:{PRIORITY_COLORS[priority]}">{PRIORITIES[priority]} {priority}</span>'
        f'{due_badge(task)}</div></div>'
    )


# =====================================================================
# 4. ACTIONS  (called when a button is clicked)
# =====================================================================


def add_task():
    title, error = validate_title(st.session_state.new_title)
    if error:
        flash("error", error)
        return
    due = due_from_choice(st.session_state.new_when, st.session_state.get("new_date"))
    st.session_state.tasks.append(
        {
            "id": uuid.uuid4().hex[:8],
            "title": title,
            "category": st.session_state.new_category,
            "priority": st.session_state.new_priority,
            "due": due,
            "done": False,
        }
    )
    save_tasks()
    flash("success", f"Added: {title}")
    st.session_state.new_title = ""  # clear the box for the next task
    st.session_state.new_when = "No due date"


def toggle_task(task_id):
    task = find_task(task_id)
    if task:
        task["done"] = bool(st.session_state[f"chk_{task_id}"])
        save_tasks()
        if all(t["done"] for t in st.session_state.tasks):
            st.session_state.celebrate = True  # party time when everything is finished!


def delete_task(task_id):
    task = find_task(task_id)
    if task:
        st.session_state.tasks.remove(task)
        if st.session_state.editing == task_id:
            st.session_state.editing = None
        save_tasks()
        flash("success", "Task deleted.")


def start_edit(task_id):
    task = find_task(task_id)
    if not task:
        return
    st.session_state.editing = task_id
    # Pre-fill the edit box with the task's current values
    st.session_state[f"edit_title_{task_id}"] = task["title"]
    st.session_state[f"edit_category_{task_id}"] = task["category"]
    st.session_state[f"edit_priority_{task_id}"] = task["priority"]
    st.session_state[f"edit_when_{task_id}"] = "Choose a date" if task["due"] else "No due date"
    st.session_state[f"edit_date_{task_id}"] = parse_date(task["due"]) or date.today()


def save_edit(task_id):
    task = find_task(task_id)
    if not task:
        st.session_state.editing = None
        return
    title, error = validate_title(st.session_state[f"edit_title_{task_id}"])
    if error:
        flash("error", error)  # stay in edit mode so nothing is lost
        return
    task["title"] = title
    task["category"] = st.session_state[f"edit_category_{task_id}"]
    task["priority"] = st.session_state[f"edit_priority_{task_id}"]
    task["due"] = due_from_choice(st.session_state[f"edit_when_{task_id}"],
                                  st.session_state.get(f"edit_date_{task_id}"))
    st.session_state.editing = None
    save_tasks()
    flash("success", "Task updated.")


def cancel_edit():
    st.session_state.editing = None


def clear_completed():
    before = len(st.session_state.tasks)
    st.session_state.tasks = [t for t in st.session_state.tasks if not t["done"]]
    if not find_task(st.session_state.editing):
        st.session_state.editing = None
    st.session_state.confirm_clear = False
    save_tasks()
    flash("success", f"Removed {before - len(st.session_state.tasks)} completed task(s).")


# =====================================================================
# 5. LOOK AND FEEL  (colours, cards, dark / light mode)
# =====================================================================

CSS = Template(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, .stApp, .stApp button, .stApp input, .stApp textarea {
    font-family: 'Poppins', 'Segoe UI', system-ui, sans-serif; }
:root { --card: $card; }
.stApp { background: $bg; }
header[data-testid="stHeader"] { background: transparent; }
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stWidgetLabel"] p { color: $text; }
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p { color: $muted; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, $card, $bg); border-right: 3px solid #ec4899; }
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="input"] { background: $input !important; color: $text !important; }
.stApp button[kind="primary"], .stApp [data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #6366f1, #ec4899); border: 0; color: #ffffff; font-weight: 600; }
button[data-baseweb="tab"] { font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] { color: #ec4899; }
div[data-baseweb="tab-highlight"] { background: linear-gradient(90deg, #6366f1, #ec4899); height: 4px; }

/* ---------- Top banner + features ---------- */
.hero { background: linear-gradient(120deg, #4f46e5, #8b5cf6, #ec4899, #f43f5e, #4f46e5);
    background-size: 300% 300%; animation: flow 10s ease infinite; border-radius: 22px;
    padding: 26px 16px 28px 16px; text-align: center; margin-bottom: 14px;
    box-shadow: 0 10px 24px rgba(99, 102, 241, 0.35); }
@keyframes flow { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; } }
.stApp .hero h1, .stApp .hero .date { color: #ffffff; margin: 0; }
.hero h1 { font-size: 2.6rem; font-weight: 700; text-shadow: 0 3px 8px rgba(0, 0, 0, 0.25); }
.hero .date { margin-top: 8px; font-size: 1.05rem; }

/* ---------- The smiley face (drawn with CSS) ---------- */
.smiley { position: relative; width: 88px; height: 88px; margin: 0 auto 10px auto; border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #fff9b0, #ffd93b 60%, #ffb703);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3); animation: bounce 2s ease-in-out infinite; }
@keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-9px); } }
.smiley .eye { position: absolute; top: 28px; width: 11px; height: 16px; border-radius: 50%;
    background: #5b3a00; }
.smiley .el { left: 26px; }
.smiley .er { right: 26px; }
.smiley .mouth { position: absolute; left: 24px; right: 24px; top: 46px; height: 22px;
    border-bottom: 5px solid #5b3a00; border-radius: 0 0 60px 60px; }
.smiley .cheek { position: absolute; top: 48px; width: 14px; height: 9px; border-radius: 50%;
    background: rgba(255, 105, 135, 0.55); }
.smiley .cl { left: 9px; }
.smiley .cr { right: 9px; }
.features { background: $card; border: 1px solid $border; border-radius: 18px;
    padding: 14px 16px; text-align: center; margin-bottom: 18px; }
.features h3 { margin: 0 0 10px 0; background: linear-gradient(90deg, #6366f1, #ec4899, #f59e0b);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.features ul { list-style: none; padding: 0; margin: 0; display: flex;
    flex-wrap: wrap; justify-content: center; gap: 8px; }
.features li { background: $bg; border: 2px solid $border; border-radius: 999px;
    padding: 4px 14px; font-size: 0.88rem; }

/* ---------- Dashboard ---------- */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 14px; margin: 6px 0 14px 0; }
.stat { border-radius: 18px; padding: 16px 18px; text-align: center;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15); transition: transform 0.2s; }
.stat:hover { transform: translateY(-4px) scale(1.03); }
.stApp .stat, .stApp .stat div { color: #ffffff; }
.stat-icon { font-size: 1.6rem; }
.stat-num { font-size: 2.1rem; font-weight: 700; line-height: 1.1; }
.stat-label { font-size: 0.9rem; opacity: 0.95; }
.s-blue { background: linear-gradient(135deg, #3b82f6, #06b6d4); }
.s-green { background: linear-gradient(135deg, #22c55e, #10b981); }
.s-orange { background: linear-gradient(135deg, #f59e0b, #f97316); }
.s-purple { background: linear-gradient(135deg, #8b5cf6, #ec4899); }
.progress-box { background: $card; border: 1px solid $border; border-radius: 18px;
    padding: 14px 18px; margin-bottom: 16px; }
.progress-top { display: flex; justify-content: space-between; font-size: 1.05rem; margin-bottom: 8px; }
.bar { height: 18px; background: $bg; border: 1px solid $border; border-radius: 999px; overflow: hidden; }
.fill { height: 100%; background: linear-gradient(90deg, #22c55e, #84cc16, #facc15); border-radius: 999px; }
.cheer { margin-top: 8px; font-weight: 600; }

/* ---------- Task cards ---------- */
.task-card { background: $card; border: 1px solid $border; border-left: 8px solid #94a3b8;
    border-radius: 14px; padding: 10px 14px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); }
.task-title { font-size: 1.05rem; font-weight: 600; color: $text; }
.stApp .title-done { color: $muted; text-decoration: line-through; }
.tick { display: inline-flex; align-items: center; justify-content: center; width: 22px;
    height: 22px; border-radius: 50%; background: #22c55e; color: #ffffff; font-size: 0.8rem;
    margin-right: 8px; }
.badges { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px; }
.stApp .badge { color: #ffffff; font-size: 0.75rem; font-weight: 600; border-radius: 999px;
    padding: 2px 10px; }
.empty-box { background: $card; border: 2px dashed $border; border-radius: 18px;
    padding: 30px 16px; text-align: center; font-size: 1.1rem; }

/* ---------- Calendar ---------- */
.cal-title { text-align: center; font-size: 1.4rem; font-weight: 700; margin: 8px 0; }
table.cal { width: 100%; border-collapse: collapse; table-layout: fixed; }
table.cal th { padding: 8px; background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #ffffff; border: 1px solid $border; }
table.cal td { height: 96px; vertical-align: top; padding: 4px; background: $card;
    border: 1px solid $border; overflow: hidden; }
table.cal td.empty { background: transparent; }
table.cal td.today { outline: 3px solid #ec4899; outline-offset: -3px; }
.daynum { font-weight: 700; margin-bottom: 2px; }
.chip { font-size: 0.72rem; color: #ffffff; border-radius: 6px; padding: 1px 5px;
    margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.more { font-size: 0.72rem; color: $muted; }
</style>
"""
)

LIGHT = {"bg": "#f3f5fb", "card": "#ffffff", "text": "#1f2937", "muted": "#6b7280",
         "border": "#e2e8f0", "input": "#ffffff"}
DARK = {"bg": "#0f172a", "card": "#1e293b", "text": "#e5e7eb", "muted": "#94a3b8",
        "border": "#334155", "input": "#0f172a"}


def apply_theme(dark):
    st.markdown(CSS.substitute(DARK if dark else LIGHT), unsafe_allow_html=True)


# =====================================================================
# 6. PAGE SECTIONS
# =====================================================================


def render_header():
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    today_text = date.today().strftime("%A, %d %B %Y")
    items = "".join(
        f'<li style="border-color:{FEATURE_COLORS[i % len(FEATURE_COLORS)]};'
        f'background:{FEATURE_COLORS[i % len(FEATURE_COLORS)]}22">{html.escape(f)}</li>'
        for i, f in enumerate(FEATURES)
    )
    st.markdown(
        '<div class="hero">'
        '<div class="smiley"><div class="cheek cl"></div><div class="cheek cr"></div>'
        '<div class="eye el"></div><div class="eye er"></div><div class="mouth"></div></div>'
        "<h1>Monika's To-Do Lists</h1>"
        f'<div class="date">🌈 {greeting}! Today is {today_text} ✨</div></div>'
        f'<div class="features"><h3>✨ What this app can do</h3><ul>{items}</ul></div>',
        unsafe_allow_html=True,
    )


def cheer_message(total, percent):
    if total == 0:
        return "🚀 Add your first task below to get started!"
    if percent == 100:
        return "🎉 Amazing! Every task is done!"
    if percent >= 70:
        return "💪 Almost there, keep going!"
    if percent >= 30:
        return "🌟 Good progress, well done!"
    return "👣 Every big journey starts with one small step."


def stat_card(icon, label, value, color_class):
    return (f'<div class="stat {color_class}"><div class="stat-icon">{icon}</div>'
            f'<div class="stat-num">{value}</div><div class="stat-label">{label}</div></div>')


def render_dashboard(tasks):
    total = len(tasks)
    completed = sum(1 for t in tasks if t["done"])
    pending = total - completed
    percent = round(completed / total * 100) if total else 0

    st.markdown(
        '<div class="stats">'
        + stat_card("📋", "Total tasks", total, "s-blue")
        + stat_card("✅", "Completed", completed, "s-green")
        + stat_card("⏳", "Pending", pending, "s-orange")
        + stat_card("📈", "Completion", f"{percent}%", "s-purple")
        + "</div>"
        f'<div class="progress-box"><div class="progress-top">'
        f"<b>{completed}/{total} tasks completed</b><span><b>{percent}%</b></span></div>"
        f'<div class="bar" role="progressbar" aria-valuenow="{percent}" aria-valuemin="0" '
        f'aria-valuemax="100"><div class="fill" style="width:{percent}%"></div></div>'
        f'<div class="cheer">{cheer_message(total, percent)}</div></div>',
        unsafe_allow_html=True,
    )


def render_help():
    with st.expander("❓ New here? How to use this app (3 easy steps)"):
        st.markdown(
            "**1️⃣ Add a task:** type it in the box, choose a category, priority and date, "
            "then press **➕ Add task**.\n\n"
            "**2️⃣ Finish a task:** tick the box next to it. It gets a green ✔ and a line through it.\n\n"
            "**3️⃣ Change a task:** press ✏️ to edit it or 🗑️ to delete it.\n\n"
            "💡 Use the **sidebar on the left** to search, filter and switch dark mode."
        )


def show_flash():
    message = st.session_state.flash
    if message:
        kind, text = message
        if kind == "success":
            st.success(text)
        else:
            st.error(text)
        st.session_state.flash = None


def render_add_box():
    with st.container(border=True):
        st.markdown("### ➕ Add a new task")
        st.text_input("What do you want to do?", key="new_title", max_chars=MAX_TITLE_LENGTH,
                      placeholder="Example: Finish Python homework")
        a1, a2, a3, a4 = st.columns(4)
        a1.selectbox("Category", list(CATEGORIES), key="new_category", format_func=category_label)
        a2.selectbox("Priority", list(PRIORITIES), key="new_priority", format_func=priority_label)
        a3.selectbox("When is it due?", DUE_CHOICES, key="new_when")
        if st.session_state.new_when == "Choose a date":
            a4.date_input("Pick a date", key="new_date")
        st.button("➕ Add task", key="add_button", type="primary", on_click=add_task)


def render_edit_panel(task):
    task_id = task["id"]
    with st.container(border=True):
        st.markdown("**✏️ Edit this task**")
        st.text_input("Task name", key=f"edit_title_{task_id}", max_chars=MAX_TITLE_LENGTH)
        e1, e2, e3, e4 = st.columns(4)
        e1.selectbox("Category", list(CATEGORIES), key=f"edit_category_{task_id}",
                     format_func=category_label)
        e2.selectbox("Priority", list(PRIORITIES), key=f"edit_priority_{task_id}",
                     format_func=priority_label)
        e3.selectbox("When is it due?", DUE_CHOICES, key=f"edit_when_{task_id}")
        if st.session_state.get(f"edit_when_{task_id}") == "Choose a date":
            e4.date_input("Pick a date", key=f"edit_date_{task_id}")
        b1, b2, _ = st.columns([1, 1, 4])
        b1.button("💾 Save", key=f"save_{task_id}", type="primary",
                  on_click=save_edit, args=(task_id,))
        b2.button("Cancel", key=f"cancel_{task_id}", on_click=cancel_edit)


def render_task(task):
    task_id = task["id"]
    c_check, c_card, c_edit, c_del = st.columns([0.7, 7, 0.8, 0.8], vertical_alignment="center")
    c_check.checkbox("Done", value=task["done"], key=f"chk_{task_id}", help="Tick when finished",
                     on_change=toggle_task, args=(task_id,), label_visibility="collapsed")
    c_card.markdown(task_card_html(task), unsafe_allow_html=True)
    c_edit.button("✏️", key=f"edit_{task_id}", help="Edit this task",
                  on_click=start_edit, args=(task_id,))
    c_del.button("🗑️", key=f"del_{task_id}", help="Delete this task",
                 on_click=delete_task, args=(task_id,))
    if st.session_state.editing == task_id:
        render_edit_panel(task)


def filter_tasks(tasks, search, category, priority, status):
    query = search.strip().lower()
    result = []
    for t in tasks:
        if query and query not in t["title"].lower():
            continue
        if category != "All" and t["category"] != category:
            continue
        if priority != "All" and t["priority"] != priority:
            continue
        if status == "Pending" and t["done"]:
            continue
        if status == "Completed" and not t["done"]:
            continue
        result.append(t)
    # Pending first, then High priority first, then earliest due date
    return sorted(result, key=lambda t: (t["done"], PRIORITY_ORDER[t["priority"]],
                                         t["due"] or "9999-12-31", t["title"].lower()))


def render_task_list(tasks, search, category, priority, status):
    if not tasks:
        st.markdown('<div class="empty-box">🌱 No tasks yet.<br>Add your first task in the box above!</div>',
                    unsafe_allow_html=True)
        return
    visible = filter_tasks(tasks, search, category, priority, status)
    if not visible:
        st.warning("No tasks match your search or filters. Try changing the sidebar.")
        return
    st.caption(f"Showing {len(visible)} of {len(tasks)} tasks")
    for task in visible:
        render_task(task)

    completed = sum(1 for t in tasks if t["done"])
    if completed:
        with st.expander(f"🧹 Clean up ({completed} completed)"):
            st.checkbox("Yes, I want to remove all completed tasks", key="confirm_clear")
            st.button("🧹 Remove completed tasks", key="clear_button", on_click=clear_completed,
                      disabled=not st.session_state.get("confirm_clear", False))


def render_reminders(tasks):
    today = date.today()
    pending = [t for t in tasks if not t["done"]]
    with_due = sorted((t for t in pending if parse_date(t["due"])), key=lambda t: t["due"])

    groups = [
        ("🔴 Overdue", [t for t in with_due if parse_date(t["due"]) < today]),
        ("🟠 Due today", [t for t in with_due if parse_date(t["due"]) == today]),
        ("🔵 Coming up in the next 7 days",
         [t for t in with_due if today < parse_date(t["due"]) <= today + timedelta(days=7)]),
    ]

    shown_any = False
    for title, group in groups:
        if group:
            shown_any = True
            st.markdown(f"#### {title} ({len(group)})")
            for t in group:
                st.markdown(task_card_html(t), unsafe_allow_html=True)
    if not shown_any:
        st.success("🎉 No reminders right now. You're all caught up!")

    no_date = len(pending) - len(with_due)
    if no_date:
        st.caption(f"{no_date} pending task(s) have no due date. Add one to get reminders.")


def render_calendar(tasks):
    today = date.today()
    c1, c2 = st.columns(2)
    month_names = list(calendar.month_name)[1:]
    month = c1.selectbox("Month", list(range(1, 13)), index=today.month - 1, key="cal_month",
                         format_func=lambda m: month_names[m - 1])
    year = int(c2.number_input("Year", min_value=2000, max_value=2100, value=today.year,
                               step=1, key="cal_year"))

    by_day = {}
    for t in tasks:
        due = parse_date(t["due"])
        if due:
            by_day.setdefault(due, []).append(t)

    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    table = (f'<div class="cal-title">📅 {month_names[month - 1]} {year}</div>'
             '<table class="cal"><tr>' + "".join(f"<th>{d}</th>" for d in days) + "</tr>")
    for week in calendar.Calendar(firstweekday=6).monthdayscalendar(year, month):
        table += "<tr>"
        for day in week:
            if day == 0:
                table += '<td class="empty"></td>'
                continue
            current = date(year, month, day)
            day_tasks = by_day.get(current, [])
            chips = ""
            for t in day_tasks[:3]:
                color = "#22c55e" if t["done"] else PRIORITY_COLORS[t["priority"]]
                tick = "✔ " if t["done"] else ""
                chips += f'<div class="chip" style="background:{color}">{tick}{html.escape(t["title"])}</div>'
            if len(day_tasks) > 3:
                chips += f'<div class="more">+{len(day_tasks) - 3} more</div>'
            css_class = "today" if current == today else ""
            table += f'<td class="{css_class}"><div class="daynum">{day}</div>{chips}</td>'
        table += "</tr>"
    table += "</table>"
    st.markdown(table, unsafe_allow_html=True)
    st.caption("Colours: 🔴 high · 🟠 medium · 🟢 low priority · green with ✔ = completed. "
               "Today has a pink border.")

    st.markdown("#### 🔎 See the tasks for one day")
    picked = st.date_input("Pick a day", value=today, key="cal_pick")
    day_tasks = by_day.get(picked, [])
    if not day_tasks:
        st.info("No tasks are due on this day.")
    for t in day_tasks:
        st.markdown(task_card_html(t), unsafe_allow_html=True)


# =====================================================================
# 7. MAIN PROGRAM
# =====================================================================


def init_state():
    """Set up the values the app remembers between clicks."""
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks()
    defaults = {
        "editing": None, "flash": None, "dark_mode": False, "confirm_clear": False, "celebrate": False,
        "new_title": "", "new_category": "Study", "new_priority": "Medium",
        "new_when": "No due date", "new_date": date.today(),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def main():
    init_state()

    # Sidebar: appearance + search + filters
    st.sidebar.markdown("## 🎨 Look")
    dark = st.sidebar.toggle("🌙 Dark mode", key="dark_mode")
    st.sidebar.markdown("## 🔍 Find your tasks")
    search = st.sidebar.text_input("Search by name", placeholder="Type a word...")
    category = st.sidebar.selectbox("Category", ["All"] + list(CATEGORIES), format_func=category_label)
    priority = st.sidebar.selectbox("Priority", ["All"] + list(PRIORITIES), format_func=priority_label)
    status = st.sidebar.radio("Show", ["All", "Pending", "Completed"], horizontal=True)

    apply_theme(dark)
    render_header()

    tasks = st.session_state.tasks
    render_dashboard(tasks)
    render_help()
    show_flash()
    render_add_box()
    st.write("")

    tab_tasks, tab_reminders, tab_calendar = st.tabs(["📝 My Tasks", "⏰ Reminders", "📅 Calendar"])
    with tab_tasks:
        render_task_list(tasks, search, category, priority, status)
    with tab_reminders:
        render_reminders(tasks)
    with tab_calendar:
        render_calendar(tasks)

    if st.session_state.celebrate:
        st.balloons()
        st.session_state.celebrate = False

    st.caption("💾 Your tasks are saved automatically in tasks.json")


main()
