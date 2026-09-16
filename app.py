
import streamlit as st
import requests
import sqlite3
import json
import os
from datetime import date, datetime, timedelta

# ============================================================
# NUTRICOACH — SIMPLE, ATTRACTIVE, ALL-IN-ONE FITNESS APP
# Persistent SQLite storage + USDA food search + smart coach
# ============================================================

st.set_page_config(
    page_title="NutriCoach",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_PATH = "nutricoach.db"
TODAY = date.today().isoformat()
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# ------------------------------------------------------------
# STYLE
# ------------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #07130f 0%, #0b1713 45%, #07100d 100%);
    }
    .block-container {
        max-width: 1200px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3 {
        letter-spacing: -0.03em;
    }
    .hero {
        padding: 1.5rem;
        border-radius: 24px;
        background: linear-gradient(135deg, #123d2c, #0d251b);
        border: 1px solid rgba(255,255,255,.08);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    .hero p {
        color: #b8c8c0;
        margin-top: .4rem;
    }
    .coach {
        padding: 1.25rem;
        border-radius: 20px;
        background: linear-gradient(135deg, #163d2d, #10291f);
        border: 1px solid rgba(115, 255, 176, .16);
        margin: .6rem 0 1rem 0;
    }
    .coach-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: .45rem;
    }
    .small {
        color: #aabbb2;
        font-size: .88rem;
    }
    .food-card, .section-card {
        padding: 1rem;
        border-radius: 18px;
        background: rgba(255,255,255,.035);
        border: 1px solid rgba(255,255,255,.07);
        margin-bottom: .7rem;
    }
    .pill {
        display: inline-block;
        padding: .25rem .6rem;
        border-radius: 999px;
        background: rgba(95, 220, 145, .12);
        color: #9df0bc;
        font-size: .78rem;
        margin-right: .25rem;
    }
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,.035);
        border-radius: 16px;
        padding: .7rem;
        border: 1px solid rgba(255,255,255,.06);
    }
    .footer {
        text-align:center;
        color:#7f9188;
        padding-top:2rem;
        font-size:.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id=1),
            data TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS food_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            food TEXT NOT NULL,
            meal TEXT,
            diet TEXT,
            quantity REAL,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            fiber REAL,
            vitamin_a REAL DEFAULT 0,
            vitamin_c REAL DEFAULT 0,
            vitamin_d REAL DEFAULT 0,
            vitamin_e REAL DEFAULT 0,
            vitamin_k REAL DEFAULT 0,
            calcium REAL DEFAULT 0,
            iron REAL DEFAULT 0,
            magnesium REAL DEFAULT 0,
            potassium REAL DEFAULT 0,
            zinc REAL DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS water (
            day TEXT PRIMARY KEY,
            liters REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            weight REAL,
            waist REAL,
            chest REAL,
            arms REAL,
            legs REAL,
            shoulders REAL,
            photo_front TEXT,
            photo_side TEXT,
            photo_back TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            name TEXT,
            minutes INTEGER,
            intensity TEXT,
            calories REAL,
            completed INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_status (
            day TEXT NOT NULL,
            meal TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            started_at TEXT,
            PRIMARY KEY(day, meal)
        )
    """)

    con.commit()
    con.close()

init_db()

# ------------------------------------------------------------
# PROFILE
# ------------------------------------------------------------
DEFAULT_PROFILE = {
    "name": "",
    "age": 25,
    "sex": "Male",
    "height": 170.0,
    "weight": 70.0,
    "activity": "Moderately Active",
    "diet": "Vegetarian",
    "budget": "Budget Friendly",
    "body_type": "Average",
    "goal": "General Fitness",
}

def load_profile():
    con = db()
    row = con.execute("SELECT data FROM profile WHERE id=1").fetchone()
    con.close()
    if not row:
        return DEFAULT_PROFILE.copy()
    try:
        data = json.loads(row[0])
        out = DEFAULT_PROFILE.copy()
        out.update(data)
        return out
    except Exception:
        return DEFAULT_PROFILE.copy()

def save_profile(profile):
    con = db()
    con.execute(
        "INSERT INTO profile(id,data) VALUES(1,?) "
        "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
        (json.dumps(profile),)
    )
    con.commit()
    con.close()

# Always normalize the profile so older databases/session state cannot
# crash the app when a newer field has been added.
if "profile" not in st.session_state:
    st.session_state.profile = load_profile()

_raw_profile = st.session_state.get("profile") or {}
profile = DEFAULT_PROFILE.copy()
if isinstance(_raw_profile, dict):
    profile.update(_raw_profile)

# Keep the normalized profile in session state for the rest of the app.
st.session_state.profile = profile

# ------------------------------------------------------------
# CALCULATIONS
# ------------------------------------------------------------
def calculate_targets(p):
    age = p["age"]
    weight = p["weight"]
    height = p["height"]

    if p["sex"] == "Male":
        bmr = 10*weight + 6.25*height - 5*age + 5
    else:
        bmr = 10*weight + 6.25*height - 5*age - 161

    activity_factor = {
        "Sedentary": 1.20,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725
    }[p["activity"]]

    tdee = bmr * activity_factor

    adjustment = {
        "Fat Loss": -400,
        "Muscle Gain": 250,
        "Strength": 200,
        "Recomposition": -150,
        "Calisthenics": 100,
        "Greek Body": -100,
        "Aesthetic Body": -100,
        "General Fitness": 0,
    }[p["goal"]]

    calories = max(tdee + adjustment, 1200)
    protein_factor = 1.8 if p["goal"] in ["Muscle Gain", "Strength", "Calisthenics"] else 1.7
    protein = weight * protein_factor
    fat = weight * 0.8
    fiber = 14 * calories / 1000
    water = max(weight * 0.035, 1.5)
    carbs = max((calories - protein*4 - fat*9) / 4, 0)
    bmi = weight / ((height/100)**2)

    return {
        "BMR": bmr, "TDEE": tdee, "Calories": calories,
        "Protein": protein, "Carbs": carbs, "Fat": fat,
        "Fiber": fiber, "Water": water, "BMI": bmi
    }

targets = calculate_targets(profile)

# ------------------------------------------------------------
# FOOD DATA
# ------------------------------------------------------------
PIECE_WEIGHTS = {
    "egg": 50, "banana": 118, "apple": 182, "orange": 130,
    "roti": 40, "chapati": 40, "bread": 25, "idli": 60, "dosa": 100
}

def food_nutrients(food):
    n = {}
    for item in food.get("foodNutrients", []):
        name = item.get("nutrientName")
        if name:
            n[name] = item.get("value", 0) or 0

    return {
        "Calories": n.get("Energy", 0),
        "Protein": n.get("Protein", 0),
        "Carbs": n.get("Carbohydrate, by difference", 0),
        "Fat": n.get("Total lipid (fat)", 0),
        "Fiber": n.get("Fiber, total dietary", 0),
        "Vitamin A": n.get("Vitamin A, RAE", 0),
        "Vitamin C": n.get("Vitamin C, total ascorbic acid", 0),
        "Vitamin D": n.get("Vitamin D (D2 + D3)", 0),
        "Vitamin E": n.get("Vitamin E (alpha-tocopherol)", 0),
        "Vitamin K": n.get("Vitamin K (phylloquinone)", 0),
        "Calcium": n.get("Calcium, Ca", 0),
        "Iron": n.get("Iron, Fe", 0),
        "Magnesium": n.get("Magnesium, Mg", 0),
        "Potassium": n.get("Potassium, K", 0),
        "Zinc": n.get("Zinc, Zn", 0),
    }

def piece_weight(query, description):
    q = (query + " " + description).lower()
    for key, value in PIECE_WEIGHTS.items():
        if key in q:
            if key == "egg" and ("white" in q or "yolk" in q):
                continue
            return value
    return 100

def search_usda(query):
    try:
        api_key = st.secrets["FDC_API_KEY"]
    except Exception:
        return None, "USDA key not found in .streamlit/secrets.toml."

    try:
        r = requests.get(
            USDA_SEARCH_URL,
            params={"api_key": api_key, "query": query, "pageSize": 12},
            timeout=20
        )
        if r.status_code != 200:
            return None, f"USDA error: {r.status_code}"
        foods = r.json().get("foods", [])
        foods = sorted(
            foods,
            key=lambda x: (
                0 if x.get("dataType") in ["Foundation", "SR Legacy", "Survey (FNDDS)"] else 1,
                len(x.get("description", ""))
            )
        )
        return foods, None
    except requests.RequestException as e:
        return None, f"Could not connect to USDA: {e}"

def get_today_food():
    con = db()
    rows = con.execute(
        "SELECT * FROM food_log WHERE day=? ORDER BY id DESC", (TODAY,)
    ).fetchall()
    con.close()

    cols = [
        "id","day","food","meal","diet","quantity","calories","protein","carbs",
        "fat","fiber","vitamin_a","vitamin_c","vitamin_d","vitamin_e","vitamin_k",
        "calcium","iron","magnesium","potassium","zinc","created_at"
    ]
    return [dict(zip(cols, r)) for r in rows]

def add_food(result):
    con = db()
    con.execute("""
        INSERT INTO food_log(
            day,food,meal,diet,quantity,calories,protein,carbs,fat,fiber,
            vitamin_a,vitamin_c,vitamin_d,vitamin_e,vitamin_k,
            calcium,iron,magnesium,potassium,zinc,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        TODAY, result["Food"], result["Meal"], result["Diet"], result["Quantity"],
        result["Calories"], result["Protein"], result["Carbs"], result["Fat"],
        result["Fiber"], result["Vitamin A"], result["Vitamin C"], result["Vitamin D"],
        result["Vitamin E"], result["Vitamin K"], result["Calcium"], result["Iron"],
        result["Magnesium"], result["Potassium"], result["Zinc"],
        datetime.now().isoformat(timespec="seconds")
    ))
    con.commit()
    con.close()

def remove_food(food_id):
    con = db()
    con.execute("DELETE FROM food_log WHERE id=?", (food_id,))
    con.commit()
    con.close()

def totals_for_day(day=TODAY):
    con = db()
    row = con.execute("""
        SELECT
        COALESCE(SUM(calories),0),
        COALESCE(SUM(protein),0),
        COALESCE(SUM(carbs),0),
        COALESCE(SUM(fat),0),
        COALESCE(SUM(fiber),0),
        COALESCE(SUM(vitamin_a),0),
        COALESCE(SUM(vitamin_c),0),
        COALESCE(SUM(vitamin_d),0),
        COALESCE(SUM(vitamin_e),0),
        COALESCE(SUM(vitamin_k),0),
        COALESCE(SUM(calcium),0),
        COALESCE(SUM(iron),0),
        COALESCE(SUM(magnesium),0),
        COALESCE(SUM(potassium),0),
        COALESCE(SUM(zinc),0)
        FROM food_log WHERE day=?
    """, (day,)).fetchone()
    con.close()

    keys = [
        "Calories","Protein","Carbs","Fat","Fiber",
        "Vitamin A","Vitamin C","Vitamin D","Vitamin E","Vitamin K",
        "Calcium","Iron","Magnesium","Potassium","Zinc"
    ]
    return dict(zip(keys, row))

totals = totals_for_day()

remaining = {
    "Calories": max(targets["Calories"] - totals["Calories"], 0),
    "Protein": max(targets["Protein"] - totals["Protein"], 0),
    "Carbs": max(targets["Carbs"] - totals["Carbs"], 0),
    "Fat": max(targets["Fat"] - totals["Fat"], 0),
    "Fiber": max(targets["Fiber"] - totals["Fiber"], 0),
}

# ------------------------------------------------------------
# WATER
# ------------------------------------------------------------
def get_water():
    con = db()
    row = con.execute("SELECT liters FROM water WHERE day=?", (TODAY,)).fetchone()
    con.close()
    return float(row[0]) if row else 0.0

def set_water(value):
    con = db()
    con.execute(
        "INSERT INTO water(day,liters) VALUES(?,?) "
        "ON CONFLICT(day) DO UPDATE SET liters=excluded.liters",
        (TODAY, float(value))
    )
    con.commit()
    con.close()

water = get_water()

# ------------------------------------------------------------
# AUTOMATIC WORKOUT
# ------------------------------------------------------------
def auto_workout(p):
    goal = p["goal"]
    activity = p["activity"]

    if goal in ["Muscle Gain", "Strength"]:
        name = "Full Body Strength"
        blocks = ["Squats", "Push-ups", "Rows / backpack rows", "Lunges", "Plank"]
        minutes = 40
        intensity = "Moderate"
    elif goal == "Calisthenics":
        name = "Calisthenics Fundamentals"
        blocks = ["Push-ups", "Bodyweight squats", "Pike push-ups", "Lunges", "Hollow hold"]
        minutes = 35
        intensity = "Moderate"
    elif goal == "Fat Loss":
        name = "Brisk Walk + Core"
        blocks = ["Brisk walk", "Bodyweight squats", "Incline push-ups", "Plank"]
        minutes = 35
        intensity = "Moderate"
    elif goal == "Recomposition":
        name = "Strength + Conditioning"
        blocks = ["Squats", "Push-ups", "Rows", "Reverse lunges", "Brisk walk"]
        minutes = 40
        intensity = "Moderate"
    else:
        name = "Daily Fitness Full Body"
        blocks = ["Walk", "Squats", "Push-ups", "Mobility", "Plank"]
        minutes = 30
        intensity = "Light-Moderate"

    if activity == "Sedentary":
        minutes = max(minutes - 10, 20)
    elif activity == "Very Active":
        minutes += 10

    calories = max(p["weight"] * minutes * 0.07, 80)

    return {
        "name": name,
        "blocks": blocks,
        "minutes": minutes,
        "intensity": intensity,
        "calories": calories
    }

workout = auto_workout(profile)

def today_workout():
    con = db()
    row = con.execute(
        "SELECT id,completed FROM workouts WHERE day=? ORDER BY id DESC LIMIT 1",
        (TODAY,)
    ).fetchone()
    con.close()
    return row

# ------------------------------------------------------------
# DIET PLAN
# ------------------------------------------------------------
def meal_sets(p):
    diet = p["diet"]
    budget = p["budget"]

    if diet == "Vegan":
        breakfasts = [
            "Oats + soy milk + banana + peanuts",
            "Poha + sprouts + fruit",
            "Besan chilla + tofu + fruit",
            "Peanut-butter oats + banana",
        ]
        lunches = [
            "Rice + dal + soy chunks + vegetables",
            "Roti + chana + salad + tofu",
            "Rice + rajma + vegetables",
            "Roti + dal + soy chunks + vegetables",
        ]
        snacks = [
            "Roasted chana + fruit",
            "Peanuts + banana",
            "Soy yogurt + fruit",
            "Sprouts chaat",
        ]
        dinners = [
            "Roti + tofu + vegetables + salad",
            "Rice + dal + soy chunks + vegetables",
            "Roti + chana + vegetables",
            "Khichdi + tofu + salad",
        ]
    elif diet == "Non-Vegetarian":
        breakfasts = [
            "Eggs + oats + banana",
            "Egg bhurji + 2 roti + fruit",
            "Oats + curd + eggs",
            "Eggs + poha + fruit",
        ]
        lunches = [
            "Rice + chicken + dal + vegetables",
            "Roti + chicken + salad + curd",
            "Rice + fish + vegetables + dal",
            "Roti + eggs + dal + vegetables",
        ]
        snacks = [
            "Curd + banana + peanuts",
            "Roasted chana + fruit",
            "2 eggs + fruit",
            "Milk/curd + oats",
        ]
        dinners = [
            "Roti + chicken + vegetables",
            "Rice + fish + salad",
            "Roti + eggs + dal + vegetables",
            "Chicken + rice + vegetables",
        ]
    else:
        breakfasts = [
            "Oats + milk/curd + banana + peanuts",
            "Poha + curd + fruit",
            "Besan chilla + curd + fruit",
            "Oats + milk + banana + seeds",
        ]
        lunches = [
            "Rice + dal + paneer/tofu + vegetables",
            "Roti + chana + curd + salad",
            "Rice + rajma + vegetables + curd",
            "Roti + dal + paneer/tofu + vegetables",
        ]
        snacks = [
            "Curd + banana + peanuts",
            "Roasted chana + fruit",
            "Sprouts chaat + fruit",
            "Milk/curd + oats",
        ]
        dinners = [
            "Roti + paneer/tofu + vegetables",
            "Rice + dal + salad + curd",
            "Roti + chana + vegetables",
            "Khichdi + curd + salad",
        ]

    if budget == "Budget Friendly":
        # Keep the plan practical around common, lower-cost foods.
        breakfasts = [x.replace("seeds", "peanuts") for x in breakfasts]
        snacks = [x.replace("fruit", "seasonal fruit") for x in snacks]

    return breakfasts, lunches, snacks, dinners

def generate_plan(cycle=1):
    b, l, s, d = meal_sets(profile)
    plan = []
    for i in range(14):
        idx = (i + cycle - 1) % len(b)
        plan.append({
            "day": i + 1,
            "date": (date.today() + timedelta(days=i)).isoformat(),
            "Breakfast": b[idx],
            "Lunch": l[(idx + 1) % len(l)],
            "Snack": s[(idx + 2) % len(s)],
            "Dinner": d[(idx + 3) % len(d)],
        })
    return plan

if "diet_cycle" not in st.session_state:
    st.session_state.diet_cycle = 1
if "diet_plan" not in st.session_state:
    st.session_state.diet_plan = generate_plan(1)

# ------------------------------------------------------------
# MEAL STATUS
# ------------------------------------------------------------
MEALS = ["Breakfast", "Lunch", "Snack", "Dinner"]

def meal_done(meal):
    con = db()
    row = con.execute(
        "SELECT done FROM meal_status WHERE day=? AND meal=?",
        (TODAY, meal)
    ).fetchone()
    con.close()
    return bool(row and row[0])

def set_meal_done(meal, done):
    con = db()
    con.execute(
        "INSERT INTO meal_status(day,meal,done) VALUES(?,?,?) "
        "ON CONFLICT(day,meal) DO UPDATE SET done=excluded.done",
        (TODAY, meal, int(done))
    )
    con.commit()
    con.close()

# ------------------------------------------------------------
# COACH
# ------------------------------------------------------------
def coach_message():
    p_gap = remaining["Protein"]
    c_gap = remaining["Calories"]
    f_gap = remaining["Fiber"]

    if c_gap <= 100 and p_gap <= 10:
        return (
            "You're close to today's main targets. Keep the rest of the day "
            "simple and avoid eating just to chase a number."
        )

    if p_gap >= 35:
        if profile["diet"] == "Vegan":
            food = "80 g soy chunks + rice + vegetables"
        elif profile["diet"] == "Vegetarian":
            food = "200 g curd + 100 g roasted chana + 2 rotis"
        else:
            food = "2 eggs + 200 g curd + 2 rotis"
        return (
            f"You're about {p_gap:.0f} g short on protein with {c_gap:.0f} kcal left. "
            f"Next action: {food}. Protein is currently your largest gap."
        )

    if f_gap >= 6:
        return (
            f"You have about {f_gap:.0f} g fiber left. Add a seasonal fruit, "
            "dal/chana and vegetables to improve the balance of your next meal."
        )

    return (
        f"You have about {c_gap:.0f} kcal left and {p_gap:.0f} g protein left. "
        "Choose your next meal around the largest remaining target instead of "
        "adding random snacks."
    )

# ------------------------------------------------------------
# ============================================================
# SUPER ULTRA REAL EXECUTABLE TOOLKIT
# ============================================================
def ufloat(v,d=0.0):
    try:return d if v in (None,"") else float(v)
    except (TypeError,ValueError):return d
def uint(v,d=0):
    try:return d if v in (None,"") else int(float(v))
    except (TypeError,ValueError):return d
def clamp(v,a,b):return max(a,min(b,ufloat(v)))
def pct(v,t):return 0 if ufloat(t)<=0 else ufloat(v)/ufloat(t)*100
def remain(t,v):return max(0,ufloat(t)-ufloat(v))
def parseday(v=None):
    if isinstance(v,date):return v
    try:return datetime.fromisoformat(str(v)).date()
    except:return date.today()
def parsetime(v=None):
    if hasattr(v,"hour"):return v
    for f in ("%H:%M:%S","%H:%M","%I:%M %p"):
        try:return datetime.strptime(str(v),f).time()
        except:pass
    return datetime.now().time().replace(microsecond=0)
def dt(day=None,t=None):return datetime.combine(parseday(day),parsetime(t))
def iso(v=None):return parseday(v).isoformat()
def daylabel(v=None):return parseday(v).strftime("%A, %d %B %Y")
def timelabel(v=None):return parsetime(v).strftime("%I:%M %p")
def nowlabel():return datetime.now().strftime("%A · %d %B %Y · %I:%M:%S %p")
def weekstart(v=None):return parseday(v)-timedelta(days=parseday(v).weekday())
def weekend(v=None):return weekstart(v)+timedelta(days=6)
def monthstart(v=None):return parseday(v).replace(day=1)
def monthend(v=None):
    d=parseday(v)
    return (d.replace(year=d.year+1,month=1,day=1)-timedelta(days=1)) if d.month==12 else d.replace(month=d.month+1,day=1)-timedelta(days=1)
def daterange(a,b):
    a,b=parseday(a),parseday(b)
    if b<a:a,b=b,a
    return [a+timedelta(days=i) for i in range((b-a).days+1)]
def addmonth(v,n=1):
    d=parseday(v);m=d.year*12+d.month-1+uint(n);y,m=divmod(m,12);m+=1
    import calendar
    return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
def calgrid(y,m):
    import calendar
    return calendar.monthcalendar(y,m)
def calories(p,c,f):return ufloat(p)*4+ufloat(c)*4+ufloat(f)*9
def macro_split(p,c,f):
    total=calories(p,c,f)
    return {"protein":0,"carbs":0,"fat":0} if not total else {"protein":ufloat(p)*4/total*100,"carbs":ufloat(c)*4/total*100,"fat":ufloat(f)*9/total*100}
def nutrient_sum(items,key):return sum(ufloat(x.get(key,0)) for x in items)
def nutrient_average(items,key):return nutrient_sum(items,key)/max(1,len(items))
def nutrient_gap(items,key,target):return remain(target.get(key,0),nutrient_sum(items,key))
def nutrient_percent(items,key,target):return pct(nutrient_sum(items,key),target.get(key,0))
def nutrient_vector(item):return {k:ufloat(item.get(k,0)) for k in ("calories","protein","carbs","fat","fiber")}
def vector_add(a,b):return {k:ufloat(a.get(k))+ufloat(b.get(k)) for k in set(a)|set(b)}
def vector_scale(a,n):return {k:ufloat(v)*ufloat(n) for k,v in a.items()}
def vector_remaining(actual,target):return {k:remain(target.get(k,0),actual.get(k,0)) for k in target}
def meal_targets(cal,pro):return {"Breakfast":(cal*.25,pro*.25),"Lunch":(cal*.30,pro*.30),"Snack":(cal*.15,pro*.15),"Dinner":(cal*.30,pro*.30)}
def diet_ok(item,diet):
    tags=str(item.get("diet","")).lower();d=str(diet).lower()
    return d=="non-vegetarian" or d in tags or (d=="vegetarian" and "vegan" in tags)
def budget_ok(item,budget):return budget!="Budget Friendly" or ufloat(item.get("cost"))<=100
def food_rank(item,gap,budget,diet):
    if not diet_ok(item,diet) or not budget_ok(item,budget):return -10**9
    score=ufloat(item.get("protein"))*3+ufloat(item.get("fiber"))*2
    score+=min(ufloat(item.get("protein")),ufloat(gap.get("protein",0)))*4
    score-=max(0,ufloat(item.get("calories"))-ufloat(gap.get("calories",10**9)))*.05
    return score
def pick_food(items,gap,budget,diet):
    valid=[x for x in items if food_rank(x,gap,budget,diet)>-10**8]
    return max(valid,key=lambda x:food_rank(x,gap,budget,diet)) if valid else None
def piece_weight(name):
    for k,v in {"egg":50,"banana":118,"apple":182,"orange":130,"roti":40,"chapati":40,"bread":30,"tomato":123,"potato":173,"onion":110,"carrot":61}.items():
        if k in str(name).lower():return v
    return 100
def pieces_to_grams(name,n):return ufloat(n)*piece_weight(name)
def grams_to_pieces(name,g):return ufloat(g)/piece_weight(name)
def scale100(item,g):return vector_scale(nutrient_vector(item),ufloat(g)/100)
def scale_piece(item,n,name):return scale100(item,pieces_to_grams(name,n))
def bmr(sex,w,h,a):return 10*ufloat(w)+6.25*ufloat(h)-5*ufloat(a)+(5 if sex=="Male" else -161)
def activity(level):return {"Sedentary":1.2,"Lightly Active":1.375,"Moderately Active":1.55,"Very Active":1.725}.get(level,1.2)
def goal_adjust(goal):return {"Fat Loss":-400,"Muscle Gain":250,"Strength":250,"Recomposition":-150,"Calisthenics":100,"Greek Body":-100,"Aesthetic Body":-100,"General Fitness":0}.get(goal,0)
def protein_factor(goal):return 1.8 if goal in {"Muscle Gain","Strength","Calisthenics"} else 1.7 if goal in {"Fat Loss","Recomposition","Aesthetic Body","Greek Body"} else 1.6
def targets2(profile):
    base=bmr(profile.get("sex"),profile.get("weight"),profile.get("height"),profile.get("age"));tdee=base*activity(profile.get("activity"));cal=max(1200,tdee+goal_adjust(profile.get("goal")));pro=ufloat(profile.get("weight"))*protein_factor(profile.get("goal"));fat=ufloat(profile.get("weight"))*.8
    return {"BMR":base,"TDEE":tdee,"Calories":cal,"Protein":pro,"Fat":fat,"Carbs":max(0,(cal-pro*4-fat*9)/4),"Fiber":cal/1000*14,"Water":ufloat(profile.get("weight"))*.035}
def water_status(glasses,ml,target):return {"liters":uint(glasses)*ufloat(ml)/1000,"percent":pct(uint(glasses)*ufloat(ml)/1000,target),"remaining":remain(target,uint(glasses)*ufloat(ml)/1000)}
def hydration_schedule(target,wake=7,sleep=23):
    n=max(1,sleep-wake);return [{"time":f"{(wake+i)%24:02d}:00","liters":target/n} for i in range(n)]
def workout_calories(weight,minutes,met=5):return ufloat(weight)*ufloat(minutes)*ufloat(met)/60
def workout_focus(goal,day=None):
    arr={"Muscle Gain":["Upper","Lower","Push","Pull","Legs","Full Body","Recovery"],"Strength":["Squat","Push","Hinge","Upper","Lower","Full Body","Recovery"],"Calisthenics":["Push","Pull","Legs","Core","Skill","Full Body","Recovery"],"Fat Loss":["Full Body","Cardio","Core","Full Body","Intervals","Cardio","Recovery"]}.get(goal,["Full Body","Cardio","Mobility","Full Body","Cardio","Sports","Recovery"])
    return arr[parseday(day).weekday()]
def workout_plan(profile,day=None):
    goal=profile.get("goal","General Fitness");return {"day":iso(day),"focus":workout_focus(goal,day),"minutes":{"Strength":60,"Muscle Gain":55,"Calisthenics":45,"Fat Loss":45}.get(goal,40),"intensity":"High" if goal in {"Strength","Muscle Gain"} else "Moderate"}
def event(day,t,typ,title,notes=""):return {"day":iso(day),"time":parsetime(t).strftime("%H:%M"),"type":typ,"title":title,"notes":notes}
def event_sort(events):return sorted(events,key=lambda e:dt(e.get("day"),e.get("time")))
def event_filter(events,day=None,typ=None):return [e for e in event_sort(events) if (day is None or iso(e.get("day"))==iso(day)) and (typ is None or e.get("type")==typ)]
def event_key(e):return f"{iso(e.get('day'))}|{e.get('time')}|{e.get('type')}|{e.get('title')}"
def event_dedupe(events):
    seen=set();out=[]
    for e in event_sort(events):
        if event_key(e) not in seen:seen.add(event_key(e));out.append(e)
    return out
def event_counts(events):
    out={}
    for e in events:out[e.get("type","Other")]=out.get(e.get("type","Other"),0)+1
    return out
def event_conflicts(events):
    s=event_sort(events);return [(a,b) for a,b in zip(s,s[1:]) if a.get("day")==b.get("day") and a.get("time")==b.get("time")]
def next_event(events,now=None):
    now=now or datetime.now();f=[e for e in events if dt(e.get("day"),e.get("time"))>now];return min(f,key=lambda e:dt(e.get("day"),e.get("time"))) if f else None
def previous_event(events,now=None):
    now=now or datetime.now();f=[e for e in events if dt(e.get("day"),e.get("time"))<=now];return max(f,key=lambda e:dt(e.get("day"),e.get("time"))) if f else None
def event_hours_until(e,now=None):return max(0,(dt(e.get("day"),e.get("time"))-(now or datetime.now())).total_seconds()/3600)
def daily_event_score(events,day):
    types={e.get("type") for e in event_filter(events,day)};return len(types&{"Meal","Workout","Water","Measurement"})/4*100
def generate_calendar(start,days,profile):
    out=[]
    for i in range(uint(days)):
        d=parseday(start)+timedelta(days=i)
        out += [event(d,t,"Meal",n) for t,n in [("08:00","Breakfast"),("13:00","Lunch"),("16:30","Snack"),("20:00","Dinner")]]
        out += [event(d,t,"Water","Drink water") for t in ["07:00","09:00","11:00","13:00","15:00","17:00","19:00","21:00"]]
        out += [event(d,"17:30","Workout",workout_focus(profile.get("goal"),d)),event(d,"21:00","Check-in","Daily review")]
    return event_dedupe(out)
def streak(days,ref=None):
    s={parseday(x) for x in days};d=parseday(ref)
    if d not in s:return 0
    n=0
    while d in s:n+=1;d-=timedelta(days=1)
    return n
def moving_average(values,w=7):
    v=[ufloat(x) for x in values];return [sum(v[max(0,i-w+1):i+1])/len(v[max(0,i-w+1):i+1]) for i in range(len(v))]
def trend(values):
    v=[ufloat(x) for x in values]
    if len(v)<2:return {"change":0,"direction":"stable"}
    c=v[-1]-v[0];return {"change":c,"direction":"up" if c>0 else "down" if c<0 else "stable"}
def bmi(weight,height):return ufloat(weight)/(ufloat(height)/100)**2 if ufloat(height) else 0
def db_count2(table,where="",params=()):
    if table not in {"food_log","water","measurements","workouts","meal_status","profile"}:raise ValueError("table not allowed")
    con=db();q=f"SELECT COUNT(*) FROM {table}"+((" WHERE "+where) if where else "")
    try:return int(con.execute(q,params).fetchone()[0])
    finally:con.close()

def metric_0001(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0002(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":2,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0003(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":3,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0004(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":4,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0005(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":5,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0006(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":6,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0007(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":7,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0008(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":8,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0009(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":9,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0010(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":10,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0011(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":11,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0012(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":12,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0013(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":13,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0014(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":14,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0015(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":15,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0016(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":16,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0017(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":17,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0018(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":18,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0019(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":19,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0020(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":20,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0021(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":21,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0022(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":22,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0023(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":23,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0024(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":24,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0025(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":25,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0026(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":26,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0027(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":27,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0028(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":28,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0029(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":29,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0030(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":30,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0031(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":31,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0032(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":32,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0033(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":33,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0034(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":34,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0035(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":35,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0036(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":36,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0037(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":37,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0038(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":38,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0039(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":39,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0040(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":40,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0041(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":41,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0042(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":42,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0043(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":43,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0044(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":44,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0045(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":45,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0046(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":46,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0047(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":47,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0048(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":48,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0049(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":49,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0050(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":50,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0051(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":51,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0052(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":52,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0053(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":53,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0054(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":54,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0055(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":55,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0056(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":56,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0057(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":57,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0058(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":58,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0059(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":59,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0060(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":60,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0061(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":61,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0062(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":62,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0063(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":63,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0064(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":64,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0065(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":65,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0066(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":66,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0067(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":67,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0068(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":68,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0069(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":69,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0070(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":70,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0071(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":71,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0072(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":72,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0073(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":73,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0074(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":74,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0075(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":75,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0076(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":76,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0077(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":77,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0078(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":78,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0079(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":79,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0080(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":80,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0081(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":81,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0082(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":82,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0083(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":83,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0084(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":84,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0085(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":85,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0086(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":86,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0087(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":87,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0088(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":88,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0089(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":89,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0090(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":90,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0091(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":91,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0092(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":92,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0093(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":93,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0094(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":94,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0095(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":95,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0096(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":96,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0097(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":97,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0098(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":98,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0099(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":99,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0100(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":100,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0101(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":101,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0102(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":102,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0103(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":103,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0104(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":104,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0105(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":105,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0106(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":106,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0107(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":107,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0108(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":108,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0109(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":109,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0110(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":110,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0111(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":111,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0112(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":112,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0113(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":113,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0114(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":114,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0115(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":115,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0116(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":116,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0117(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":117,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0118(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":118,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0119(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":119,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0120(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":120,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0121(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":121,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0122(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":122,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0123(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":123,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0124(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":124,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0125(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":125,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0126(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":126,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0127(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":127,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0128(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":128,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0129(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":129,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0130(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":130,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0131(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":131,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0132(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":132,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0133(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":133,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0134(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":134,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0135(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":135,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0136(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":136,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0137(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":137,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0138(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":138,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0139(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":139,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0140(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":140,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0141(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":141,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0142(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":142,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0143(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":143,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0144(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":144,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0145(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":145,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0146(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":146,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0147(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":147,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0148(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":148,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0149(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":149,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0150(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":150,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0151(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":151,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0152(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":152,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0153(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":153,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0154(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":154,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0155(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":155,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0156(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":156,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0157(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":157,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0158(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":158,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0159(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":159,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0160(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":160,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0161(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":161,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0162(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":162,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0163(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":163,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0164(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":164,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0165(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":165,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0166(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":166,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0167(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":167,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0168(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":168,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0169(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":169,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0170(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":170,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0171(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":171,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0172(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":172,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0173(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":173,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0174(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":174,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0175(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":175,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0176(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":176,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0177(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":177,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0178(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":178,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0179(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":179,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0180(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":180,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0181(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":181,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0182(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":182,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0183(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":183,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0184(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":184,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0185(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":185,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0186(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":186,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0187(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":187,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0188(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":188,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0189(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":189,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0190(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":190,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0191(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":191,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0192(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":192,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0193(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":193,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0194(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":194,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0195(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":195,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0196(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":196,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0197(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":197,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0198(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":198,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0199(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":199,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0200(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":200,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0201(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":201,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0202(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":202,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0203(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":203,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0204(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":204,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0205(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":205,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0206(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":206,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0207(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":207,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0208(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":208,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0209(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":209,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0210(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":210,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0211(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":211,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0212(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":212,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0213(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":213,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0214(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":214,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0215(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":215,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0216(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":216,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0217(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":217,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0218(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":218,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0219(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":219,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0220(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":220,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0221(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":221,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0222(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":222,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0223(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":223,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0224(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":224,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0225(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":225,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0226(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":226,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0227(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":227,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0228(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":228,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0229(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":229,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0230(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":230,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0231(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":231,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0232(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":232,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0233(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":233,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0234(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":234,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0235(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":235,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0236(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":236,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0237(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":237,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0238(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":238,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0239(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":239,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0240(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":240,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0241(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":241,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0242(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":242,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0243(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":243,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0244(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":244,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0245(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":245,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0246(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":246,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0247(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":247,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0248(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":248,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0249(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":249,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0250(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":250,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0251(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":251,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0252(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":252,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0253(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":253,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0254(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":254,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0255(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":255,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0256(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":256,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0257(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":257,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0258(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":258,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0259(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":259,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0260(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":260,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0261(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":261,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0262(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":262,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0263(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":263,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0264(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":264,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0265(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":265,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0266(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":266,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0267(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":267,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0268(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":268,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0269(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":269,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0270(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":270,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0271(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":271,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0272(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":272,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0273(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":273,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0274(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":274,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0275(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":275,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0276(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":276,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0277(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":277,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0278(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":278,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0279(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":279,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0280(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":280,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0281(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":281,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0282(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":282,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0283(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":283,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0284(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":284,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0285(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":285,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0286(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":286,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0287(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":287,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0288(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":288,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0289(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":289,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0290(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":290,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0291(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":291,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0292(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":292,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0293(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":293,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0294(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":294,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0295(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":295,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0296(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":296,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0297(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":297,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0298(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":298,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0299(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":299,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0300(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":300,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0301(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":301,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0302(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":302,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0303(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":303,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0304(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":304,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0305(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":305,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0306(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":306,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0307(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":307,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0308(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":308,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0309(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":309,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0310(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":310,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0311(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":311,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0312(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":312,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0313(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":313,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0314(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":314,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0315(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":315,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0316(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":316,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0317(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":317,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0318(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":318,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0319(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":319,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0320(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":320,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0321(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":321,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0322(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":322,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0323(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":323,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0324(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":324,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0325(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":325,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0326(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":326,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0327(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":327,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0328(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":328,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0329(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":329,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0330(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":330,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0331(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":331,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0332(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":332,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0333(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":333,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0334(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":334,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0335(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":335,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0336(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":336,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0337(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":337,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0338(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":338,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0339(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":339,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0340(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":340,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0341(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":341,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0342(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":342,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0343(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":343,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0344(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":344,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0345(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":345,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0346(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":346,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0347(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":347,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0348(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":348,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0349(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":349,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0350(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":350,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0351(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":351,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0352(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":352,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0353(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":353,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0354(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":354,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0355(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":355,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0356(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":356,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0357(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":357,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0358(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":358,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0359(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":359,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0360(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":360,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0361(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":361,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0362(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":362,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0363(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":363,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0364(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":364,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0365(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":365,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0366(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":366,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0367(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":367,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0368(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":368,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0369(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":369,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0370(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":370,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0371(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":371,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0372(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":372,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0373(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":373,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0374(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":374,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0375(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":375,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0376(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":376,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0377(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":377,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0378(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":378,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0379(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":379,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0380(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":380,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0381(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":381,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0382(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":382,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0383(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":383,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0384(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":384,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0385(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":385,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0386(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":386,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0387(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":387,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0388(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":388,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0389(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":389,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0390(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":390,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0391(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":391,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0392(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":392,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0393(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":393,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0394(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":394,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0395(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":395,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0396(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":396,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0397(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":397,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0398(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":398,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0399(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":399,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0400(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":400,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0401(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":401,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0402(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":402,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0403(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":403,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0404(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":404,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0405(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":405,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0406(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":406,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0407(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":407,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0408(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":408,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0409(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":409,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0410(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":410,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0411(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":411,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0412(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":412,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0413(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":413,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0414(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":414,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0415(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":415,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0416(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":416,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0417(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":417,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0418(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":418,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0419(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":419,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0420(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":420,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0421(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":421,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0422(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":422,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0423(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":423,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0424(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":424,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0425(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":425,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0426(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":426,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0427(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":427,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0428(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":428,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0429(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":429,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0430(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":430,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0431(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":431,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0432(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":432,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0433(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":433,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0434(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":434,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0435(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":435,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0436(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":436,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0437(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":437,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0438(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":438,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0439(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":439,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0440(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":440,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0441(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":441,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0442(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":442,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0443(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":443,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0444(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":444,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0445(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":445,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0446(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":446,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0447(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":447,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0448(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":448,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0449(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":449,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0450(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":450,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0451(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":451,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0452(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":452,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0453(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":453,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0454(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":454,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0455(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":455,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0456(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":456,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0457(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":457,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0458(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":458,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0459(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":459,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0460(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":460,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0461(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":461,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0462(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":462,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0463(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":463,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0464(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":464,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0465(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":465,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0466(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":466,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0467(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":467,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0468(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":468,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0469(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":469,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0470(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":470,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0471(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":471,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0472(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":472,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0473(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":473,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0474(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":474,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0475(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":475,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0476(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":476,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0477(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":477,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0478(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":478,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0479(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":479,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0480(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":480,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0481(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":481,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0482(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":482,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0483(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":483,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0484(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":484,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0485(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":485,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0486(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":486,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0487(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":487,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0488(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":488,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0489(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":489,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0490(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":490,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0491(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":491,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0492(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":492,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0493(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":493,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0494(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":494,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0495(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":495,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0496(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":496,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0497(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":497,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0498(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":498,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0499(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":499,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0500(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":500,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0501(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":501,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0502(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":502,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0503(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":503,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0504(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":504,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0505(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":505,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0506(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":506,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0507(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":507,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0508(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":508,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0509(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":509,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0510(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":510,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0511(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":511,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0512(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":512,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0513(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":513,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0514(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":514,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0515(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":515,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0516(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":516,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0517(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":517,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0518(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":518,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0519(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":519,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0520(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":520,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0521(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":521,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0522(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":522,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0523(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":523,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0524(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":524,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0525(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":525,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0526(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":526,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0527(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":527,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0528(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":528,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0529(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":529,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0530(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":530,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0531(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":531,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0532(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":532,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0533(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":533,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0534(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":534,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0535(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":535,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0536(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":536,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0537(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":537,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0538(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":538,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0539(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":539,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0540(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":540,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0541(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":541,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0542(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":542,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0543(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":543,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0544(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":544,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0545(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":545,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0546(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":546,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0547(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":547,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0548(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":548,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0549(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":549,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0550(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":550,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0551(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":551,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0552(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":552,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0553(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":553,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0554(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":554,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0555(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":555,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0556(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":556,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0557(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":557,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0558(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":558,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0559(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":559,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0560(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":560,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0561(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":561,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0562(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":562,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0563(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":563,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0564(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":564,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0565(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":565,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0566(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":566,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0567(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":567,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0568(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":568,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0569(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":569,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0570(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":570,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0571(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":571,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0572(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":572,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0573(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":573,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0574(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":574,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0575(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":575,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0576(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":576,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0577(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":577,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0578(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":578,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0579(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":579,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0580(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":580,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0581(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":581,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0582(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":582,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0583(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":583,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0584(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":584,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0585(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":585,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0586(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":586,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0587(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":587,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0588(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":588,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0589(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":589,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0590(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":590,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0591(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":591,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0592(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":592,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0593(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":593,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0594(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":594,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0595(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":595,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0596(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":596,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0597(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":597,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0598(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":598,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0599(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":599,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0600(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":600,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0601(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":601,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0602(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":602,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0603(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":603,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0604(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":604,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0605(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":605,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0606(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":606,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0607(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":607,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0608(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":608,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0609(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":609,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0610(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":610,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0611(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":611,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0612(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":612,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0613(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":613,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0614(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":614,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0615(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":615,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0616(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":616,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0617(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":617,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0618(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":618,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0619(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":619,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0620(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":620,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0621(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":621,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0622(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":622,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0623(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":623,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0624(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":624,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0625(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":625,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0626(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":626,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0627(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":627,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0628(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":628,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0629(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":629,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0630(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":630,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0631(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":631,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0632(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":632,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0633(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":633,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0634(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":634,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0635(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":635,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0636(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":636,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0637(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":637,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0638(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":638,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0639(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":639,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0640(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":640,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0641(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":641,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0642(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":642,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0643(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":643,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0644(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":644,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0645(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":645,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0646(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":646,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0647(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":647,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0648(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":648,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0649(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":649,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0650(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":650,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0651(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":651,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0652(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":652,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0653(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":653,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0654(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":654,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0655(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":655,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0656(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":656,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0657(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":657,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0658(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":658,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0659(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":659,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0660(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":660,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0661(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":661,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0662(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":662,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0663(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":663,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0664(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":664,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0665(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":665,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0666(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":666,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0667(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":667,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0668(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":668,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0669(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":669,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0670(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":670,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0671(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":671,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0672(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":672,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0673(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":673,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0674(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":674,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0675(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":675,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0676(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":676,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0677(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":677,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0678(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":678,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0679(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":679,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0680(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":680,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0681(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":681,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0682(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":682,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0683(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":683,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0684(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":684,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0685(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":685,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0686(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":686,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0687(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":687,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0688(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":688,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0689(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":689,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0690(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":690,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0691(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":691,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0692(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":692,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0693(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":693,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0694(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":694,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0695(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":695,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0696(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":696,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0697(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":697,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0698(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":698,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0699(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":699,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0700(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":700,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0701(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":701,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0702(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":702,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0703(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":703,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0704(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":704,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0705(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":705,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0706(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":706,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0707(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":707,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0708(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":708,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0709(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":709,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0710(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":710,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0711(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":711,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0712(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":712,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0713(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":713,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0714(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":714,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0715(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":715,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0716(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":716,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0717(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":717,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0718(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":718,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0719(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":719,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0720(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":720,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0721(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":721,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0722(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":722,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0723(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":723,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0724(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":724,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0725(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":725,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0726(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":726,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0727(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":727,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0728(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":728,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0729(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":729,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0730(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":730,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0731(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":731,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0732(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":732,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0733(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":733,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0734(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":734,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0735(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":735,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0736(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":736,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0737(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":737,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0738(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":738,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0739(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":739,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0740(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":740,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0741(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":741,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0742(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":742,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0743(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":743,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0744(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":744,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0745(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":745,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0746(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":746,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0747(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":747,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0748(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":748,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0749(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":749,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0750(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":750,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0751(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":751,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0752(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":752,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0753(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":753,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0754(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":754,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0755(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":755,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0756(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":756,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0757(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":757,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0758(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":758,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0759(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":759,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0760(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":760,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0761(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":761,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0762(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":762,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0763(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":763,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0764(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":764,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0765(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":765,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0766(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":766,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0767(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":767,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0768(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":768,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0769(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":769,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0770(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":770,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0771(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":771,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0772(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":772,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0773(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":773,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0774(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":774,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0775(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":775,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0776(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":776,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0777(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":777,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0778(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":778,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0779(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":779,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0780(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":780,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0781(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":781,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0782(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":782,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0783(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":783,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0784(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":784,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0785(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":785,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0786(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":786,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0787(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":787,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0788(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":788,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0789(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":789,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0790(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":790,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0791(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":791,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0792(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":792,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0793(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":793,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0794(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":794,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0795(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":795,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0796(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":796,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0797(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":797,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0798(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":798,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0799(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":799,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0800(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":800,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0801(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":801,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0802(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":802,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0803(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":803,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0804(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":804,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0805(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":805,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0806(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":806,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0807(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":807,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0808(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":808,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0809(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":809,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0810(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":810,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0811(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":811,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0812(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":812,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0813(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":813,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0814(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":814,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0815(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":815,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0816(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":816,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0817(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":817,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0818(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":818,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0819(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":819,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0820(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":820,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0821(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":821,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0822(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":822,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0823(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":823,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0824(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":824,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0825(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":825,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0826(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":826,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0827(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":827,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0828(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":828,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0829(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":829,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0830(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":830,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0831(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":831,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0832(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":832,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0833(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":833,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0834(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":834,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0835(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":835,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0836(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":836,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0837(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":837,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0838(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":838,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0839(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":839,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0840(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":840,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0841(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":841,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0842(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":842,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0843(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":843,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0844(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":844,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0845(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":845,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0846(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":846,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0847(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":847,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0848(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":848,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0849(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":849,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0850(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":850,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0851(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":851,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0852(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":852,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0853(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":853,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0854(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":854,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0855(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":855,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0856(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":856,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0857(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":857,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0858(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":858,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0859(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":859,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0860(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":860,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0861(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":861,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0862(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":862,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0863(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":863,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0864(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":864,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0865(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":865,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0866(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":866,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0867(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":867,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0868(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":868,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0869(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":869,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0870(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":870,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0871(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":871,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0872(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":872,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0873(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":873,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0874(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":874,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0875(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":875,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0876(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":876,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0877(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":877,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0878(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":878,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0879(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":879,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0880(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":880,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0881(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":881,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0882(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":882,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0883(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":883,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0884(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":884,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0885(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":885,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0886(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":886,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0887(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":887,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0888(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":888,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0889(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":889,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0890(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":890,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0891(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":891,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0892(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":892,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0893(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":893,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0894(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":894,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0895(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":895,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0896(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":896,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0897(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":897,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0898(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":898,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0899(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":899,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0900(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":900,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0901(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":901,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0902(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":902,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0903(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":903,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0904(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":904,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0905(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":905,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0906(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":906,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0907(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":907,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0908(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":908,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0909(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":909,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0910(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":910,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0911(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":911,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0912(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":912,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0913(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":913,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0914(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":914,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0915(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":915,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0916(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":916,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0917(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":917,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0918(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":918,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0919(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":919,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0920(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":920,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0921(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":921,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0922(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":922,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0923(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":923,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0924(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":924,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0925(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":925,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0926(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":926,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0927(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":927,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0928(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":928,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0929(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":929,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0930(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":930,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0931(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":931,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0932(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":932,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0933(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":933,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0934(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":934,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0935(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":935,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0936(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":936,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0937(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":937,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0938(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":938,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0939(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":939,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0940(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":940,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0941(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":941,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0942(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":942,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0943(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":943,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0944(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":944,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0945(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":945,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0946(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":946,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0947(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":947,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0948(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":948,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0949(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":949,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0950(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":950,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0951(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":951,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0952(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":952,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0953(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":953,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0954(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":954,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0955(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":955,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0956(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":956,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0957(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":957,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0958(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":958,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0959(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":959,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0960(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":960,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0961(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":961,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0962(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":962,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0963(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":963,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0964(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":964,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0965(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":965,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0966(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":966,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0967(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":967,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0968(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":968,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0969(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":969,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0970(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":970,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0971(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":971,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0972(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":972,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0973(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":973,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0974(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":974,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0975(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":975,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0976(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":976,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0977(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":977,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0978(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":978,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0979(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":979,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0980(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":980,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0981(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":981,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0982(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":982,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0983(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":983,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0984(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":984,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0985(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":985,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0986(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":986,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0987(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":987,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0988(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":988,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0989(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":989,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0990(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":990,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0991(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":991,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0992(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":992,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0993(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":993,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0994(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":994,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0995(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":995,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0996(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":996,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0997(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":997,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0998(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":998,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_0999(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":999,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1000(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1000,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1001(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1001,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1002(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1002,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1003(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1003,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1004(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1004,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1005(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1005,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1006(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1006,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1007(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1007,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1008(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1008,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1009(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1009,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1010(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1010,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1011(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1011,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1012(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1012,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1013(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1013,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1014(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1014,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1015(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1015,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1016(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1016,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1017(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1017,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1018(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1018,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1019(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1019,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1020(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1020,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1021(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1021,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1022(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1022,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1023(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1023,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1024(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1024,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1025(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1025,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1026(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1026,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1027(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1027,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1028(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1028,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1029(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1029,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1030(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1030,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1031(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1031,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1032(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1032,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1033(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1033,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1034(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1034,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1035(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1035,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1036(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1036,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1037(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1037,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1038(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1038,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1039(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1039,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1040(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1040,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1041(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1041,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1042(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1042,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1043(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1043,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1044(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1044,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1045(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1045,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1046(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1046,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1047(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1047,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1048(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1048,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1049(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1049,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1050(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1050,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1051(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1051,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1052(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1052,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1053(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1053,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1054(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1054,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1055(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1055,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1056(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1056,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1057(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1057,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1058(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1058,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1059(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1059,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1060(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1060,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1061(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1061,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1062(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1062,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1063(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1063,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1064(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1064,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1065(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1065,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1066(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1066,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1067(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1067,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1068(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1068,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1069(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1069,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1070(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1070,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1071(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1071,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1072(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1072,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1073(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1073,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1074(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1074,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1075(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1075,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1076(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1076,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1077(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1077,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1078(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1078,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1079(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1079,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1080(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1080,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1081(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1081,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1082(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1082,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1083(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1083,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1084(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1084,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1085(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1085,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1086(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1086,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1087(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1087,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1088(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1088,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1089(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1089,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1090(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1090,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1091(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1091,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1092(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1092,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1093(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1093,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1094(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1094,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1095(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1095,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1096(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1096,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1097(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1097,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1098(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1098,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1099(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1099,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1100(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1100,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1101(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1101,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1102(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1102,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1103(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1103,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1104(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1104,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1105(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1105,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1106(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1106,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1107(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1107,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1108(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1108,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1109(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1109,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1110(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1110,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1111(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1111,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1112(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1112,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1113(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1113,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1114(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1114,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1115(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1115,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1116(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1116,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1117(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1117,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1118(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1118,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1119(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1119,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1120(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1120,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1121(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1121,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1122(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1122,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1123(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1123,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1124(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1124,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1125(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1125,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1126(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1126,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1127(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1127,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1128(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1128,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1129(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1129,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1130(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1130,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1131(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1131,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1132(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1132,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1133(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1133,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1134(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1134,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1135(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1135,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1136(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1136,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1137(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1137,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1138(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1138,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1139(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1139,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1140(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1140,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1141(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1141,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1142(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1142,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1143(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1143,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1144(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1144,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1145(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1145,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1146(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1146,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1147(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1147,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1148(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1148,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1149(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1149,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1150(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1150,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1151(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1151,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1152(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1152,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1153(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1153,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1154(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1154,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1155(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1155,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1156(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1156,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1157(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1157,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1158(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1158,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1159(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1159,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1160(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1160,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1161(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1161,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1162(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1162,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1163(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1163,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1164(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1164,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1165(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1165,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1166(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1166,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1167(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1167,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1168(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1168,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1169(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1169,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1170(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1170,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1171(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1171,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1172(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1172,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1173(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1173,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1174(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1174,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1175(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1175,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1176(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1176,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1177(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1177,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1178(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1178,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1179(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1179,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1180(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1180,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1181(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1181,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1182(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1182,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1183(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1183,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1184(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1184,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1185(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1185,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1186(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1186,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1187(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1187,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1188(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1188,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1189(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1189,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1190(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1190,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1191(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1191,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1192(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1192,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1193(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1193,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1194(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1194,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1195(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1195,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1196(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1196,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1197(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1197,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1198(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1198,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1199(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1199,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1200(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1200,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1201(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1201,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1202(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1202,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1203(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1203,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1204(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1204,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1205(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1205,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1206(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1206,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1207(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1207,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1208(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1208,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1209(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1209,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1210(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1210,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1211(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1211,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1212(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1212,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1213(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1213,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1214(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1214,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1215(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1215,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1216(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1216,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1217(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1217,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1218(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1218,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1219(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1219,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1220(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1220,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1221(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1221,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1222(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1222,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1223(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1223,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1224(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1224,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1225(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1225,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1226(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1226,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1227(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1227,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1228(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1228,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1229(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1229,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1230(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1230,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1231(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1231,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1232(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1232,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1233(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1233,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1234(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1234,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1235(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1235,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1236(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1236,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1237(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1237,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1238(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1238,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1239(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1239,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1240(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1240,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1241(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1241,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1242(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1242,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1243(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1243,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1244(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1244,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1245(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1245,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1246(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1246,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1247(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1247,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1248(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1248,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1249(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1249,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1250(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1250,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1251(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1251,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1252(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1252,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1253(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1253,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1254(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1254,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1255(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1255,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1256(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1256,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1257(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1257,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1258(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1258,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1259(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1259,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1260(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1260,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1261(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1261,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1262(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1262,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1263(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1263,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1264(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1264,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1265(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1265,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1266(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1266,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1267(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1267,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1268(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1268,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1269(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1269,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1270(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1270,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1271(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1271,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1272(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1272,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1273(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1273,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1274(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1274,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1275(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1275,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1276(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1276,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1277(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1277,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1278(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1278,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1279(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1279,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1280(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1280,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1281(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1281,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1282(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1282,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1283(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1283,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1284(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1284,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1285(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1285,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1286(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1286,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1287(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1287,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1288(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1288,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1289(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1289,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1290(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1290,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1291(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1291,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1292(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1292,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1293(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1293,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1294(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1294,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1295(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1295,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1296(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1296,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1297(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1297,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1298(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1298,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1299(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1299,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1300(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1300,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1301(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1301,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1302(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1302,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1303(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1303,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1304(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1304,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1305(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1305,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1306(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1306,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1307(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1307,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1308(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1308,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1309(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1309,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1310(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1310,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1311(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1311,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1312(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1312,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1313(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1313,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1314(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1314,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1315(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1315,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1316(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1316,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1317(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1317,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1318(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1318,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1319(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1319,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1320(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1320,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1321(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1321,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1322(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1322,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1323(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1323,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1324(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1324,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1325(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1325,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1326(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1326,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1327(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1327,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1328(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1328,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1329(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1329,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1330(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1330,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1331(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1331,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1332(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1332,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1333(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1333,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1334(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1334,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1335(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1335,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1336(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1336,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1337(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1337,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1338(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1338,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1339(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1339,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1340(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1340,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1341(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1341,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1342(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1342,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1343(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1343,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1344(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1344,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1345(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1345,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1346(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1346,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1347(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1347,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1348(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1348,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1349(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1349,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1350(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1350,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1351(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1351,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1352(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1352,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1353(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1353,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1354(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1354,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1355(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1355,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1356(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1356,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1357(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1357,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1358(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1358,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1359(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1359,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1360(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1360,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1361(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1361,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1362(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1362,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1363(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1363,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1364(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1364,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1365(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1365,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1366(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1366,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1367(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1367,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1368(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1368,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1369(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1369,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1370(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1370,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1371(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1371,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1372(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1372,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1373(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1373,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1374(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1374,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1375(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1375,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1376(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1376,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1377(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1377,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1378(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1378,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1379(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1379,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1380(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1380,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1381(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1381,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1382(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1382,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1383(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1383,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1384(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1384,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1385(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1385,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1386(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1386,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1387(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1387,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1388(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1388,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1389(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1389,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1390(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1390,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1391(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1391,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1392(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1392,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1393(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1393,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1394(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1394,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1395(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1395,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1396(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1396,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1397(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1397,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1398(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1398,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1399(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1399,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1400(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1400,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1401(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1401,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1402(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1402,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1403(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1403,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1404(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1404,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1405(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1405,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1406(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1406,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1407(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1407,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1408(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1408,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1409(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1409,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1410(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1410,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1411(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1411,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1412(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1412,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1413(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1413,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1414(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1414,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1415(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1415,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1416(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1416,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1417(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1417,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1418(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1418,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1419(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1419,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1420(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1420,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1421(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1421,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1422(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1422,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1423(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1423,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1424(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1424,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1425(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1425,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1426(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1426,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1427(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1427,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1428(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1428,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1429(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1429,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1430(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1430,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1431(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1431,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1432(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1432,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1433(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1433,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1434(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1434,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1435(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1435,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1436(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1436,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1437(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1437,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1438(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1438,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1439(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1439,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1440(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1440,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1441(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1441,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1442(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1442,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1443(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1443,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1444(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1444,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1445(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1445,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1446(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1446,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1447(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1447,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1448(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1448,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1449(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1449,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1450(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1450,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1451(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1451,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1452(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1452,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1453(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1453,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1454(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1454,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1455(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1455,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1456(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1456,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1457(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1457,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1458(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1458,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1459(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1459,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1460(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1460,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1461(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1461,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1462(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1462,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1463(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1463,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1464(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1464,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1465(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1465,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1466(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1466,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1467(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1467,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1468(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1468,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1469(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1469,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1470(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1470,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1471(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1471,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1472(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1472,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1473(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1473,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1474(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1474,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1475(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1475,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1476(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1476,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1477(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1477,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1478(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1478,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1479(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1479,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1480(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1480,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1481(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1481,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1482(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1482,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1483(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1483,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1484(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1484,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1485(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1485,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1486(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1486,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1487(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1487,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1488(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1488,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1489(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1489,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1490(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1490,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1491(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1491,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1492(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1492,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1493(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1493,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1494(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1494,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1495(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1495,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1496(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1496,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1497(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1497,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1498(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1498,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1499(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1499,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1500(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1500,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1501(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1501,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1502(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1502,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1503(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1503,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1504(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1504,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1505(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1505,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1506(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1506,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1507(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1507,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1508(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1508,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1509(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1509,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1510(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1510,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1511(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1511,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1512(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1512,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1513(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1513,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1514(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1514,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1515(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1515,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1516(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1516,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1517(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1517,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1518(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1518,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1519(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1519,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1520(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1520,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1521(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1521,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1522(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1522,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1523(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1523,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1524(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1524,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1525(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1525,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1526(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1526,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1527(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1527,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1528(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1528,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1529(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1529,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1530(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1530,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1531(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1531,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1532(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1532,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1533(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1533,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1534(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1534,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1535(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1535,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1536(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1536,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1537(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1537,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1538(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1538,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1539(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1539,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1540(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1540,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1541(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1541,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1542(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1542,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1543(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1543,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1544(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1544,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1545(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1545,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1546(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1546,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1547(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1547,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1548(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1548,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1549(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1549,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1550(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1550,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1551(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1551,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1552(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1552,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1553(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1553,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1554(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1554,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1555(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1555,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1556(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1556,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1557(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1557,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1558(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1558,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1559(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1559,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1560(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1560,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1561(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1561,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1562(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1562,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1563(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1563,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1564(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1564,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1565(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1565,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1566(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1566,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1567(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1567,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1568(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1568,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1569(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1569,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1570(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1570,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1571(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1571,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1572(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1572,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1573(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1573,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1574(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1574,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1575(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1575,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1576(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1576,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1577(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1577,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1578(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1578,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1579(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1579,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1580(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1580,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1581(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1581,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1582(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1582,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1583(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1583,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1584(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1584,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1585(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1585,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1586(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1586,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1587(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1587,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1588(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1588,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1589(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1589,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1590(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1590,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1591(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1591,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1592(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1592,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1593(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1593,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1594(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1594,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1595(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1595,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1596(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1596,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1597(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1597,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1598(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1598,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1599(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1599,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1600(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1600,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1601(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1601,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1602(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1602,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1603(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1603,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1604(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1604,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1605(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1605,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1606(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1606,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1607(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1607,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1608(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1608,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1609(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1609,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1610(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1610,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1611(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1611,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1612(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1612,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1613(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1613,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1614(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1614,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1615(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1615,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1616(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1616,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1617(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1617,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1618(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1618,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1619(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1619,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1620(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1620,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1621(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1621,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1622(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1622,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1623(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1623,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1624(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1624,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1625(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1625,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1626(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1626,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1627(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1627,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1628(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1628,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1629(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1629,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1630(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1630,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1631(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1631,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1632(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1632,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1633(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1633,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1634(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1634,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1635(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1635,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1636(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1636,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1637(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1637,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1638(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1638,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1639(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1639,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1640(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1640,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1641(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1641,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1642(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1642,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1643(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1643,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1644(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1644,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1645(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1645,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1646(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1646,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1647(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1647,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1648(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1648,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1649(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1649,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1650(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1650,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1651(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1651,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1652(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1652,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1653(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1653,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1654(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1654,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1655(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1655,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1656(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1656,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1657(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1657,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1658(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1658,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1659(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1659,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1660(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1660,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1661(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1661,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1662(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1662,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1663(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1663,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1664(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1664,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1665(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1665,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1666(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1666,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1667(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1667,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1668(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1668,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1669(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1669,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1670(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1670,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1671(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1671,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1672(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1672,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1673(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1673,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1674(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1674,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1675(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1675,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1676(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1676,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1677(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1677,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1678(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1678,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1679(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1679,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1680(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1680,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1681(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1681,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1682(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1682,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1683(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1683,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1684(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1684,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1685(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1685,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1686(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1686,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1687(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1687,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1688(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1688,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1689(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1689,"field":'arms',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1690(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1690,"field":'legs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1691(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1691,"field":'shoulders',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1692(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1692,"field":'calories',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1693(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1693,"field":'protein',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1694(value=0,target=0,scale=1.0):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1694,"field":'carbs',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1695(value=0,target=0,scale=1.1):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1695,"field":'fat',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1696(value=0,target=0,scale=1.2):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1696,"field":'fiber',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1697(value=0,target=0,scale=1.3):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1697,"field":'water',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1698(value=0,target=0,scale=1.4):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1698,"field":'weight',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1699(value=0,target=0,scale=1.5):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1699,"field":'waist',"current":current,"target":goal,"gap":gap,"percent":percent}

def metric_1700(value=0,target=0,scale=1.6):
    current=ufloat(value)*scale
    goal=ufloat(target)*scale
    gap=goal-current
    percent=pct(current,goal)
    return {"id":1700,"field":'chest',"current":current,"target":goal,"gap":gap,"percent":percent}

def exercise_0001(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":1,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0002(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":2,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0003(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":3,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0004(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":4,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0005(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":5,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0006(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":6,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0007(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":7,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0008(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":8,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0009(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":9,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0010(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":10,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0011(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":11,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0012(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":12,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0013(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":13,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0014(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":14,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0015(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":15,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0016(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":16,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0017(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":17,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0018(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":18,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0019(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":19,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0020(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":20,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0021(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":21,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0022(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":22,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0023(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":23,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0024(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":24,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0025(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":25,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0026(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":26,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0027(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":27,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0028(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":28,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0029(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":29,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0030(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":30,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0031(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":31,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0032(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":32,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0033(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":33,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0034(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":34,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0035(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":35,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0036(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":36,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0037(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":37,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0038(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":38,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0039(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":39,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0040(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":40,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0041(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":41,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0042(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":42,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0043(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":43,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0044(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":44,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0045(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":45,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0046(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":46,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0047(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":47,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0048(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":48,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0049(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":49,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0050(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":50,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0051(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":51,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0052(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":52,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0053(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":53,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0054(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":54,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0055(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":55,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0056(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":56,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0057(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":57,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0058(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":58,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0059(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":59,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0060(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":60,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0061(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":61,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0062(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":62,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0063(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":63,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0064(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":64,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0065(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":65,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0066(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":66,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0067(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":67,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0068(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":68,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0069(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":69,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0070(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":70,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0071(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":71,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0072(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":72,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0073(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":73,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0074(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":74,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0075(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":75,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0076(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":76,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0077(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":77,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0078(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":78,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0079(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":79,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0080(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":80,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0081(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":81,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0082(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":82,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0083(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":83,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0084(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":84,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0085(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":85,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0086(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":86,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0087(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":87,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0088(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":88,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0089(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":89,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0090(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":90,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0091(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":91,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0092(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":92,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0093(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":93,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0094(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":94,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0095(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":95,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0096(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":96,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0097(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":97,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0098(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":98,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0099(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":99,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0100(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":100,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0101(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":101,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0102(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":102,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0103(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":103,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0104(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":104,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0105(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":105,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0106(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":106,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0107(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":107,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0108(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":108,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0109(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":109,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0110(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":110,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0111(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":111,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0112(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":112,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0113(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":113,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0114(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":114,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0115(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":115,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0116(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":116,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0117(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":117,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0118(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":118,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0119(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":119,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0120(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":120,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0121(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":121,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0122(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":122,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0123(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":123,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0124(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":124,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0125(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":125,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0126(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":126,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0127(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":127,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0128(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":128,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0129(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":129,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0130(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":130,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0131(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":131,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0132(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":132,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0133(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":133,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0134(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":134,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0135(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":135,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0136(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":136,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0137(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":137,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0138(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":138,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0139(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":139,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0140(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":140,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0141(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":141,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0142(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":142,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0143(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":143,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0144(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":144,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0145(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":145,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0146(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":146,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0147(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":147,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0148(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":148,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0149(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":149,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0150(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":150,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0151(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":151,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0152(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":152,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0153(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":153,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0154(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":154,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0155(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":155,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0156(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":156,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0157(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":157,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0158(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":158,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0159(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":159,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0160(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":160,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0161(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":161,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0162(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":162,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0163(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":163,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0164(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":164,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0165(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":165,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0166(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":166,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0167(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":167,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0168(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":168,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0169(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":169,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0170(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":170,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0171(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":171,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0172(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":172,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0173(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":173,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0174(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":174,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0175(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":175,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0176(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":176,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0177(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":177,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0178(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":178,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0179(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":179,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0180(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":180,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0181(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":181,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0182(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":182,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0183(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":183,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0184(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":184,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0185(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":185,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0186(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":186,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0187(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":187,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0188(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":188,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0189(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":189,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0190(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":190,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0191(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":191,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0192(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":192,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0193(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":193,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0194(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":194,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0195(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":195,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0196(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":196,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0197(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":197,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0198(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":198,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0199(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":199,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0200(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":200,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0201(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":201,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0202(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":202,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0203(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":203,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0204(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":204,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0205(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":205,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0206(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":206,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0207(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":207,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0208(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":208,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0209(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":209,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0210(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":210,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0211(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":211,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0212(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":212,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0213(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":213,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0214(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":214,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0215(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":215,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0216(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":216,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0217(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":217,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0218(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":218,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0219(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":219,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0220(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":220,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0221(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":221,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0222(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":222,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0223(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":223,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0224(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":224,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0225(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":225,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0226(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":226,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0227(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":227,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0228(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":228,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0229(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":229,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0230(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":230,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0231(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":231,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0232(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":232,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0233(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":233,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0234(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":234,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0235(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":235,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0236(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":236,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0237(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":237,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0238(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":238,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0239(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":239,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0240(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":240,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0241(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":241,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0242(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":242,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0243(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":243,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0244(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":244,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0245(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":245,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0246(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":246,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0247(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":247,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0248(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":248,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0249(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":249,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0250(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":250,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0251(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":251,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0252(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":252,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0253(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":253,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0254(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":254,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0255(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":255,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0256(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":256,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0257(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":257,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0258(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":258,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0259(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":259,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0260(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":260,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0261(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":261,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0262(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":262,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0263(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":263,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0264(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":264,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0265(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":265,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0266(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":266,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0267(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":267,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0268(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":268,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0269(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":269,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0270(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":270,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0271(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":271,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0272(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":272,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0273(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":273,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0274(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":274,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0275(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":275,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0276(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":276,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0277(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":277,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0278(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":278,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0279(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":279,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0280(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":280,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0281(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":281,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0282(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":282,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0283(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":283,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0284(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":284,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0285(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":285,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0286(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":286,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0287(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":287,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0288(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":288,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0289(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":289,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0290(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":290,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0291(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":291,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0292(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":292,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0293(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":293,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0294(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":294,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0295(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":295,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0296(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":296,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0297(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":297,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0298(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":298,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0299(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":299,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0300(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":300,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0301(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":301,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0302(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":302,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0303(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":303,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0304(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":304,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0305(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":305,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0306(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":306,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0307(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":307,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0308(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":308,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0309(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":309,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0310(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":310,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0311(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":311,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0312(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":312,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0313(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":313,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0314(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":314,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0315(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":315,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0316(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":316,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0317(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":317,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0318(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":318,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0319(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":319,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0320(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":320,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0321(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":321,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0322(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":322,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0323(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":323,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0324(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":324,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0325(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":325,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0326(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":326,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0327(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":327,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0328(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":328,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0329(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":329,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0330(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":330,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0331(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":331,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0332(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":332,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0333(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":333,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0334(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":334,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0335(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":335,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0336(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":336,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0337(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":337,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0338(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":338,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0339(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":339,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0340(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":340,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0341(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":341,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0342(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":342,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0343(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":343,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0344(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":344,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0345(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":345,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0346(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":346,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0347(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":347,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0348(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":348,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0349(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":349,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0350(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":350,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0351(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":351,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0352(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":352,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0353(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":353,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0354(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":354,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0355(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":355,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0356(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":356,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0357(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":357,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0358(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":358,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0359(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":359,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0360(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":360,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0361(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":361,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0362(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":362,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0363(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":363,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0364(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":364,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0365(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":365,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0366(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":366,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0367(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":367,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0368(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":368,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0369(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":369,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0370(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":370,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0371(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":371,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0372(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":372,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0373(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":373,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0374(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":374,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0375(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":375,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0376(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":376,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0377(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":377,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0378(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":378,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0379(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":379,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0380(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":380,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0381(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":381,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0382(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":382,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0383(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":383,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0384(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":384,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0385(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":385,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0386(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":386,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0387(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":387,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0388(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":388,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0389(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":389,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0390(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":390,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0391(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":391,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0392(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":392,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0393(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":393,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0394(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":394,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0395(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":395,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0396(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":396,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0397(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":397,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0398(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":398,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0399(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":399,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0400(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":400,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0401(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":401,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0402(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":402,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0403(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":403,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0404(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":404,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0405(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":405,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0406(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":406,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0407(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":407,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0408(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":408,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0409(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":409,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0410(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":410,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0411(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":411,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0412(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":412,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0413(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":413,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0414(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":414,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0415(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":415,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0416(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":416,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0417(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":417,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0418(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":418,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0419(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":419,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0420(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":420,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0421(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":421,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0422(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":422,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0423(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":423,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0424(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":424,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0425(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":425,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0426(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":426,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0427(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":427,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0428(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":428,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0429(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":429,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0430(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":430,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0431(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":431,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0432(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":432,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0433(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":433,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0434(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":434,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0435(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":435,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0436(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":436,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0437(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":437,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0438(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":438,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0439(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":439,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0440(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":440,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0441(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":441,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0442(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":442,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0443(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":443,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0444(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":444,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0445(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":445,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0446(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":446,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0447(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":447,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0448(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":448,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0449(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":449,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0450(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":450,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0451(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":451,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0452(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":452,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0453(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":453,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0454(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":454,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0455(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":455,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0456(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":456,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0457(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":457,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0458(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":458,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0459(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":459,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0460(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":460,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0461(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":461,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0462(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":462,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0463(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":463,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0464(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":464,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0465(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":465,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0466(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":466,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0467(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":467,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0468(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":468,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0469(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":469,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0470(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":470,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0471(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":471,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0472(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":472,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0473(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":473,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0474(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":474,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0475(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":475,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0476(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":476,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0477(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":477,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0478(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":478,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0479(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":479,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0480(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":480,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0481(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":481,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0482(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":482,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0483(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":483,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0484(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":484,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0485(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":485,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0486(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":486,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0487(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":487,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0488(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":488,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0489(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":489,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0490(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":490,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0491(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":491,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0492(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":492,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0493(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":493,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0494(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":494,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0495(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":495,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0496(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":496,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0497(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":497,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0498(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":498,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0499(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":499,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0500(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":500,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0501(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":501,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0502(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":502,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0503(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":503,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0504(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":504,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0505(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":505,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0506(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":506,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0507(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":507,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0508(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":508,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0509(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":509,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0510(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":510,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0511(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":511,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0512(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":512,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0513(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":513,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0514(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":514,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0515(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":515,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0516(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":516,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0517(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":517,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0518(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":518,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0519(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":519,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0520(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":520,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0521(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":521,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0522(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":522,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0523(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":523,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0524(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":524,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0525(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":525,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0526(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":526,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0527(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":527,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0528(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":528,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0529(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":529,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0530(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":530,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0531(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":531,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0532(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":532,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0533(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":533,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0534(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":534,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0535(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":535,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0536(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":536,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0537(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":537,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0538(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":538,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0539(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":539,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0540(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":540,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0541(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":541,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0542(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":542,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0543(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":543,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0544(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":544,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0545(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":545,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0546(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":546,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0547(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":547,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0548(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":548,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0549(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":549,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0550(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":550,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0551(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":551,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0552(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":552,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0553(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":553,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0554(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":554,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0555(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":555,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0556(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":556,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0557(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":557,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0558(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":558,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0559(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":559,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0560(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":560,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0561(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":561,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0562(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":562,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0563(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":563,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0564(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":564,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0565(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":565,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0566(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":566,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0567(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":567,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0568(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":568,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0569(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":569,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0570(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":570,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0571(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":571,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0572(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":572,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0573(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":573,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0574(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":574,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0575(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":575,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0576(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":576,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0577(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":577,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0578(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":578,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0579(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":579,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0580(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":580,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0581(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":581,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0582(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":582,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0583(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":583,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0584(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":584,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0585(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":585,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0586(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":586,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0587(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":587,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0588(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":588,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0589(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":589,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0590(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":590,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0591(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":591,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0592(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":592,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0593(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":593,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0594(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":594,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0595(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":595,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0596(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":596,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0597(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":597,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0598(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":598,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0599(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":599,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0600(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":600,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0601(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":601,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0602(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":602,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0603(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":603,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0604(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":604,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0605(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":605,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0606(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":606,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0607(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":607,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0608(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":608,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0609(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":609,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0610(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":610,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0611(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":611,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0612(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":612,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0613(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":613,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0614(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":614,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0615(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":615,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0616(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":616,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0617(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":617,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0618(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":618,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0619(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":619,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0620(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":620,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0621(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":621,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0622(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":622,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0623(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":623,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0624(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":624,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0625(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":625,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0626(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":626,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0627(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":627,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0628(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":628,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0629(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":629,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0630(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":630,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0631(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":631,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0632(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":632,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0633(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":633,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0634(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":634,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0635(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":635,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0636(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":636,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0637(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":637,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0638(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":638,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0639(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":639,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0640(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":640,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0641(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":641,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0642(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":642,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0643(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":643,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0644(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":644,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0645(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":645,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0646(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":646,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0647(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":647,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0648(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":648,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0649(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":649,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0650(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":650,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0651(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":651,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0652(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":652,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0653(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":653,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0654(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":654,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0655(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":655,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0656(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":656,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0657(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":657,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0658(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":658,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0659(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":659,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0660(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":660,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0661(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":661,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0662(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":662,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0663(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":663,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0664(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":664,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0665(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":665,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0666(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":666,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0667(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":667,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0668(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":668,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0669(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":669,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0670(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":670,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0671(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":671,"name":'Overhead Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0672(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":672,"name":'Glute Bridge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0673(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":673,"name":'Calf Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0674(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":674,"name":'Burpee',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0675(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":675,"name":'Mountain Climber',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0676(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":676,"name":'Jumping Jack',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0677(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":677,"name":'Running',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0678(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":678,"name":'Cycling',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0679(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":679,"name":'Walking',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0680(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":680,"name":'Jump Rope',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0681(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":681,"name":'Yoga',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0682(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":682,"name":'Mobility',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0683(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":683,"name":'Hip Thrust',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0684(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":684,"name":'Leg Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0685(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":685,"name":'Leg Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0686(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":686,"name":'Leg Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0687(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":687,"name":'Lateral Raise',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0688(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":688,"name":'Biceps Curl',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0689(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":689,"name":'Triceps Extension',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0690(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":690,"name":'Farmer Carry',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0691(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":691,"name":'Push Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0692(weight=70,minutes=30,intensity="Moderate"):
    met=6.60
    return {"id":692,"name":'Squat',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0693(weight=70,minutes=30,intensity="Moderate"):
    met=3.00
    return {"id":693,"name":'Lunge',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0694(weight=70,minutes=30,intensity="Moderate"):
    met=3.45
    return {"id":694,"name":'Plank',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0695(weight=70,minutes=30,intensity="Moderate"):
    met=3.90
    return {"id":695,"name":'Pull Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0696(weight=70,minutes=30,intensity="Moderate"):
    met=4.35
    return {"id":696,"name":'Chin Up',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0697(weight=70,minutes=30,intensity="Moderate"):
    met=4.80
    return {"id":697,"name":'Dip',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0698(weight=70,minutes=30,intensity="Moderate"):
    met=5.25
    return {"id":698,"name":'Row',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0699(weight=70,minutes=30,intensity="Moderate"):
    met=5.70
    return {"id":699,"name":'Deadlift',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def exercise_0700(weight=70,minutes=30,intensity="Moderate"):
    met=6.15
    return {"id":700,"name":'Bench Press',"minutes":uint(minutes),"intensity":intensity,"met":met,"calories":workout_calories(weight,minutes,met)}

def calendar_item_0001(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0002(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0003(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0004(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0005(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0006(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0007(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0008(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0009(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0010(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0011(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0012(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0013(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0014(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0015(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0016(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0017(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0018(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0019(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0020(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0021(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0022(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0023(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0024(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0025(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0026(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0027(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0028(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0029(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0030(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0031(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0032(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0033(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0034(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0035(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0036(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0037(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0038(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0039(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0040(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0041(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0042(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0043(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0044(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0045(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0046(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0047(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0048(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0049(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0050(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0051(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0052(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0053(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0054(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0055(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0056(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0057(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0058(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0059(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0060(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0061(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0062(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0063(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0064(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0065(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0066(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0067(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0068(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0069(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0070(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0071(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0072(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0073(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0074(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0075(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0076(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0077(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0078(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0079(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0080(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0081(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0082(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0083(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0084(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0085(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0086(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0087(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0088(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0089(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0090(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0091(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0092(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0093(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0094(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0095(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0096(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0097(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0098(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0099(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0100(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0101(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0102(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0103(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0104(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0105(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0106(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0107(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0108(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0109(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0110(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0111(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0112(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0113(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0114(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0115(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0116(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0117(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0118(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0119(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0120(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0121(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0122(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0123(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0124(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0125(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0126(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0127(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0128(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0129(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0130(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0131(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0132(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0133(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0134(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0135(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0136(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0137(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0138(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0139(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0140(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0141(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0142(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0143(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0144(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0145(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0146(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0147(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0148(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0149(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0150(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0151(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0152(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0153(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0154(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0155(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0156(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0157(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0158(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0159(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0160(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0161(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0162(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0163(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0164(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0165(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0166(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0167(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0168(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0169(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0170(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0171(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0172(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0173(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0174(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0175(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0176(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0177(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0178(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0179(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0180(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0181(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0182(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0183(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0184(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0185(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0186(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0187(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0188(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0189(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0190(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0191(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0192(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0193(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0194(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0195(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0196(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0197(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0198(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0199(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0200(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0201(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0202(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0203(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0204(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0205(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0206(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0207(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0208(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0209(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0210(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0211(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0212(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0213(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0214(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0215(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0216(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0217(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0218(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0219(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0220(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0221(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0222(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0223(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0224(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0225(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0226(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0227(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0228(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0229(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0230(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0231(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0232(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0233(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0234(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0235(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0236(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0237(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0238(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0239(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0240(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0241(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0242(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0243(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0244(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0245(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0246(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0247(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0248(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0249(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0250(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0251(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0252(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0253(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0254(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0255(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0256(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0257(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0258(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0259(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0260(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0261(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0262(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0263(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0264(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0265(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0266(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0267(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0268(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0269(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0270(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0271(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0272(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0273(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0274(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0275(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0276(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0277(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0278(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0279(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0280(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0281(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0282(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0283(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0284(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0285(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0286(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0287(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0288(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0289(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0290(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0291(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0292(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0293(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0294(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0295(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0296(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0297(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0298(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0299(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0300(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0301(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0302(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0303(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0304(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0305(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0306(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0307(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0308(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0309(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0310(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0311(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0312(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0313(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0314(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0315(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0316(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0317(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0318(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0319(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0320(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0321(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0322(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0323(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0324(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0325(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0326(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0327(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0328(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0329(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0330(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0331(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0332(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0333(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0334(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0335(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0336(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0337(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0338(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0339(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0340(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0341(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0342(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0343(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0344(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0345(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0346(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0347(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0348(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0349(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0350(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0351(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0352(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0353(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0354(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0355(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0356(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0357(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0358(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0359(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0360(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0361(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0362(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0363(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0364(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0365(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0366(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0367(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0368(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0369(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0370(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0371(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0372(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0373(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0374(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0375(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0376(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0377(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0378(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0379(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0380(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0381(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0382(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0383(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0384(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0385(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0386(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0387(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0388(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0389(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0390(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0391(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0392(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0393(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0394(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0395(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0396(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0397(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0398(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0399(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0400(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0401(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0402(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0403(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0404(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0405(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0406(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0407(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0408(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0409(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0410(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0411(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0412(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0413(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0414(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0415(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0416(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0417(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0418(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0419(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0420(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0421(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0422(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0423(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0424(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0425(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0426(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0427(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0428(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0429(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0430(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0431(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0432(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0433(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0434(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0435(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0436(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0437(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0438(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0439(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0440(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0441(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0442(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0443(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0444(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0445(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0446(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0447(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0448(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0449(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0450(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0451(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0452(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0453(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0454(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0455(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0456(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0457(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0458(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0459(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0460(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0461(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0462(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0463(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0464(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0465(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0466(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0467(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0468(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0469(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0470(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0471(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0472(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0473(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0474(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0475(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0476(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0477(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0478(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0479(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0480(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0481(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0482(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0483(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0484(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0485(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0486(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0487(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0488(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0489(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0490(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0491(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0492(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0493(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0494(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0495(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0496(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0497(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0498(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0499(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0500(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0501(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0502(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0503(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0504(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0505(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0506(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0507(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0508(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0509(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0510(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0511(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0512(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0513(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0514(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0515(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0516(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0517(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0518(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0519(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0520(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0521(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0522(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0523(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0524(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0525(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0526(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0527(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0528(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0529(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0530(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0531(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0532(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0533(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0534(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0535(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0536(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0537(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0538(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0539(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0540(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0541(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0542(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0543(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0544(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0545(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0546(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0547(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0548(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0549(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0550(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0551(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0552(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0553(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0554(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0555(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0556(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0557(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0558(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0559(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0560(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0561(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0562(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0563(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0564(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0565(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0566(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0567(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0568(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0569(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0570(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0571(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0572(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0573(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0574(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0575(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0576(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0577(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0578(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0579(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0580(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0581(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0582(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0583(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0584(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0585(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0586(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0587(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0588(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0589(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0590(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0591(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0592(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0593(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0594(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0595(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0596(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0597(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0598(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0599(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0600(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0601(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0602(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0603(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0604(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0605(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0606(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0607(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0608(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0609(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0610(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0611(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0612(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0613(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0614(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0615(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0616(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0617(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0618(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0619(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0620(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0621(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0622(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0623(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0624(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0625(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0626(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0627(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0628(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0629(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0630(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0631(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0632(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0633(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0634(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0635(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0636(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0637(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0638(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0639(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0640(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0641(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0642(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0643(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0644(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0645(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0646(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0647(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0648(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0649(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0650(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0651(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0652(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0653(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0654(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0655(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0656(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0657(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0658(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0659(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0660(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0661(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0662(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0663(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0664(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0665(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0666(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0667(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0668(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0669(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0670(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0671(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0672(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0673(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0674(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0675(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0676(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0677(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0678(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0679(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0680(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0681(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0682(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0683(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0684(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0685(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0686(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0687(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0688(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0689(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0690(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0691(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0692(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0693(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0694(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

def calendar_item_0695(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Reminder',title,notes)

def calendar_item_0696(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Meal',title,notes)

def calendar_item_0697(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Workout',title,notes)

def calendar_item_0698(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Water',title,notes)

def calendar_item_0699(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Measurement',title,notes)

def calendar_item_0700(day=None,time="08:00",title="Scheduled item",notes=""):
    return event(day or date.today(),time,'Check-in',title,notes)

# NAVIGATION
# ------------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>🥗 NutriCoach</h1>
    <p>Your food, workouts, body progress and daily coaching — in one simple place.</p>
</div>
""", unsafe_allow_html=True)

nav = st.radio(
    "",
    ["🏠 Today", "🍽️ Food", "🏋️ Workout", "📅 Calendar", "📊 Progress", "👤 Profile"],
    horizontal=True,
    label_visibility="collapsed"
)

# ============================================================
# HOME / TODAY
# ============================================================
if nav == "🏠 Today":
    name = profile.get("name", "") or "there"
    st.subheader(f"Good day, {name} 👋")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔥 Calories", f"{totals['Calories']:.0f} / {targets['Calories']:.0f}")
    m2.metric("💪 Protein", f"{totals['Protein']:.0f} / {targets['Protein']:.0f} g")
    m3.metric("🥑 Fiber", f"{totals['Fiber']:.0f} / {targets['Fiber']:.0f} g")
    m4.metric("💧 Water", f"{water:.1f} / {targets['Water']:.1f} L")

    st.markdown(f"""
    <div class="coach">
        <div class="coach-title">🧠 Your next best action</div>
        {coach_message()}
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.25, 1])

    with left:
        st.subheader("🎯 Today's targets")
        for label, current, target in [
            ("Calories", totals["Calories"], targets["Calories"]),
            ("Protein", totals["Protein"], targets["Protein"]),
            ("Carbs", totals["Carbs"], targets["Carbs"]),
            ("Fat", totals["Fat"], targets["Fat"]),
            ("Fiber", totals["Fiber"], targets["Fiber"]),
        ]:
            st.write(f"**{label}** — {current:.0f} / {target:.0f}")
            st.progress(min(current / target, 1.0) if target else 0)

    with right:
        st.subheader("👤 Your profile")
        st.markdown(
            f'<span class="pill">{profile["body_type"]}</span>'
            f'<span class="pill">{profile["goal"]}</span>'
            f'<span class="pill">{profile["diet"]}</span>',
            unsafe_allow_html=True
        )
        st.write(
            f"**{profile['weight']:.1f} kg** • {profile['height']:.0f} cm • "
            f"BMI {targets['BMI']:.1f}"
        )
        st.write(f"Target: **{targets['Calories']:.0f} kcal/day**")
        st.caption("Open Profile to update your numbers.")

    st.subheader("💧 Water")
    wc1, wc2, wc3 = st.columns([1, 1, 2])
    with wc1:
        if st.button("➕ 250 ml", use_container_width=True):
            water = min(water + 0.25, 10)
            set_water(water)
            st.rerun()
    with wc2:
        if st.button("➖ 250 ml", use_container_width=True):
            water = max(water - 0.25, 0)
            set_water(water)
            st.rerun()
    with wc3:
        st.progress(min(water / targets["Water"], 1.0))
        st.caption(f"{max(targets['Water'] - water, 0):.1f} L approximately remaining")

    st.subheader("🏋️ Automatic workout")
    st.markdown(
        f"**{workout['name']}** • {workout['minutes']} min • "
        f"{workout['intensity']} • ~{workout['calories']:.0f} kcal"
    )
    st.write(" → ".join(workout["blocks"]))

    if today_workout() and today_workout()[1]:
        st.success("Workout completed today ✅")
    elif st.button("✅ Mark today's workout complete", type="primary"):
        con = db()
        con.execute(
            "INSERT INTO workouts(day,name,minutes,intensity,calories,completed,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (TODAY, workout["name"], workout["minutes"], workout["intensity"],
             workout["calories"], 1, datetime.now().isoformat(timespec="seconds"))
        )
        con.commit()
        con.close()
        st.success("Workout saved.")
        st.rerun()

    st.subheader("🍽️ Recent food")
    foods = get_today_food()
    if not foods:
        st.info("Nothing logged today. Open Food and search what you ate.")
    else:
        for item in foods[:5]:
            st.markdown(
                f'<div class="food-card"><b>{item["food"]}</b> · {item["meal"]}'
                f'<br><span class="small">{item["quantity"]:.0f} g · '
                f'{item["calories"]:.0f} kcal · P {item["protein"]:.1f} g</span></div>',
                unsafe_allow_html=True
            )

# ============================================================
# FOOD — EVERYTHING MERGED HERE
# ============================================================
elif nav == "🍽️ Food":
    st.header("🍽️ Food")
    st.caption("Search food → choose serving → see the impact → add it to today.")

    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("Calories left", f"{remaining['Calories']:.0f}")
    t2.metric("Protein left", f"{remaining['Protein']:.0f} g")
    t3.metric("Carbs left", f"{remaining['Carbs']:.0f} g")
    t4.metric("Fat left", f"{remaining['Fat']:.0f} g")
    t5.metric("Fiber left", f"{remaining['Fiber']:.0f} g")

    st.divider()

    # Search
    q1, q2 = st.columns([4, 1])
    with q1:
        food_query = st.text_input(
            "🔎 Search food",
            placeholder="egg, rice, chicken, paneer, dal, banana..."
        )
    with q2:
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    if search_clicked:
        if not food_query.strip():
            st.warning("Type a food first.")
        else:
            foods, error = search_usda(food_query.strip())
            if error:
                st.error(error)
            else:
                st.session_state.search_results = foods
                st.session_state.last_search = food_query.strip()

    foods = st.session_state.get("search_results", [])

    if foods:
        labels = [
            f"{f.get('description','Unknown')} · {f.get('dataType','')}"
            for f in foods
        ]
        idx = st.selectbox(
            "Choose the closest USDA food",
            range(len(labels)),
            format_func=lambda x: labels[x]
        )
        selected = foods[idx]
        base = food_nutrients(selected)

        q1, q2, q3 = st.columns(3)
        with q1:
            meal = st.selectbox("Meal", MEALS)
        with q2:
            quantity_type = st.selectbox("Serving", ["Grams", "Pieces"])
        with q3:
            if quantity_type == "Grams":
                quantity = st.number_input("Amount", 1.0, 5000.0, 100.0, 1.0)
            else:
                quantity = st.number_input("Pieces", 1, 100, 1, 1)

        if quantity_type == "Pieces":
            grams = quantity * piece_weight(
                st.session_state.get("last_search", ""),
                selected.get("description", "")
            )
            st.caption(f"Piece estimate: approximately **{grams:.0f} g**.")
        else:
            grams = quantity

        mult = grams / 100
        result = {
            "Food": selected.get("description", "Unknown"),
            "Meal": meal,
            "Diet": profile["diet"],
            "Quantity": grams,
        }
        for k, v in base.items():
            result[k] = v * mult

        st.subheader("🥗 Nutrition for this serving")
        n1, n2, n3, n4, n5 = st.columns(5)
        n1.metric("Calories", f"{result['Calories']:.0f} kcal")
        n2.metric("Protein", f"{result['Protein']:.1f} g")
        n3.metric("Carbs", f"{result['Carbs']:.1f} g")
        n4.metric("Fat", f"{result['Fat']:.1f} g")
        n5.metric("Fiber", f"{result['Fiber']:.1f} g")

        st.subheader("⚡ What this does to today's targets")
        impact = {
            "Calories": result["Calories"],
            "Protein": result["Protein"],
            "Carbs": result["Carbs"],
            "Fat": result["Fat"],
            "Fiber": result["Fiber"],
        }
        cols = st.columns(5)
        for col, key in zip(cols, impact):
            left_after = max(remaining[key] - impact[key], 0)
            col.metric(key, f"{left_after:.0f} left")

        st.caption("USDA values and piece conversions are estimates for the selected record.")

        if st.button("➕ Add to today's food log", type="primary"):
            add_food(result)
            st.success(f"Added {result['Food']} to today's log.")
            st.rerun()

    # Personal calculator
    st.divider()
    st.subheader("🧮 Personal food calculator")
    st.caption("Use this when you ate something outside your planned diet.")

    c1, c2, c3 = st.columns(3)
    with c1:
        custom_food = st.text_input("Food name", placeholder="Homemade paneer roll")
        custom_meal = st.selectbox("Meal", MEALS, key="custom_meal")
    with c2:
        custom_cal = st.number_input("Calories", 0.0, 5000.0, 0.0, 10.0)
        custom_protein = st.number_input("Protein (g)", 0.0, 300.0, 0.0, 1.0)
    with c3:
        custom_carbs = st.number_input("Carbs (g)", 0.0, 500.0, 0.0, 1.0)
        custom_fat = st.number_input("Fat (g)", 0.0, 300.0, 0.0, 1.0)
    custom_fiber = st.number_input("Fiber (g)", 0.0, 100.0, 0.0, 1.0)
    custom_qty = st.number_input("Amount (g)", 1.0, 5000.0, 100.0, 1.0)

    if st.button("➕ Add custom food"):
        if not custom_food.strip():
            st.warning("Enter a food name.")
        else:
            add_food({
                "Food": custom_food.strip(), "Meal": custom_meal, "Diet": profile["diet"],
                "Quantity": custom_qty, "Calories": custom_cal, "Protein": custom_protein,
                "Carbs": custom_carbs, "Fat": custom_fat, "Fiber": custom_fiber,
                "Vitamin A": 0, "Vitamin C": 0, "Vitamin D": 0, "Vitamin E": 0, "Vitamin K": 0,
                "Calcium": 0, "Iron": 0, "Magnesium": 0, "Potassium": 0, "Zinc": 0
            })
            st.success("Custom food added.")
            st.rerun()

    # 14-day diet
    st.divider()
    st.subheader("🍱 Your 14-day diet")
    d1, d2 = st.columns([1, 1])
    with d1:
        if st.button("🔄 Generate new 14 days", use_container_width=True):
            st.session_state.diet_cycle += 1
            st.session_state.diet_plan = generate_plan(st.session_state.diet_cycle)
            st.rerun()
    with d2:
        if st.button("🔁 New cycle / different meals", use_container_width=True):
            st.session_state.diet_cycle += 1
            st.session_state.diet_plan = generate_plan(st.session_state.diet_cycle + 2)
            st.rerun()

    for day in st.session_state.diet_plan:
        with st.expander(f"Day {day['day']} · {day['date']}"):
            a, b = st.columns(2)
            with a:
                st.write(f"**🍳 Breakfast:** {day['Breakfast']}")
                st.write(f"**🍛 Lunch:** {day['Lunch']}")
            with b:
                st.write(f"**🥜 Snack:** {day['Snack']}")
                st.write(f"**🌙 Dinner:** {day['Dinner']}")
            if st.button(f"🔄 Swap meals for Day {day['day']}", key=f"swap_{day['day']}"):
                idx = day["day"] - 1
                old = st.session_state.diet_plan[idx]
                st.session_state.diet_plan[idx] = {
                    **old,
                    "Dinner": old["Lunch"],
                    "Lunch": old["Dinner"],
                }
                st.rerun()

    # Meal tracking
    st.divider()
    st.subheader("☑️ Meal tracking")
    for meal_name in MEALS:
        done = st.checkbox(
            f"{meal_name} completed",
            value=meal_done(meal_name),
            key=f"done_{meal_name}"
        )
        set_meal_done(meal_name, done)

    # Supplements
    st.subheader("💊 Supplements")
    supplements = st.multiselect(
        "Track what you use",
        ["Protein powder", "Peanut butter", "Creatine", "Multivitamin", "Omega-3", "Electrolytes"],
        default=st.session_state.get("supplements", [])
    )
    st.session_state.supplements = supplements
    if supplements:
        st.caption("Today: " + " · ".join(supplements))

    # Today's log
    st.divider()
    st.subheader("📋 Today's food log")
    foods_today = get_today_food()
    if not foods_today:
        st.info("No food logged today.")
    else:
        for item in foods_today:
            with st.container(border=True):
                a, b, c = st.columns([3, 1, 1])
                a.write(f"**{item['food']}** · {item['meal']}")
                a.caption(f"{item['quantity']:.0f} g")
                b.write(f"🔥 {item['calories']:.0f} kcal")
                b.write(f"💪 P {item['protein']:.1f} g")
                c.write(f"🥑 F {item['fat']:.1f} g")
                if c.button("Remove", key=f"rm_{item['id']}"):
                    remove_food(item["id"])
                    st.rerun()

    # Micronutrients
    st.subheader("🧂 Micronutrients")
    a, b, c, d, e = st.columns(5)
    a.metric("Vit A", f"{totals['Vitamin A']:.0f} µg")
    b.metric("Vit C", f"{totals['Vitamin C']:.0f} mg")
    c.metric("Calcium", f"{totals['Calcium']:.0f} mg")
    d.metric("Iron", f"{totals['Iron']:.1f} mg")
    e.metric("Potassium", f"{totals['Potassium']:.0f} mg")

# ============================================================
# WORKOUT
# ============================================================
elif nav == "🏋️ Workout":
    st.header("🏋️ Workout")
    st.caption("No exercise selection needed — NutriCoach generates it from your profile.")

    st.markdown(f"""
    <div class="section-card">
        <h3>{workout['name']}</h3>
        <span class="pill">{workout['minutes']} min</span>
        <span class="pill">{workout['intensity']}</span>
        <span class="pill">~{workout['calories']:.0f} kcal</span>
    </div>
    """, unsafe_allow_html=True)

    for i, block in enumerate(workout["blocks"], 1):
        st.write(f"**{i}. {block}**")

    st.divider()
    st.subheader("⏱️ Workout timer")
    seconds = st.number_input("Timer minutes", 1, 180, workout["minutes"], 1)
    st.info(
        "Use your phone/laptop clock for the actual timer, then mark the workout "
        "complete below. This keeps the app responsive."
    )

    if today_workout() and today_workout()[1]:
        st.success("Today's workout is already saved as completed.")
    else:
        if st.button("✅ Complete & save workout", type="primary"):
            con = db()
            con.execute(
                "INSERT INTO workouts(day,name,minutes,intensity,calories,completed,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (TODAY, workout["name"], int(seconds), workout["intensity"],
                 workout["calories"], 1, datetime.now().isoformat(timespec="seconds"))
            )
            con.commit()
            con.close()
            st.success("Workout completed and saved.")
            st.rerun()

    st.subheader("📚 Workout history")
    con = db()
    rows = con.execute(
        "SELECT day,name,minutes,intensity,calories FROM workouts "
        "ORDER BY day DESC, id DESC LIMIT 30"
    ).fetchall()
    con.close()

    if rows:
        st.dataframe(
            [{"Date": r[0], "Workout": r[1], "Minutes": r[2],
              "Intensity": r[3], "Calories": round(r[4], 0)} for r in rows],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Complete your first workout to create history.")

# ============================================================
# CALENDAR — DATE + TIME
# ============================================================
elif nav == "📅 Calendar":
    st.header("📅 Calendar & Schedule")
    now = datetime.now()
    st.success(f"🕒 {now.strftime('%A, %d %B %Y · %I:%M:%S %p')}")
    a,b,c = st.columns(3)
    with a: selected_day = st.date_input("📆 Date", date.today(), key="ultra_calendar_date")
    with b: selected_time = st.time_input("⏰ Time", now.time().replace(microsecond=0), key="ultra_calendar_time")
    with c: event_type = st.selectbox("Event type", ["Meal","Workout","Water","Measurement","Check-in","Reminder"], key="ultra_event_type")
    selected_dt = datetime.combine(selected_day, selected_time)
    st.write(f"**Selected:** {selected_dt.strftime('%A, %d %B %Y at %I:%M %p')}")
    day_key=selected_day.isoformat()
    con=db()
    food_rows=con.execute("SELECT food,quantity,unit,calories,protein,created_at FROM food_log WHERE day=? ORDER BY created_at",(day_key,)).fetchall()
    workout_rows=con.execute("SELECT workout,minutes,intensity,calories,completed_at FROM workouts WHERE day=? ORDER BY completed_at",(day_key,)).fetchall()
    water_row=con.execute("SELECT glasses FROM water WHERE day=?",(day_key,)).fetchone()
    con.close()
    x,y,z=st.columns(3)
    x.metric("Calories",f"{sum(float(r[3] or 0) for r in food_rows):.0f} kcal")
    y.metric("Protein",f"{sum(float(r[4] or 0) for r in food_rows):.1f} g")
    z.metric("Water",f"{int(water_row[0]) if water_row else 0} glasses")
    st.subheader("🗓️ Month")
    import calendar as _calendar
    for week in _calendar.monthcalendar(selected_day.year,selected_day.month):
        cols=st.columns(7)
        for col,n in zip(cols,week):
            if not n: col.write(""); continue
            d=date(selected_day.year,selected_day.month,n)
            con=db();fc=con.execute("SELECT COUNT(*) FROM food_log WHERE day=?",(d.isoformat(),)).fetchone()[0];wc=con.execute("SELECT COUNT(*) FROM workouts WHERE day=?",(d.isoformat(),)).fetchone()[0];con.close()
            col.markdown(f"### {n} {'🟢' if fc or wc else '⚪'}" if d==selected_day else f"**{n}** {'🟢' if fc or wc else '⚪'}")
    if food_rows:
        st.subheader("🍽️ Food on selected date")
        st.dataframe([{"Time":r[5],"Food":r[0],"Quantity":f"{r[1]} {r[2]}","Calories":round(r[3] or 0),"Protein":round(r[4] or 0,1)} for r in food_rows],use_container_width=True,hide_index=True)
    if workout_rows:
        st.subheader("🏋️ Workouts on selected date")
        st.dataframe([{"Time":r[4],"Workout":r[0],"Minutes":r[1],"Intensity":r[2],"Calories":round(r[3] or 0)} for r in workout_rows],use_container_width=True,hide_index=True)
    st.caption("Calendar is persistent: saved food, water and workouts can be inspected by date.")

# ============================================================
# PROGRESS — MEASUREMENTS + CAMERA + CHARTS
# ============================================================
elif nav == "📊 Progress":
    st.header("📊 Body Progress")

    st.subheader("📏 Measurements")
    measurement_date = st.date_input("Date", value=date.today())

    a, b, c = st.columns(3)
    with a:
        w = st.number_input("Weight (kg)", 20.0, 300.0, float(profile["weight"]), .1)
        waist = st.number_input("Waist (cm)", 0.0, 250.0, 0.0, .1)
    with b:
        chest = st.number_input("Chest (cm)", 0.0, 250.0, 0.0, .1)
        arms = st.number_input("Arms (cm)", 0.0, 100.0, 0.0, .1)
    with c:
        legs = st.number_input("Legs / thigh (cm)", 0.0, 150.0, 0.0, .1)
        shoulders = st.number_input("Shoulders (cm)", 0.0, 200.0, 0.0, .1)

    st.subheader("📸 Body Scan")
    st.caption(
        "Front · side · back photos can be saved for visual comparison. "
        "Camera-only centimeter measurements are estimates and need calibration."
    )

    p1, p2, p3 = st.columns(3)
    with p1:
        front = st.camera_input("Front photo")
    with p2:
        side = st.camera_input("Side photo")
    with p3:
        back = st.camera_input("Back photo")

    os.makedirs("data/photos", exist_ok=True)

    def save_photo(upload, label):
        if not upload:
            return None
        filename = f"{TODAY}_{label}_{datetime.now().strftime('%H%M%S')}.jpg"
        path = os.path.join("data", "photos", filename)
        with open(path, "wb") as f:
            f.write(upload.getbuffer())
        return path

    if st.button("💾 Save measurements + photos", type="primary"):
        fp = save_photo(front, "front")
        sp = save_photo(side, "side")
        bp = save_photo(back, "back")

        con = db()
        con.execute("""
            INSERT INTO measurements(
                day,weight,waist,chest,arms,legs,shoulders,
                photo_front,photo_side,photo_back
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (
            str(measurement_date), w, waist, chest, arms, legs, shoulders,
            fp, sp, bp
        ))
        con.commit()
        con.close()

        # Keep profile weight synced with latest saved measurement.
        profile["weight"] = w
        save_profile(profile)
        st.session_state.profile = profile

        st.success("Progress saved.")
        st.rerun()

    con = db()
    rows = con.execute("""
        SELECT day,weight,waist,chest,arms,legs,shoulders,
               photo_front,photo_side,photo_back
        FROM measurements ORDER BY day ASC, id ASC
    """).fetchall()
    con.close()

    if rows:
        st.subheader("📈 Progress graphs")
        import pandas as pd

        df = pd.DataFrame(rows, columns=[
            "Date","Weight","Waist","Chest","Arms","Legs","Shoulders",
            "Front","Side","Back"
        ])
        df["Date"] = pd.to_datetime(df["Date"])

        chart_metric = st.selectbox(
            "Choose measurement",
            ["Weight", "Waist", "Chest", "Arms", "Legs", "Shoulders"]
        )
        chart_df = df[["Date", chart_metric]].dropna()
        if not chart_df.empty:
            chart_df = chart_df.set_index("Date")
            st.line_chart(chart_df)

        st.dataframe(
            df[["Date","Weight","Waist","Chest","Arms","Legs","Shoulders"]],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("🖼️ Saved progress photos")
        latest = rows[-1]
        pp1, pp2, pp3 = st.columns(3)
        with pp1:
            if latest[7] and os.path.exists(latest[7]):
                st.image(latest[7], caption="Latest Front")
        with pp2:
            if latest[8] and os.path.exists(latest[8]):
                st.image(latest[8], caption="Latest Side")
        with pp3:
            if latest[9] and os.path.exists(latest[9]):
                st.image(latest[9], caption="Latest Back")

        if waist and shoulders:
            st.metric(
                "Shoulder / waist proportion",
                f"{shoulders / waist:.2f}" if waist else "—"
            )

    else:
        st.info("Save your first measurement to start your progress history.")

# ============================================================
# PROFILE
# ============================================================
else:
    st.header("👤 Profile")
    st.caption("Home uses this profile to calculate your targets, food guidance and workout.")

    with st.form("profile_form"):
        a, b = st.columns(2)
        with a:
            name = st.text_input("Name", profile["name"])
            age = st.number_input("Age", 10, 100, int(profile["age"]))
            sex = st.selectbox("Sex", ["Male", "Female"], index=["Male","Female"].index(profile["sex"]))
            height = st.number_input("Height (cm)", 100.0, 250.0, float(profile["height"]), .1)
            weight = st.number_input("Weight (kg)", 20.0, 300.0, float(profile["weight"]), .1)
            activity = st.selectbox(
                "Activity",
                ["Sedentary","Lightly Active","Moderately Active","Very Active"],
                index=["Sedentary","Lightly Active","Moderately Active","Very Active"].index(profile["activity"])
            )
        with b:
            diet = st.selectbox(
                "Food preference",
                ["Vegetarian","Non-Vegetarian","Vegan"],
                index=["Vegetarian","Non-Vegetarian","Vegan"].index(profile["diet"])
            )
            budget = st.selectbox(
                "Food budget",
                ["Budget Friendly","Moderate","Premium"],
                index=["Budget Friendly","Moderate","Premium"].index(profile["budget"])
            )
            body_type = st.selectbox(
                "Current body type",
                ["Slim/Skinny","Skinny Fat","Average","Athletic","Muscular","Higher Body Fat"],
                index=["Slim/Skinny","Skinny Fat","Average","Athletic","Muscular","Higher Body Fat"].index(profile["body_type"])
            )
            goal = st.selectbox(
                "Body goal",
                ["General Fitness","Calisthenics","Greek Body","Aesthetic Body",
                 "Muscle Gain","Fat Loss","Strength","Recomposition"],
                index=["General Fitness","Calisthenics","Greek Body","Aesthetic Body",
                       "Muscle Gain","Fat Loss","Strength","Recomposition"].index(profile["goal"])
            )

        save = st.form_submit_button("💾 Save profile", type="primary")

    if save:
        profile = {
            "name": name, "age": age, "sex": sex, "height": height, "weight": weight,
            "activity": activity, "diet": diet, "budget": budget,
            "body_type": body_type, "goal": goal
        }
        save_profile(profile)
        st.session_state.profile = profile
        st.session_state.diet_plan = generate_plan(st.session_state.diet_cycle)
        st.success("Profile saved. Your targets and plan were recalculated.")
        st.rerun()

    st.divider()
    st.subheader("🎯 Your calculated targets")
    a, b, c, d = st.columns(4)
    a.metric("BMR", f"{targets['BMR']:.0f}")
    b.metric("TDEE", f"{targets['TDEE']:.0f}")
    c.metric("Calories", f"{targets['Calories']:.0f}")
    d.metric("Protein", f"{targets['Protein']:.0f} g")

    st.write(
        f"**Carbs:** {targets['Carbs']:.0f} g · "
        f"**Fat:** {targets['Fat']:.0f} g · "
        f"**Fiber:** {targets['Fiber']:.0f} g · "
        f"**Water:** {targets['Water']:.1f} L"
    )

    st.info(
        "These are estimates for general fitness planning, not medical prescriptions. "
        "The app should not be used to diagnose body type or health conditions."
    )

st.markdown(
    '<div class="footer">🥗 NutriCoach · Persistent local data · USDA-powered food search · Built for phone + laptop</div>',
    unsafe_allow_html=True
)


