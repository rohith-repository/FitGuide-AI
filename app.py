"""FitGuide AI: a Streamlit dashboard with the original Flask routes."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import sqlite3

import requests
import streamlit as st
from flask import Flask, flash, redirect, render_template, request, url_for
from streamlit.runtime.scriptrunner import get_script_run_ctx


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("FITGUIDE_DB", BASE_DIR / "fitguide.db"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
GEMMA_MODEL = os.environ.get("GEMMA_MODEL", "gemma3:1b")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-development-key-change-me")

EXERCISES = [
    {
        "name": "Bodyweight Squat",
        "target": "Legs and glutes",
        "equipment": "None",
        "instructions": "Stand with feet about shoulder-width apart. Sit your hips back, then stand up with control.",
        "benefits": "Practices lower-body strength and everyday movement.",
        "difficulty": "Beginner",
    },
    {
        "name": "Wall Push-up",
        "target": "Chest and arms",
        "equipment": "Wall",
        "instructions": "Place hands on a wall at shoulder height. Bend your elbows toward the wall, then gently push away.",
        "benefits": "Builds upper-body strength with adjustable effort.",
        "difficulty": "Beginner",
    },
    {
        "name": "Glute Bridge",
        "target": "Glutes and hips",
        "equipment": "Mat or floor",
        "instructions": "Lie on your back with knees bent. Lift your hips comfortably, pause, then lower slowly.",
        "benefits": "Strengthens the hips and glutes.",
        "difficulty": "Beginner",
    },
    {
        "name": "Bird Dog",
        "target": "Core and back",
        "equipment": "Mat or floor",
        "instructions": "On your hands and knees, extend the opposite arm and leg without twisting. Return and switch sides.",
        "benefits": "Practices balance, coordination and trunk control.",
        "difficulty": "Beginner",
    },
    {
        "name": "Reverse Lunge",
        "target": "Legs and glutes",
        "equipment": "None",
        "instructions": "Step one foot back, bend both knees only as far as comfortable, then return to standing.",
        "benefits": "Builds single-leg strength and balance.",
        "difficulty": "Intermediate",
    },
    {
        "name": "Dumbbell Row",
        "target": "Back and arms",
        "equipment": "Dumbbells",
        "instructions": "Hinge forward with a comfortable, neutral back. Pull the weight toward your hip, then lower it.",
        "benefits": "Strengthens the upper back and arms.",
        "difficulty": "Intermediate",
    },
    {
        "name": "Plank",
        "target": "Core",
        "equipment": "Mat or floor",
        "instructions": "Keep elbows under shoulders and your body in a straight line. Stop when your form changes.",
        "benefits": "Practices core endurance and body control.",
        "difficulty": "Intermediate",
    },
    {
        "name": "Step Jacks",
        "target": "Full body and cardio",
        "equipment": "None",
        "instructions": "Step one foot out at a time while raising your arms. Keep the pace comfortable.",
        "benefits": "A low-impact way to add movement and raise your heart rate.",
        "difficulty": "Beginner",
    },
]

PLANS = {
    "Beginner": [
        ("Easy warm-up walk", "5 minutes"),
        ("Bodyweight Squat", "2 sets of 8"),
        ("Wall Push-up", "2 sets of 8"),
        ("Glute Bridge", "2 sets of 10"),
        ("Bird Dog", "2 sets of 6 per side"),
        ("Gentle cool-down", "5 minutes"),
    ],
    "Strength": [
        ("Easy warm-up", "5 minutes"),
        ("Bodyweight Squat", "3 sets of 8"),
        ("Wall Push-up", "3 sets of 8"),
        ("Dumbbell Row", "2 sets of 10"),
        ("Glute Bridge", "2 sets of 10"),
        ("Gentle cool-down", "5 minutes"),
    ],
    "Cardio": [
        ("Comfortable walk", "5 minutes"),
        ("Brisk walk or Step Jacks", "1 minute"),
        ("Easy pace", "2 minutes"),
        ("Repeat brisk/easy intervals", "4 rounds"),
        ("Slow walk", "5 minutes"),
    ],
    "Mobility": [
        ("Easy walk in place", "3 minutes"),
        ("Shoulder rolls", "8 each direction"),
        ("Sit-to-stand", "2 sets of 8"),
        ("Gentle standing hip stretch", "20 seconds each side"),
        ("Slow breathing", "2 minutes"),
    ],
}

NUTRITION_TIPS = [
    "Build meals around vegetables or fruit, whole grains and protein-rich foods.",
    "Drink water regularly, especially around activity. Needs vary with weather and exercise.",
    "Include protein sources such as beans, lentils, eggs, dairy, tofu, fish or lean meat.",
    "Rice, oats, potatoes and other carbohydrate foods can help fuel exercise.",
    "Sleep and recovery are part of fitness. Increase activity gradually and take rest days.",
    "Avoid extreme diets. Ask a qualified health professional for medical nutrition advice.",
]

GOALS = ("General fitness", "Build strength", "Cardio fitness", "Improve mobility")
LEVELS = ("Beginner", "Intermediate", "Advanced")
EQUIPMENT_OPTIONS = ("None", "Resistance bands", "Dumbbells", "Full gym")
BADGE_RULES = (
    (1, "First step", "Complete your first workout."),
    (5, "Finding a rhythm", "Complete 5 workouts."),
    (10, "Consistency champion", "Complete 10 workouts."),
)

PLAN_IMAGES = {
    "Beginner": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=1200&q=85",
    "Strength": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=1200&q=85",
    "Cardio": "https://images.unsplash.com/photo-1538805060514-97d9cc17730c?auto=format&fit=crop&w=1200&q=85",
    "Mobility": "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=1200&q=85",
}


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Open a SQLite connection and always close it after the query."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db() -> None:
    """Create the tables on the first run; existing entries are preserved."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY,
                workout_date TEXT NOT NULL,
                activity TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                notes TEXT DEFAULT ''
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY,
                measure_date TEXT NOT NULL,
                weight REAL,
                notes TEXT DEFAULT ''
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                author TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )


def get_stats() -> dict[str, object]:
    """Summarize workout history, points, streak and unlocked badges."""
    with get_db() as connection:
        logs = connection.execute(
            "SELECT * FROM workouts ORDER BY workout_date DESC, id DESC"
        ).fetchall()

    workout_dates = {
        row["workout_date"]
        for row in logs
        if row["workout_date"] <= date.today().isoformat()
    }
    streak = 0
    current_day = date.today()
    if current_day.isoformat() not in workout_dates:
        current_day -= timedelta(days=1)
    while current_day.isoformat() in workout_dates:
        streak += 1
        current_day -= timedelta(days=1)

    completed_count = len(logs)
    badges = [
        {"name": name, "description": description}
        for count, name, description in BADGE_RULES
        if completed_count >= count
    ]
    if streak >= 3:
        badges.append({"name": "Three-day streak", "description": "Move on 3 days in a row."})
    if streak >= 7:
        badges.append({"name": "Week of movement", "description": "Move on 7 days in a row."})

    return {
        "logs": logs,
        "sessions": completed_count,
        "minutes": sum(row["minutes"] for row in logs),
        "points": completed_count * 10,
        "streak": streak,
        "badges": badges,
    }


def get_page_data(**extra: object) -> dict[str, object]:
    """Load the data shared by the dashboard and its form results."""
    with get_db() as connection:
        measurements = connection.execute(
            "SELECT * FROM measurements ORDER BY measure_date DESC, id DESC LIMIT 10"
        ).fetchall()
        posts = connection.execute(
            "SELECT * FROM posts ORDER BY id DESC LIMIT 20"
        ).fetchall()

    data: dict[str, object] = {
        "stats": get_stats(),
        "exercises": EXERCISES,
        "plans": PLANS,
        "nutrition_tips": NUTRITION_TIPS,
        "measurements": measurements,
        "latest_weight": next(
            (row["weight"] for row in measurements if row["weight"] is not None), None
        ),
        "posts": posts,
        "today": date.today().isoformat(),
        "recommendation": None,
        "generated_plan": None,
    }
    data.update(extra)
    return data


def render_dashboard(**extra: object) -> str:
    return render_template("index.html", **get_page_data(**extra))


def valid_date(value: str) -> date:
    """Parse a date field and reject dates in the future."""
    parsed = date.fromisoformat(value)
    if parsed > date.today():
        raise ValueError("The date cannot be in the future.")
    return parsed


def select_value(field: str, options: tuple[str, ...], default: str) -> str:
    value = request.form.get(field, default).strip()
    if value not in options:
        raise ValueError(f"Choose a valid {field.replace('_', ' ')}.")
    return value


@app.route("/")
def index() -> str:
    init_db()
    return render_dashboard()


@app.route("/log-workout", methods=["POST"])
def log_workout():
    activity = request.form.get("activity", "").strip()[:100]
    notes = request.form.get("notes", "").strip()[:500]
    try:
        workout_day = valid_date(request.form.get("workout_date", ""))
        minutes = int(request.form.get("minutes", "0"))
        if not activity or not 1 <= minutes <= 600:
            raise ValueError("Enter an activity and a duration from 1 to 600 minutes.")
    except ValueError:
        flash(
            "Enter an activity, a date no later than today, and a duration from 1 to 600 minutes.",
            "error",
        )
        return redirect(url_for("index") + "#progress")

    with get_db() as connection:
        connection.execute(
            "INSERT INTO workouts(workout_date, activity, minutes, notes) VALUES (?, ?, ?, ?)",
            (workout_day.isoformat(), activity, minutes, notes),
        )
    flash("Workout saved! You earned 10 Fit points.", "success")
    return redirect(url_for("index") + "#progress")


@app.route("/log-measurement", methods=["POST"])
def log_measurement():
    notes = request.form.get("measurement_notes", "").strip()[:300]
    raw_weight = request.form.get("weight", "").strip()
    try:
        measure_day = valid_date(request.form.get("measure_date", ""))
        weight = float(raw_weight) if raw_weight else None
        if (weight is not None and not 1 <= weight <= 500) or (
            weight is None and not notes
        ):
            raise ValueError("Add a weight or a progress note.")
    except ValueError:
        flash(
            "Enter a valid weight from 1 to 500 kg, or add a progress note, and use today's or an earlier date.",
            "error",
        )
        return redirect(url_for("index") + "#progress")

    with get_db() as connection:
        connection.execute(
            "INSERT INTO measurements(measure_date, weight, notes) VALUES (?, ?, ?)",
            (measure_day.isoformat(), weight, notes),
        )
    flash("Progress entry saved.", "success")
    return redirect(url_for("index") + "#progress")


@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        goal = select_value("goal", GOALS, GOALS[0])
        level = select_value("level", LEVELS, LEVELS[0])
        equipment = select_value("equipment", EQUIPMENT_OPTIONS, EQUIPMENT_OPTIONS[0])
        minutes = int(request.form.get("minutes", "20"))
        if minutes not in (10, 20, 30, 45):
            raise ValueError("Choose a listed session length.")
    except ValueError:
        flash("Choose valid recommendation options and a listed session length.", "error")
        return redirect(url_for("index") + "#recommendations")

    if goal == "Cardio fitness":
        focus = "a comfortable walk or low-impact cardio intervals"
    elif goal == "Build strength":
        focus = "controlled strength exercises such as squats, wall push-ups and bridges"
    elif goal == "Improve mobility":
        focus = "gentle mobility movements and comfortable range-of-motion practice"
    else:
        focus = "a balanced mix of easy cardio and full-body movements"

    effort = "beginner-friendly" if level == "Beginner" else f"appropriate for an {level.lower()} exerciser"
    if equipment == "None":
        equipment_advice = "Choose bodyweight movements that need no equipment."
    else:
        equipment_advice = f"If useful, include your {equipment.lower()}."
    recommendation = (
        f"Try {minutes} minutes of {focus}. Keep it {effort}, include an easy warm-up "
        f"and cool-down, and rest as needed. {equipment_advice}"
    )
    return render_dashboard(recommendation=recommendation)


def generate_ai_plan(goal: str, level: str, equipment: str, minutes: int, days: int) -> str:
    prompt = (
        "Create a cautious, beginner-friendly weekly workout plan. "
        f"Goal: {goal}. Experience: {level}. Equipment available: {equipment}. "
        f"Session length: {minutes} minutes. Days per week: {days}. "
        "Include a warm-up, exercises with sets/repetitions or time, rest guidance, "
        "and a cool-down. Offer low-impact alternatives. Do not give medical advice. "
        "Remind the reader to stop for pain, dizziness, chest pain, or unusual shortness of breath."
    )
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": GEMMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        output = (
            f"Cannot connect to Ollama at {OLLAMA_URL}. Start Ollama and make sure "
            f"the {GEMMA_MODEL} model is installed."
        )
    except requests.exceptions.Timeout:
        output = "Gemma took too long to respond. Try again or choose a smaller model."
    except requests.exceptions.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        output = f"Ollama returned HTTP {status}. Check that the model name is correct."
    except requests.exceptions.RequestException as error:
        output = f"Could not contact Ollama: {error}"
    else:
        try:
            response_data = response.json()
        except ValueError:
            output = "Ollama returned an unreadable response. Check the Ollama service and try again."
        else:
            if not isinstance(response_data, dict):
                output = "Ollama returned an unexpected response format. Check the Ollama service and try again."
            else:
                output = str(response_data.get("response", "")).strip()
                if response_data.get("error"):
                    output = f"Ollama error: {response_data['error']}"
                elif not output:
                    output = "Gemma returned an empty plan. Please try again."
    return output


@app.route("/generate-plan", methods=["GET", "POST"])
def generate_plan():
    if request.method == "GET":
        return redirect(url_for("index") + "#ai-coach")

    try:
        goal = select_value("ai_goal", GOALS, GOALS[0])
        level = select_value("ai_level", LEVELS, LEVELS[0])
        equipment = select_value("ai_equipment", EQUIPMENT_OPTIONS, EQUIPMENT_OPTIONS[0])
        minutes = int(request.form.get("ai_minutes", "30"))
        days = int(request.form.get("ai_days", "3"))
        if not 10 <= minutes <= 120 or not 1 <= days <= 7:
            raise ValueError("Choose a session length from 10 to 120 and 1 to 7 days.")
    except ValueError:
        flash("Choose valid workout options, session length and days per week.", "error")
        return redirect(url_for("index") + "#ai-coach")
    output = generate_ai_plan(goal, level, equipment, minutes, days)
    return render_dashboard(generated_plan=output)


@app.route("/community", methods=["POST"])
def community():
    author = request.form.get("author", "").strip()[:40] or "Fitness friend"
    message = request.form.get("message", "").strip()[:500]
    if not message:
        flash("Write a message before posting.", "error")
        return redirect(url_for("index") + "#community")

    with get_db() as connection:
        connection.execute(
            "INSERT INTO posts(author, message, created_at) VALUES (?, ?, ?)",
            (author, message, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
    flash("Post saved to this local demo.", "success")
    return redirect(url_for("index") + "#community")


def inject_streamlit_styles() -> None:
    """Apply the dark fitness theme and reusable card styling."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
        :root {
            --fit-navy: #0F172A;
            --fit-green: #22C55E;
            --fit-blue: #3B82F6;
            --fit-muted: #94A3B8;
        }
        .stApp {
            background:
                radial-gradient(ellipse at 8% 2%, #163d34 0, transparent 33%),
                radial-gradient(ellipse at 95% 12%, #172d54 0, transparent 28%),
                var(--fit-navy);
            color: #F8FAFC;
            font-family: 'DM Sans', sans-serif;
        }
        [data-testid="stHeader"] { background: rgba(15, 23, 42, .72); }
        [data-testid="stToolbar"] { right: 1rem; }
        [data-testid="stMainBlockContainer"] { padding-top: 1.2rem; }
        .fitguide-header {
            position: sticky; top: 0; z-index: 999;
            display: flex; align-items: center; justify-content: space-between;
            gap: 1rem; padding: 14px 20px; margin: 0 0 22px;
            border: 1px solid rgba(148, 163, 184, .17); border-radius: 16px;
            background: rgba(15, 23, 42, .91); backdrop-filter: blur(14px);
            box-shadow: 0 12px 35px rgba(2, 6, 23, .25);
        }
        .fitguide-brand { display: flex; align-items: center; gap: 10px; color: #F8FAFC; font-size: 1.1rem; font-weight: 800; }
        .fitguide-logo {
            display: grid; width: 38px; height: 38px; place-items: center;
            border-radius: 12px; background: linear-gradient(135deg, var(--fit-green), #14B8A6);
            color: #052E1A; font-size: 1.35rem;
        }
        .fitguide-nav { display: flex; flex-wrap: wrap; gap: 18px; }
        .fitguide-nav a { color: #CBD5E1; font-size: .88rem; text-decoration: none; }
        .fitguide-nav a:hover { color: var(--fit-green); }
        .fitguide-hero {
            padding: clamp(24px, 5vw, 48px); border-radius: 24px;
            background: linear-gradient(115deg, rgba(34, 197, 94, .2), rgba(59, 130, 246, .2)),
                        linear-gradient(135deg, #172B39, #17233E);
            border: 1px solid rgba(148, 163, 184, .2);
            box-shadow: 0 22px 55px rgba(2, 6, 23, .24);
        }
        .fitguide-hero-kicker { margin: 0 0 8px; color: #86EFAC; font-size: .76rem; font-weight: 800; letter-spacing: .14em; }
        .fitguide-hero h1 { margin: 0; color: #F8FAFC; font-size: clamp(1.8rem, 4vw, 2.8rem); line-height: 1.15; }
        .fitguide-hero p:last-child { margin: 12px 0 0; color: #CBD5E1; }
        .fitguide-section-title { margin: 0 0 5px; color: #F8FAFC; font-size: 1.65rem; font-weight: 800; }
        .fitguide-section-copy { margin: 0 0 18px; color: var(--fit-muted); }
        .fitguide-metric {
            min-height: 124px; padding: 17px 18px; border: 1px solid rgba(148, 163, 184, .19);
            border-radius: 16px; box-shadow: 0 12px 28px rgba(2, 6, 23, .2);
            transition: transform .2s ease, box-shadow .2s ease;
        }
        .fitguide-metric:hover, [data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-4px); box-shadow: 0 18px 38px rgba(2, 6, 23, .32);
        }
        .metric-green { background: linear-gradient(145deg, rgba(34, 197, 94, .24), rgba(15, 23, 42, .94)); }
        .metric-blue { background: linear-gradient(145deg, rgba(59, 130, 246, .25), rgba(15, 23, 42, .94)); }
        .metric-violet { background: linear-gradient(145deg, rgba(168, 85, 247, .22), rgba(15, 23, 42, .94)); }
        .metric-orange { background: linear-gradient(145deg, rgba(249, 115, 22, .23), rgba(15, 23, 42, .94)); }
        .fitguide-metric-label { color: #CBD5E1; font-size: .85rem; font-weight: 650; }
        .fitguide-metric-value { margin-top: 5px; color: white; font-size: 2rem; font-weight: 800; line-height: 1.2; }
        .fitguide-metric-caption { margin-top: 5px; color: #94A3B8; font-size: .75rem; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 16px; background: rgba(20, 32, 53, .8);
            box-shadow: 0 12px 30px rgba(2, 6, 23, .22);
            transition: transform .2s ease, box-shadow .2s ease;
        }
        [data-testid="stImage"] img { border-radius: 13px; object-fit: cover; }
        .plan-card-title { margin: 12px 0 4px; color: #F8FAFC; font-size: 1.2rem; font-weight: 800; }
        .plan-card-copy { margin: 0 0 12px; color: #AAB8CA; font-size: .88rem; }
        .plan-item { display: flex; justify-content: space-between; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(148, 163, 184, .12); color: #E2E8F0; font-size: .84rem; }
        .plan-item span:last-child { color: #86EFAC; text-align: right; }
        .exercise-title { color: #F8FAFC; font-weight: 750; }
        .stMarkdown, [data-testid="stWidgetLabel"] p, .stCaption { color: #D5DEEA; }
        [data-testid="stExpander"] { border-color: rgba(148, 163, 184, .22); border-radius: 12px; background: rgba(20, 32, 53, .55); }
        [data-testid="stForm"] { border-color: rgba(148, 163, 184, .2); border-radius: 16px; background: rgba(20, 32, 53, .7); }
        div.stButton > button, [data-testid="stFormSubmitButton"] button {
            min-height: 44px; border: 0; border-radius: 12px;
            background: linear-gradient(100deg, var(--fit-green), #10B981);
            color: #052E1A; font-weight: 800; transition: transform .18s ease, filter .18s ease;
        }
        div.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover { transform: translateY(-2px); filter: brightness(1.08); }
        input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div { border-radius: 10px !important; }
        [data-testid="stMetric"] { border-radius: 14px; }
        hr { border-color: rgba(148, 163, 184, .17); }
        @media (max-width: 700px) {
            .fitguide-header { align-items: flex-start; flex-direction: column; }
            .fitguide-nav { gap: 10px 15px; }
            [data-testid="stMainBlockContainer"] { padding-left: 1rem; padding-right: 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(icon: str, label: str, value: object, caption: str, tint: str) -> None:
    st.markdown(
        f"""
        <div class="fitguide-metric {tint}">
          <div class="fitguide-metric-label">{icon}&nbsp; {label}</div>
          <div class="fitguide-metric-value">{value}</div>
          <div class="fitguide-metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def save_streamlit_workout(activity: str, workout_day: date, minutes: int, notes: str) -> None:
    if not activity.strip() or not 1 <= minutes <= 600:
        raise ValueError("Enter an activity and a workout length from 1 to 600 minutes.")
    if workout_day > date.today():
        raise ValueError("Choose today or an earlier date.")
    with get_db() as connection:
        connection.execute(
            "INSERT INTO workouts(workout_date, activity, minutes, notes) VALUES (?, ?, ?, ?)",
            (workout_day.isoformat(), activity.strip()[:100], minutes, notes.strip()[:500]),
        )


def save_streamlit_measurement(measure_day: date, weight: float | None, notes: str) -> None:
    clean_notes = notes.strip()[:300]
    if measure_day > date.today():
        raise ValueError("Choose today or an earlier date.")
    if (weight is not None and not 1 <= weight <= 500) or (weight is None and not clean_notes):
        raise ValueError("Enter a weight from 1 to 500 kg, or add a progress note.")
    with get_db() as connection:
        connection.execute(
            "INSERT INTO measurements(measure_date, weight, notes) VALUES (?, ?, ?)",
            (measure_day.isoformat(), weight, clean_notes),
        )


def render_streamlit_app() -> None:
    """Render the modern Streamlit UI while reusing the existing SQLite data."""
    st.set_page_config(
        page_title="FitGuide AI | Fitness dashboard",
        page_icon="💪",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_streamlit_styles()
    init_db()
    data = get_page_data()
    stats = data["stats"]

    st.markdown(
        """
        <header class="fitguide-header">
          <div class="fitguide-brand"><span class="fitguide-logo">💪</span> FitGuide <span style="color:#22C55E">AI</span></div>
          <nav class="fitguide-nav">
            <a href="#workouts">🏋️ Workouts</a><a href="#exercises">🧘 Exercises</a>
            <a href="#progress">📈 Progress</a><a href="#coach">✨ AI Coach</a><a href="#community">🤝 Community</a>
          </nav>
        </header>
        <section class="fitguide-hero">
          <p class="fitguide-hero-kicker">YOUR PERSONAL FITNESS COMPANION</p>
          <h1>Welcome back, let&apos;s crush your goals today 💪</h1>
          <p>Small steps, steady progress. Your next workout is one good choice away.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    metric_columns = st.columns(4)
    with metric_columns[0]:
        render_metric_card("🏋️", "Total workouts", stats["sessions"], "sessions completed", "metric-green")
    with metric_columns[1]:
        render_metric_card("🔥", "Active minutes", stats["minutes"], "minutes recorded", "metric-orange")
    with metric_columns[2]:
        render_metric_card("⭐", "Fit points", stats["points"], "10 points per workout", "metric-blue")
    with metric_columns[3]:
        render_metric_card("📅", "Current streak", f'{stats["streak"]} days', "keep your routine going", "metric-violet")

    st.write("")
    st.markdown('<div id="workouts"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="fitguide-section-title">🏋️ Workout plans</h2>', unsafe_allow_html=True)
    st.markdown('<p class="fitguide-section-copy">Choose a plan and take the first step at your own pace.</p>', unsafe_allow_html=True)
    plan_columns = st.columns(2, gap="large")
    plan_descriptions = {
        "Beginner": "A gentle full-body introduction to build confidence and consistency.",
        "Strength": "Simple, controlled strength movements for a developing routine.",
        "Cardio": "Adaptable intervals to build stamina gradually.",
        "Mobility": "Easy movements to practice comfortable mobility.",
    }
    for index, (plan_name, items) in enumerate(PLANS.items()):
        with plan_columns[index % 2]:
            with st.container(border=True):
                st.image(PLAN_IMAGES[plan_name], use_container_width=True)
                st.markdown(
                    f'<div class="plan-card-title">{plan_name} plan</div>'
                    f'<p class="plan-card-copy">{plan_descriptions[plan_name]}</p>',
                    unsafe_allow_html=True,
                )
                for exercise_name, amount in items:
                    st.markdown(
                        f'<div class="plan-item"><span>✅ {exercise_name}</span><span>{amount}</span></div>',
                        unsafe_allow_html=True,
                    )
                st.write("")
                if st.button(f"📝 Log {plan_name} workout", key=f"log-plan-{plan_name}", width="stretch"):
                    st.session_state["selected_plan"] = plan_name
                    st.session_state["notice"] = ("info", f"{plan_name} plan selected. Log it in Progress below.")

    st.markdown('<div id="exercises"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="fitguide-section-title">🧘 Exercise library</h2>', unsafe_allow_html=True)
    st.markdown('<p class="fitguide-section-copy">Find a movement, learn the form, and adjust it to your level.</p>', unsafe_allow_html=True)
    exercise_columns = st.columns(4, gap="medium")
    for index, exercise in enumerate(EXERCISES):
        with exercise_columns[index % 4]:
            with st.container(border=True):
                st.markdown(
                    f'<div class="exercise-title">{exercise["name"]}</div>'
                    f'<p>{exercise["target"]} · {exercise["difficulty"]}</p>'
                    f'<p>🧰 Equipment: {exercise["equipment"]}</p>',
                    unsafe_allow_html=True,
                )
                with st.expander("📖 Instructions and benefits"):
                    st.write(exercise["instructions"])
                    st.caption(f"✨ Benefit: {exercise['benefits']}")

    st.markdown('<div id="recommendations"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="fitguide-section-title">🎯 Personalized recommendations</h2>', unsafe_allow_html=True)
    st.markdown('<p class="fitguide-section-copy">Get a practical suggestion for your goal, level, equipment, and available time.</p>', unsafe_allow_html=True)
    recommend_columns = st.columns([1, 1.2], gap="large")
    with recommend_columns[0]:
        with st.container(border=True):
            goal = st.selectbox("Fitness goal", GOALS, key="recommend-goal")
            level = st.selectbox("Experience level", LEVELS, key="recommend-level")
            equipment = st.selectbox("Available equipment", EQUIPMENT_OPTIONS, key="recommend-equipment")
            available_minutes = st.select_slider("Time available", options=[10, 20, 30, 45], value=20, format_func=lambda value: f"{value} min")
            if st.button("✨ Get my recommendation", key="recommend-submit", width="stretch"):
                focus = {
                    "Cardio fitness": "a comfortable walk or low-impact cardio intervals",
                    "Build strength": "controlled strength exercises such as squats, wall push-ups, and bridges",
                    "Improve mobility": "gentle mobility movements in a comfortable range",
                    "General fitness": "a balanced mix of easy cardio and full-body movements",
                }[goal]
                effort = "beginner-friendly" if level == "Beginner" else f"appropriate for an {level.lower()} exerciser"
                equipment_tip = "Use bodyweight movements." if equipment == "None" else f"If useful, include your {equipment.lower()}."
                st.session_state["recommendation"] = (
                    f"Try {available_minutes} minutes of {focus}. Keep it {effort}, "
                    f"warm up and cool down, and rest as needed. {equipment_tip}"
                )
    with recommend_columns[1]:
        with st.container(border=True):
            st.markdown("#### 💡 Your personalized suggestion")
            st.write(st.session_state.get("recommendation", "Choose your preferences and tap “Get my recommendation.”"))

    st.markdown('<div id="coach"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="fitguide-section-title">✨ Your Gemma AI workout coach</h2>', unsafe_allow_html=True)
    st.markdown('<p class="fitguide-section-copy">Gemma runs locally with Ollama and builds a draft from your preferences.</p>', unsafe_allow_html=True)
    ai_columns = st.columns([1, 1.2], gap="large")
    with ai_columns[0]:
        with st.form("gemma-plan-form", border=True):
            ai_goal = st.selectbox("AI plan goal", GOALS, key="ai-goal")
            ai_level = st.selectbox("AI experience level", LEVELS, key="ai-level")
            ai_equipment = st.selectbox("AI equipment", EQUIPMENT_OPTIONS, key="ai-equipment")
            ai_minutes = st.number_input("Minutes per session", min_value=10, max_value=120, value=30, step=5)
            ai_days = st.number_input("Days per week", min_value=1, max_value=7, value=3, step=1)
            generate = st.form_submit_button("✨ Generate plan with Gemma", width="stretch")
    with ai_columns[1]:
        if generate:
            with st.spinner("🏋️ Gemma is putting your workout together..."):
                st.session_state["generated_plan"] = generate_ai_plan(
                    ai_goal, ai_level, ai_equipment, int(ai_minutes), int(ai_days)
                )
        with st.container(border=True):
            st.markdown("#### 🌟 Your workout plan")
            st.markdown(
                st.session_state.get(
                    "generated_plan",
                    "Submit your preferences to get a personalized workout plan from Gemma.",
                )
            )

    st.markdown('<div id="progress"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="fitguide-section-title">📈 Your progress</h2>', unsafe_allow_html=True)
    st.markdown('<p class="fitguide-section-copy">Workouts and progress entries are saved locally in your SQLite database.</p>', unsafe_allow_html=True)
    notice = st.session_state.pop("notice", None)
    if notice:
        getattr(st, notice[0])(notice[1])
    progress_columns = st.columns([1, 1, 1.2], gap="large")
    with progress_columns[0]:
        with st.form("workout-log-form", border=True):
            st.markdown("#### 🏋️ Log a workout")
            activity = st.text_input("Activity", value=st.session_state.get("selected_plan", ""), max_chars=100, placeholder="e.g. 20-minute walk")
            workout_day = st.date_input("Workout date", value=date.today(), max_value=date.today())
            workout_minutes = st.number_input("Minutes", min_value=1, max_value=600, value=20, step=5)
            workout_notes = st.text_input("Notes (optional)", max_chars=500)
            save_workout = st.form_submit_button("✅ Save workout +10 points", width="stretch")
        if save_workout:
            try:
                save_streamlit_workout(activity, workout_day, int(workout_minutes), workout_notes)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state.pop("selected_plan", None)
                st.success("Workout saved. You earned 10 Fit points!")
                st.rerun()
    with progress_columns[1]:
        with st.form("measurement-form", border=True):
            st.markdown("#### ⚖️ Log progress")
            measure_day = st.date_input("Progress date", value=date.today(), max_value=date.today())
            weight = st.number_input("Weight in kg (0 means skip)", min_value=0.0, max_value=500.0, value=0.0, step=0.1)
            measure_notes = st.text_input("Progress note", max_chars=300, placeholder="Energy, strength, or a milestone")
            save_measurement = st.form_submit_button("💾 Save progress", width="stretch")
        if save_measurement:
            try:
                save_streamlit_measurement(measure_day, weight or None, measure_notes)
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Progress entry saved.")
                st.rerun()
    with progress_columns[2]:
        with st.container(border=True):
            st.markdown("#### 🏆 Badges")
            if stats["badges"]:
                for badge in stats["badges"]:
                    st.markdown(f"🌟 **{badge['name']}** — {badge['description']}")
            else:
                st.caption("Complete a workout to unlock your first badge.")
            st.markdown("#### 🕒 Recent workouts")
            if stats["logs"]:
                for log in stats["logs"][:5]:
                    st.markdown(f"✅ **{log['activity']}** · {log['workout_date']} · {log['minutes']} min")
            else:
                st.caption("Your workout history will show up here.")
            if data["measurements"]:
                st.markdown("#### 📊 Recent progress notes")
                for entry in data["measurements"][:5]:
                    value = f"{entry['weight']} kg" if entry["weight"] is not None else "Progress note"
                    note = f" · {entry['notes']}" if entry["notes"] else ""
                    st.markdown(f"📌 **{value}** · {entry['measure_date']}{note}")

    st.markdown('<div id="nutrition"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="fitguide-section-title">🥗 Nutrition and hydration</h2>', unsafe_allow_html=True)
    st.markdown('<p class="fitguide-section-copy">General wellness ideas, not a medical diet plan.</p>', unsafe_allow_html=True)
    nutrition_columns = st.columns(3, gap="medium")
    for index, tip in enumerate(NUTRITION_TIPS):
        with nutrition_columns[index % 3]:
            with st.container(border=True):
                st.markdown(f"🥑 **Tip {index + 1:02d}**")
                st.write(tip)

    st.markdown('<div id="community"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="fitguide-section-title">🤝 Community board</h2>', unsafe_allow_html=True)
    st.markdown('<p class="fitguide-section-copy">Share a win or encourage someone. Posts are stored on this computer only.</p>', unsafe_allow_html=True)
    community_columns = st.columns([1, 1.3], gap="large")
    with community_columns[0]:
        with st.form("community-post-form", border=True):
            st.markdown("#### 💬 Share an update")
            author = st.text_input("Your name", max_chars=40, placeholder="Fitness friend")
            message = st.text_area("Your message", max_chars=500, placeholder="I completed my first workout...", height=120)
            submit_post = st.form_submit_button("📨 Post update", width="stretch")
        if submit_post:
            clean_message = message.strip()[:500]
            if not clean_message:
                st.error("Write a message before posting.")
            else:
                clean_author = author.strip()[:40] or "Fitness friend"
                with get_db() as connection:
                    connection.execute(
                        "INSERT INTO posts(author, message, created_at) VALUES (?, ?, ?)",
                        (clean_author, clean_message, datetime.now().strftime("%Y-%m-%d %H:%M")),
                    )
                st.success("Your post was saved to this local demo.")
                st.rerun()
    with community_columns[1]:
        posts = data["posts"]
        if posts:
            for post in posts:
                with st.container(border=True):
                    st.markdown(f"💬 **{post['author']}** · {post['created_at']}")
                    st.write(post["message"])
        else:
            st.info("Your community starts here. Be the first to share a fitness win!")


if get_script_run_ctx(suppress_warning=True) is not None:
    render_streamlit_app()
elif __name__ == "__main__":
    init_db()
    app.run(debug=True)
