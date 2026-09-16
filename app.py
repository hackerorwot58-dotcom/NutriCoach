import streamlit as st
import requests
import random
import time
import re
from datetime import date, datetime

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="NutriCoach",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(91, 196, 139, .12), transparent 28%),
        radial-gradient(circle at 90% 5%, rgba(96, 165, 250, .10), transparent 25%),
        #08110e;
    color: #f4f7f5;
}

.block-container {
    max-width: 1200px;
    padding-top: 1.2rem;
    padding-bottom: 5rem;
}

h1, h2, h3 {
    letter-spacing: -0.04em;
}

h1 {
    font-weight: 800;
}

h2 {
    font-weight: 750;
}

h3 {
    font-weight: 700;
}

.hero {
    padding: 28px;
    border-radius: 28px;
    background:
        linear-gradient(135deg, rgba(35, 75, 58, .95), rgba(12, 31, 25, .98));
    border: 1px solid rgba(150, 220, 185, .15);
    box-shadow: 0 20px 60px rgba(0,0,0,.25);
    margin-bottom: 20px;
}

.hero-title {
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 4px;
}

.hero-sub {
    color: #b8cbc1;
    font-size: 15px;
}

.card {
    background: rgba(18, 30, 25, .88);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 22px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 12px 40px rgba(0,0,0,.16);
}

.small-card {
    background: rgba(18, 30, 25, .78);
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 18px;
    padding: 16px;
    min-height: 110px;
}

.card-title {
    font-size: 17px;
    font-weight: 750;
    margin-bottom: 8px;
}

.muted {
    color: #91a59b;
}

.big-number {
    font-size: 30px;
    font-weight: 800;
}

.green {
    color: #69df9c;
}

.blue {
    color: #74b9ff;
}

.orange {
    color: #ffbd70;
}

.purple {
    color: #c6a4ff;
}

.progress-track {
    height: 10px;
    width: 100%;
    border-radius: 99px;
    background: #18251f;
    overflow: hidden;
    margin-top: 8px;
}

.progress-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #56d58e, #a3f2bd);
}

.ring {
    width: 150px;
    height: 150px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: auto;
    background: conic-gradient(#69df9c var(--progress), #1a2822 0);
    position: relative;
}

.ring::after {
    content: "";
    width: 118px;
    height: 118px;
    background: #101c17;
    border-radius: 50%;
    position: absolute;
}

.ring-content {
    position: relative;
    z-index: 2;
    text-align: center;
}

.ring-number {
    font-size: 27px;
    font-weight: 800;
}

.ring-label {
    font-size: 11px;
    color: #91a59b;
}

.coach {
    background:
        linear-gradient(135deg, rgba(42, 78, 62, .95), rgba(20, 35, 29, .96));
    border: 1px solid rgba(105,223,156,.22);
    border-radius: 24px;
    padding: 23px;
    box-shadow: 0 15px 50px rgba(0,0,0,.2);
}

.coach-title {
    font-size: 20px;
    font-weight: 800;
}

.coach-action {
    font-size: 24px;
    font-weight: 800;
    margin: 10px 0;
}

.chip {
    display: inline-block;
    padding: 6px 11px;
    border-radius: 99px;
    background: rgba(255,255,255,.07);
    color: #c9d7d0;
    font-size: 12px;
    margin: 2px;
}

.meal {
    background: #111e18;
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 18px;
    padding: 17px;
    margin-bottom: 10px;
}

.meal-name {
    font-weight: 750;
    font-size: 16px;
}

.meal-food {
    color: #a8bbb1;
    font-size: 13px;
    margin-top: 5px;
}

.nav-spacer {
    height: 4px;
}

div[data-testid="stButton"] > button {
    border-radius: 13px;
    border: 1px solid rgba(255,255,255,.08);
    background: #14221c;
    color: #edf5f0;
    font-weight: 650;
    min-height: 42px;
    transition: .2s ease;
}

div[data-testid="stButton"] > button:hover {
    border-color: rgba(105,223,156,.45);
    background: #1a2d24;
    transform: translateY(-1px);
}

div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #42c97e, #6de39c);
    color: #06110b;
    border: none;
}

.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"],
.stTextArea textarea {
    background: #111e18 !important;
    border-color: rgba(255,255,255,.08) !important;
    color: white !important;
    border-radius: 12px !important;
}

div[data-testid="stMetric"] {
    background: #111e18;
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 18px;
    padding: 14px;
}

hr {
    border-color: rgba(255,255,255,.08);
}

[data-testid="stTabs"] button {
    font-weight: 650;
}

@media (max-width: 700px) {
    .block-container {
        padding: .8rem .7rem 5rem;
    }

    .hero {
        padding: 20px;
        border-radius: 22px;
    }

    .hero-title {
        font-size: 28px;
    }

    .card {
        padding: 16px;
        border-radius: 18px;
    }

    .ring {
        width: 125px;
        height: 125px;
    }

    .ring::after {
        width: 98px;
        height: 98px;
    }
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# STATE
# =========================================================

TODAY = date.today().isoformat()

DEFAULT_PROFILE = {
    "age": 22,
    "sex": "Male",
    "height": 170.0,
    "weight": 65.0,
    "activity": "Moderately Active",
    "diet": "Vegetarian",
    "budget": "Medium",
    "body_type": "Average",
    "goal": "General Fitness",
}

if "profile" not in st.session_state:
    st.session_state.profile = DEFAULT_PROFILE.copy()

if "targets" not in st.session_state:
    st.session_state.targets = {}

if "food_log" not in st.session_state:
    st.session_state.food_log = []

if "water" not in st.session_state:
    st.session_state.water = 0

if "weight_history" not in st.session_state:
    st.session_state.weight_history = []

if "waist_history" not in st.session_state:
    st.session_state.waist_history = []

if "body_history" not in st.session_state:
    st.session_state.body_history = []

if "workout_history" not in st.session_state:
    st.session_state.workout_history = []

if "meal_status" not in st.session_state:
    st.session_state.meal_status = {}

if "meal_timers" not in st.session_state:
    st.session_state.meal_timers = {}

if "supplements" not in st.session_state:
    st.session_state.supplements = {}

if "diet_plan" not in st.session_state:
    st.session_state.diet_plan = None

if "diet_cycle" not in st.session_state:
    st.session_state.diet_cycle = 1

if "photos" not in st.session_state:
    st.session_state.photos = []

if "page" not in st.session_state:
    st.session_state.page = "Today"

if "food_search" not in st.session_state:
    st.session_state.food_search = ""

# =========================================================
# DAILY RESET
# =========================================================

if "state_date" not in st.session_state:
    st.session_state.state_date = TODAY

if st.session_state.state_date != TODAY:
    st.session_state.state_date = TODAY
    st.session_state.food_log = []
    st.session_state.water = 0
    st.session_state.meal_status = {}
    st.session_state.meal_timers = {}
    st.session_state.supplements = {}

# =========================================================
# CALCULATOR
# =========================================================

def calculate_targets(profile):
    age = float(profile["age"])
    weight = float(profile["weight"])
    height = float(profile["height"])
    sex = profile["sex"]

    if sex == "Male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    activity = {
        "Sedentary": 1.20,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
    }

    tdee = bmr * activity.get(profile["activity"], 1.55)

    adjustments = {
        "Fat Loss": -400,
        "Muscle Gain": 250,
        "Strength": 250,
        "Recomposition": -150,
        "Calisthenics": 100,
        "Greek Body": -100,
        "Aesthetic Body": -100,
        "General Fitness": 0,
    }

    calories = tdee + adjustments.get(profile["goal"], 0)

    # Avoid presenting an aggressively low target.
    calories = max(calories, 1500 if sex == "Male" else 1300)

    if profile["goal"] in ["Muscle Gain", "Strength", "Calisthenics"]:
        protein = weight * 1.8
    elif profile["goal"] in [
        "Fat Loss",
        "Recomposition",
        "Aesthetic Body",
        "Greek Body",
    ]:
        protein = weight * 1.7
    else:
        protein = weight * 1.6

    fat = weight * 0.8
    fiber = calories / 1000 * 14
    water_ml = weight * 35

    protein_calories = protein * 4
    fat_calories = fat * 9

    carbs = max((calories - protein_calories - fat_calories) / 4, 0)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": round(calories),
        "protein": round(protein),
        "carbs": round(carbs),
        "fat": round(fat),
        "fiber": round(fiber),
        "water_ml": round(water_ml),
        "water_glasses": max(1, round(water_ml / 250)),
    }


st.session_state.targets = calculate_targets(st.session_state.profile)

# =========================================================
# HELPERS
# =========================================================

def total_nutrition():
    totals = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "fiber": 0,
        "vitamin_a": 0,
        "vitamin_c": 0,
        "calcium": 0,
        "iron": 0,
        "magnesium": 0,
        "potassium": 0,
    }

    for item in st.session_state.food_log:
        for key in totals:
            totals[key] += float(item.get(key, 0) or 0)

    return totals


def remaining_targets():
    totals = total_nutrition()
    targets = st.session_state.targets

    return {
        "calories": max(targets["calories"] - totals["calories"], 0),
        "protein": max(targets["protein"] - totals["protein"], 0),
        "carbs": max(targets["carbs"] - totals["carbs"], 0),
        "fat": max(targets["fat"] - totals["fat"], 0),
        "fiber": max(targets["fiber"] - totals["fiber"], 0),
    }


def progress_percent(value, target):
    if target <= 0:
        return 0
    return min(value / target * 100, 100)


def progress_bar(value, target):
    pct = progress_percent(value, target)

    st.markdown(
        f"""
        <div class="progress-track">
            <div class="progress-fill" style="width:{pct}%"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def nutrition_dict_from_usda(food, grams):
    nutrients = {}

    for nutrient in food.get("foodNutrients", []):
        name = nutrient.get("nutrientName", "")
        value = nutrient.get("value", 0) or 0
        nutrients[name] = value

    multiplier = grams / 100

    def get(*names):
        for name in names:
            if name in nutrients:
                return float(nutrients[name]) * multiplier
        return 0

    return {
        "calories": get("Energy"),
        "protein": get("Protein"),
        "carbs": get("Carbohydrate, by difference"),
        "fat": get("Total lipid (fat)"),
        "fiber": get("Fiber, total dietary"),
        "vitamin_a": get("Vitamin A, RAE"),
        "vitamin_c": get("Vitamin C, total ascorbic acid"),
        "calcium": get("Calcium, Ca"),
        "iron": get("Iron, Fe"),
        "magnesium": get("Magnesium, Mg"),
        "potassium": get("Potassium, K"),
    }


def estimate_piece_weight(food_name):
    name = food_name.lower()

    pieces = {
        "egg": 50,
        "banana": 118,
        "apple": 182,
        "orange": 130,
        "roti": 40,
        "chapati": 40,
        "bread": 28,
        "slice": 28,
    }

    for keyword, weight in pieces.items():
        if keyword in name:
            return weight

    return 100


def search_usda(query):
    try:
        api_key = st.secrets["FDC_API_KEY"]
    except Exception:
        return None, "USDA API key not found."

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {
        "api_key": api_key,
        "query": query,
        "pageSize": 8,
    }

    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None, f"USDA request failed: {response.status_code}"

        data = response.json()
        return data.get("foods", []), None

    except Exception as e:
        return None, str(e)


def make_food_item(food, grams):
    nutrition = nutrition_dict_from_usda(food, grams)

    return {
        "name": food.get("description", "Unknown food"),
        "grams": grams,
        "fdc_id": food.get("fdcId"),
        **nutrition,
    }


# =========================================================
# DIET PLAN
# =========================================================

BREAKFASTS = [
    "Oats + milk/soy milk + banana + peanut butter",
    "Vegetable poha + curd",
    "Paneer/tofu sandwich + fruit",
    "Besan chilla + curd",
    "Idli + sambar + fruit",
    "Vegetable upma + curd",
    "Overnight oats + banana + seeds",
    "Moong dal chilla + chutney",
]

LUNCHES = [
    "Dal + rice + salad + curd",
    "Rajma + rice + cucumber salad",
    "Chole + 2 rotis + salad",
    "Paneer/tofu + 2 rotis + vegetables",
    "Dal khichdi + curd + salad",
    "Soy chunks curry + rice + vegetables",
    "Mixed dal + roti + seasonal vegetables",
    "Chana pulao + raita",
]

SNACKS = [
    "Roasted chana + fruit",
    "Curd + banana",
    "Peanut butter toast",
    "Fruit + handful of nuts",
    "Sprouts chaat",
    "Protein shake + fruit",
    "Buttermilk + roasted chana",
    "Peanuts + fruit",
]

DINNERS = [
    "Paneer/tofu bhurji + roti + vegetables",
    "Dal + roti + salad",
    "Soy chunks + rice + vegetables",
    "Chole + roti + salad",
    "Vegetable khichdi + curd",
    "Paneer/tofu curry + roti",
    "Dal + rice + mixed vegetables",
    "Moong dal chilla + curd",
]

NONVEG_ADDONS = [
    "2 eggs",
    "3 eggs",
    "Chicken breast",
    "Fish",
    "Egg bhurji",
]

VEGAN_REPLACEMENTS = {
    "milk": "soy milk",
    "curd": "soy yogurt",
    "paneer": "tofu",
    "raita": "soy yogurt",
}


def adapt_meal(meal, diet):
    result = meal

    if diet == "Vegan":
        for old, new in VEGAN_REPLACEMENTS.items():
            result = re.sub(old, new, result, flags=re.IGNORECASE)

    if diet == "Non-Vegetarian":
        if random.random() < 0.45:
            result += " + " + random.choice(NONVEG_ADDONS)

    return result


def generate_diet_plan(cycle=1):
    seed = cycle * 100 + int(st.session_state.profile["age"])
    rng = random.Random(seed)

    breakfasts = BREAKFASTS.copy()
    lunches = LUNCHES.copy()
    snacks = SNACKS.copy()
    dinners = DINNERS.copy()

    rng.shuffle(breakfasts)
    rng.shuffle(lunches)
    rng.shuffle(snacks)
    rng.shuffle(dinners)

    plan = []

    for day_num in range(1, 15):
        breakfast = adapt_meal(
            breakfasts[(day_num - 1) % len(breakfasts)],
            st.session_state.profile["diet"],
        )
        lunch = adapt_meal(
            lunches[(day_num + cycle) % len(lunches)],
            st.session_state.profile["diet"],
        )
        snack = adapt_meal(
            snacks[(day_num + cycle * 2) % len(snacks)],
            st.session_state.profile["diet"],
        )
        dinner = adapt_meal(
            dinners[(day_num + cycle * 3) % len(dinners)],
            st.session_state.profile["diet"],
        )

        plan.append({
            "day": day_num,
            "breakfast": breakfast,
            "lunch": lunch,
            "snack": snack,
            "dinner": dinner,
        })

    return plan


if st.session_state.diet_plan is None:
    st.session_state.diet_plan = generate_diet_plan(
        st.session_state.diet_cycle
    )

# =========================================================
# SMART COACH
# =========================================================

def coach_message():
    totals = total_nutrition()
    remain = remaining_targets()
    target = st.session_state.targets
    profile = st.session_state.profile

    protein_gap = remain["protein"]
    calorie_gap = remain["calories"]

    if protein_gap > 35:
        if profile["diet"] == "Vegan":
            action = "80g soy chunks + rice + vegetables"
            option = "Vegan option"
        elif profile["diet"] == "Vegetarian":
            action = "200g curd + 100g roasted chana + 2 rotis"
            option = "Vegetarian option"
        else:
            action = "200g curd + 2 eggs + 2 rotis"
            option = "High-protein option"

        return {
            "title": "Your next best action",
            "action": f"You're about {round(protein_gap)}g short on protein.",
            "recommendation": action,
            "option": option,
            "why": "Protein is currently your largest nutrition gap.",
        }

    if calorie_gap > 400:
        return {
            "title": "Your next best action",
            "action": f"You have about {round(calorie_gap)} kcal remaining.",
            "recommendation": "Build your next meal around protein + vegetables + a quality carb.",
            "option": "Balanced option",
            "why": "You have enough calorie room for a complete meal.",
        }

    if remain["fiber"] > 7:
        return {
            "title": "Your next best action",
            "action": f"You're about {round(remain['fiber'])}g short on fiber.",
            "recommendation": "Add fruit + vegetables + dal/beans to your next meal.",
            "option": "Fiber focus",
            "why": "Fiber is one of your remaining nutrition gaps.",
        }

    water_gap = max(target["water_glasses"] - st.session_state.water, 0)

    if water_gap > 2:
        return {
            "title": "Your next best action",
            "action": f"You have {water_gap} glasses of water left.",
            "recommendation": "Drink one glass now, then spread the rest across the evening.",
            "option": "Hydration",
            "why": "Your hydration tracker is behind today's target.",
        }

    return {
        "title": "You're on track",
        "action": "Keep your next meal balanced.",
        "recommendation": "Prioritize protein, vegetables and a sensible carb portion.",
        "option": "Maintain",
        "why": "Your tracked nutrition is currently reasonably balanced against your targets.",
    }


# =========================================================
# AUTOMATIC WORKOUT
# =========================================================

def automatic_workout():
    profile = st.session_state.profile

    goal = profile["goal"]
    activity = profile["activity"]

    if goal == "Muscle Gain":
        exercises = [
            ("Push-ups", "3 × 10–15"),
            ("Bodyweight Squats", "4 × 12–15"),
            ("Backpack Rows", "3 × 10–15"),
            ("Glute Bridges", "3 × 15"),
            ("Plank", "3 × 30–45 sec"),
        ]
        title = "Full Body Strength"

    elif goal == "Strength":
        exercises = [
            ("Push-ups", "4 × 8–12"),
            ("Bulgarian Split Squats", "3 × 8–12 / leg"),
            ("Backpack Rows", "4 × 8–12"),
            ("Pike Push-ups", "3 × 8–12"),
            ("Plank", "3 × 45 sec"),
        ]
        title = "Strength Builder"

    elif goal == "Calisthenics":
        exercises = [
            ("Push-ups", "4 × 8–15"),
            ("Bodyweight Squats", "4 × 15"),
            ("Pike Push-ups", "3 × 8–12"),
            ("Reverse Lunges", "3 × 10 / leg"),
            ("Plank", "3 × 45 sec"),
        ]
        title = "Calisthenics Session"

    elif goal in ["Fat Loss", "Recomposition", "Aesthetic Body", "Greek Body"]:
        exercises = [
            ("Brisk Walk", "15 min"),
            ("Bodyweight Squats", "3 × 15"),
            ("Push-ups", "3 × 10–15"),
            ("Reverse Lunges", "3 × 10 / leg"),
            ("Mountain Climbers", "3 × 30 sec"),
            ("Plank", "3 × 30–45 sec"),
        ]
        title = "Fat Loss + Conditioning"

    else:
        exercises = [
            ("Brisk Walk", "15 min"),
            ("Bodyweight Squats", "3 × 12–15"),
            ("Push-ups", "3 × 8–12"),
            ("Glute Bridges", "3 × 15"),
            ("Plank", "3 × 30 sec"),
        ]
        title = "Daily Fitness"

    if activity == "Sedentary":
        difficulty = "Beginner-friendly"
    elif activity == "Very Active":
        difficulty = "Higher volume"
    else:
        difficulty = "Moderate"

    return title, difficulty, exercises


# =========================================================
# NAVIGATION
# =========================================================

st.markdown(
    """
    <div style="text-align:center;margin-bottom:10px;">
        <span style="font-size:28px;">🥗</span>
        <span style="font-size:22px;font-weight:800;">NutriCoach</span>
    </div>
    """,
    unsafe_allow_html=True,
)

nav_cols = st.columns(5)

pages = [
    ("🏠", "Today"),
    ("🍽️", "Food"),
    ("🏋️", "Workout"),
    ("📊", "Progress"),
    ("👤", "Profile"),
]

for col, (icon, name) in zip(nav_cols, pages):
    with col:
        if st.button(
            f"{icon} {name}",
            use_container_width=True,
            type="primary" if st.session_state.page == name else "secondary",
            key=f"nav_{name}",
        ):
            st.session_state.page = name
            st.rerun()

st.markdown("<div class='nav-spacer'></div>", unsafe_allow_html=True)

# =========================================================
# HOME / TODAY
# =========================================================

if st.session_state.page == "Today":

    profile = st.session_state.profile
    targets = st.session_state.targets
    totals = total_nutrition()
    coach = coach_message()

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-title">Good to see you 👋</div>
            <div class="hero-sub">
                Your personal fitness dashboard · {profile["goal"]}
            </div>
            <div style="margin-top:14px;">
                <span class="chip">🎯 {profile["goal"]}</span>
                <span class="chip">🧍 {profile["body_type"]}</span>
                <span class="chip">🥗 {profile["diet"]}</span>
                <span class="chip">⚖️ {profile["weight"]:.1f} kg</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Profile summary
    st.markdown("### 👤 Your Profile")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Age", f'{profile["age"]}')
    c2.metric("Height", f'{profile["height"]:.0f} cm')
    c3.metric("Weight", f'{profile["weight"]:.1f} kg')
    c4.metric("Daily target", f'{targets["calories"]} kcal')

    # Main dashboard
    left, right = st.columns([1, 1.7])

    with left:
        calorie_pct = progress_percent(
            totals["calories"],
            targets["calories"],
        )

        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">🔥 Calories</div>
                <div class="ring" style="--progress:{calorie_pct}%">
                    <div class="ring-content">
                        <div class="ring-number">{round(totals["calories"])}</div>
                        <div class="ring-label">of {targets["calories"]}</div>
                    </div>
                </div>
                <div style="text-align:center;margin-top:12px;">
                    <span class="muted">
                        {round(max(targets["calories"] - totals["calories"], 0))}
                        kcal remaining
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📈 Today's Macros")

        for label, key, color in [
            ("Protein", "protein", "green"),
            ("Carbs", "carbs", "blue"),
            ("Fat", "fat", "orange"),
            ("Fiber", "fiber", "purple"),
        ]:
            value = totals[key]
            target = targets[key]

            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;">
                    <span>{label}</span>
                    <span class="{color}">
                        {round(value)} / {round(target)} g
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            progress_bar(value, target)

        st.markdown("</div>", unsafe_allow_html=True)

    # Coach
    st.markdown(
        f"""
        <div class="coach">
            <div class="coach-title">🧠 {coach["title"]}</div>
            <div class="coach-action">{coach["action"]}</div>
            <div style="font-size:16px;">
                <b>{coach["option"]}:</b> {coach["recommendation"]}
            </div>
            <div class="muted" style="margin-top:10px;">
                Why: {coach["why"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 💧 Hydration")

    water_target = targets["water_glasses"]
    water_done = st.session_state.water
    water_pct = progress_percent(water_done, water_target)

    w1, w2, w3 = st.columns([1, 3, 1])

    with w1:
        if st.button("−", use_container_width=True, key="water_minus"):
            st.session_state.water = max(0, st.session_state.water - 1)
            st.rerun()

    with w2:
        st.markdown(
            f"""
            <div style="text-align:center;">
                <div class="big-number">💧 {water_done}/{water_target}</div>
                <div class="muted">glasses today</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        progress_bar(water_done, water_target)

    with w3:
        if st.button("＋", use_container_width=True, key="water_plus"):
            st.session_state.water += 1
            st.rerun()

    # Automatic workout preview
    st.markdown("### 🏋️ Today's Automatic Workout")

    workout_title, difficulty, exercises = automatic_workout()

    with st.container():
        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">{workout_title}</div>
                <span class="chip">⚡ {difficulty}</span>
                <span class="chip">🎯 {profile["goal"]}</span>
            """,
            unsafe_allow_html=True,
        )

        for exercise, sets in exercises:
            st.markdown(
                f"**{exercise}** — <span class='muted'>{sets}</span>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if st.button(
            "🏁 Mark today's workout complete",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.workout_history.append({
                "date": TODAY,
                "workout": workout_title,
                "duration": 35,
                "calories": 180,
            })
            st.success("Workout added to your history.")

    # Recent foods
    st.markdown("### 🍽️ Today's Food")

    if not st.session_state.food_log:
        st.info("No food logged yet. Go to Food and search your first meal.")
    else:
        for item in reversed(st.session_state.food_log[-6:]):
            st.markdown(
                f"""
                <div class="meal">
                    <div class="meal-name">{item["name"]}</div>
                    <div class="meal-food">
                        {item["grams"]:.0f}g ·
                        {item["calories"]:.0f} kcal ·
                        {item["protein"]:.1f}g protein ·
                        {item["carbs"]:.1f}g carbs ·
                        {item["fat"]:.1f}g fat
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# =========================================================
# FOOD
# =========================================================

elif st.session_state.page == "Food":

    profile = st.session_state.profile
    targets = st.session_state.targets
    totals = total_nutrition()
    remain = remaining_targets()

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">🍽️ Your Food Command Center</div>
            <div class="hero-sub">
                Search food, calculate portions, track meals, follow your plan,
                and immediately see how every choice changes today's targets.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------
    # TARGET STRIP
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Calories left", f"{round(remain['calories'])} kcal")
    c2.metric("Protein left", f"{round(remain['protein'])} g")
    c3.metric("Carbs left", f"{round(remain['carbs'])} g")
    c4.metric("Fat left", f"{round(remain['fat'])} g")

    # -----------------------------------------------------
    # USDA SEARCH
    # -----------------------------------------------------

    st.markdown("## 🔎 Search & Add Food")

    search_col, button_col = st.columns([4, 1])

    with search_col:
        query = st.text_input(
            "Search USDA food database",
            placeholder="Try: egg, rice, paneer, banana, oats...",
            key="usda_query",
        )

    with button_col:
        st.write("")
        st.write("")
        search_clicked = st.button(
            "Search",
            use_container_width=True,
            type="primary",
        )

    if search_clicked and query.strip():
        foods, error = search_usda(query.strip())

        if error:
            st.error(error)
        elif foods:
            st.session_state.search_results = foods
        else:
            st.warning("No USDA foods found.")

    results = st.session_state.get("search_results", [])

    if results:
        st.markdown("### Choose your food")

        descriptions = [
            f'{f.get("description", "Unknown")} · {f.get("dataType", "")}'
            for f in results
        ]

        selected_index = st.selectbox(
            "USDA result",
            range(len(descriptions)),
            format_func=lambda i: descriptions[i],
        )

        selected_food = results[selected_index]

        s1, s2, s3 = st.columns([1.3, 1.3, 1])

        with s1:
            serving_mode = st.selectbox(
                "Serving",
                ["Grams", "Pieces"],
            )

        with s2:
            if serving_mode == "Grams":
                amount = st.number_input(
                    "Amount",
                    min_value=1.0,
                    value=100.0,
                    step=5.0,
                )
                grams = amount
            else:
                pieces = st.number_input(
                    "Pieces",
                    min_value=1.0,
                    value=1.0,
                    step=1.0,
                )
                grams = pieces * estimate_piece_weight(
                    selected_food.get("description", "")
                )

        with s3:
            st.markdown(
                f"""
                <div class="small-card">
                    <div class="muted">Estimated weight</div>
                    <div class="big-number">{grams:.0f}g</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        preview = nutrition_dict_from_usda(
            selected_food,
            grams,
        )

        st.markdown("### 🧾 Nutrition for this serving")

        n1, n2, n3, n4, n5 = st.columns(5)

        n1.metric("Calories", f'{preview["calories"]:.0f}')
        n2.metric("Protein", f'{preview["protein"]:.1f} g')
        n3.metric("Carbs", f'{preview["carbs"]:.1f} g')
        n4.metric("Fat", f'{preview["fat"]:.1f} g')
        n5.metric("Fiber", f'{preview["fiber"]:.1f} g')

        new_remaining = {
            "calories": max(remain["calories"] - preview["calories"], 0),
            "protein": max(remain["protein"] - preview["protein"], 0),
            "carbs": max(remain["carbs"] - preview["carbs"], 0),
            "fat": max(remain["fat"] - preview["fat"], 0),
        }

        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">⚡ What this does to today's targets</div>
                <div class="muted">If you add this serving:</div>
                <div style="margin-top:12px;">
                    <span class="chip">
                        🔥 {new_remaining["calories"]:.0f} kcal left
                    </span>
                    <span class="chip">
                        💪 {new_remaining["protein"]:.1f}g protein left
                    </span>
                    <span class="chip">
                        🍚 {new_remaining["carbs"]:.1f}g carbs left
                    </span>
                    <span class="chip">
                        🥑 {new_remaining["fat"]:.1f}g fat left
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "＋ Add this serving to today's food",
            use_container_width=True,
            type="primary",
        ):
            item = make_food_item(
                selected_food,
                grams,
            )

            st.session_state.food_log.append(item)
            st.success(f'Added {item["name"]}.')

    # -----------------------------------------------------
    # PERSONAL CALCULATOR
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("## 🧮 Personal Food Calculator")

    st.caption(
        "Use this when you ate something that is not in your planned diet. "
        "Enter the nutrition from the package/label and NutriCoach will calculate "
        "the effect on today's remaining targets."
    )

    pc1, pc2 = st.columns(2)

    with pc1:
        custom_name = st.text_input(
            "Food name",
            placeholder="Example: Homemade paneer sandwich",
        )

        custom_calories = st.number_input(
            "Calories",
            min_value=0.0,
            value=0.0,
            step=10.0,
        )

        custom_protein = st.number_input(
            "Protein (g)",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

    with pc2:
        custom_carbs = st.number_input(
            "Carbs (g)",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

        custom_fat = st.number_input(
            "Fat (g)",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

        custom_fiber = st.number_input(
            "Fiber (g)",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

    if st.button(
        "Calculate & Add Custom Food",
        use_container_width=True,
    ):
        if not custom_name.strip():
            st.warning("Enter a food name.")
        else:
            st.session_state.food_log.append({
                "name": custom_name,
                "grams": 1,
                "calories": custom_calories,
                "protein": custom_protein,
                "carbs": custom_carbs,
                "fat": custom_fat,
                "fiber": custom_fiber,
                "vitamin_a": 0,
                "vitamin_c": 0,
                "calcium": 0,
                "iron": 0,
                "magnesium": 0,
                "potassium": 0,
            })
            st.success("Custom food added.")

    # -----------------------------------------------------
    # 14 DAY PLAN
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("## 📅 Your 14-Day Diet")

    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown(
            f"""
            <div class="small-card">
                <div class="muted">Current cycle</div>
                <div class="big-number">Cycle {st.session_state.diet_cycle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p2:
        if st.button(
            "🔄 Generate New 14 Days",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.diet_cycle += 1
            st.session_state.diet_plan = generate_diet_plan(
                st.session_state.diet_cycle
            )
            st.rerun()

    with p3:
        st.markdown(
            f"""
            <div class="small-card">
                <div class="muted">Diet preference</div>
                <div class="big-number" style="font-size:20px;">
                    {profile["diet"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    selected_day = st.selectbox(
        "View day",
        list(range(1, 15)),
        format_func=lambda x: f"Day {x}",
    )

    day_plan = st.session_state.diet_plan[selected_day - 1]

    meal_targets = {
        "breakfast": (.25, .25),
        "lunch": (.30, .30),
        "snack": (.15, .15),
        "dinner": (.30, .30),
    }

    meal_labels = {
        "breakfast": "🌅 Breakfast",
        "lunch": "☀️ Lunch",
        "snack": "🍎 Snack",
        "dinner": "🌙 Dinner",
    }

    for meal_key in ["breakfast", "lunch", "snack", "dinner"]:

        kcal_pct, protein_pct = meal_targets[meal_key]

        st.markdown(
            f"""
            <div class="meal">
                <div class="meal-name">
                    {meal_labels[meal_key]}
                </div>
                <div class="meal-food">
                    {day_plan[meal_key]}
                </div>
                <div style="margin-top:8px;">
                    <span class="chip">
                        ~{round(targets["calories"] * kcal_pct)} kcal
                    </span>
                    <span class="chip">
                        ~{round(targets["protein"] * protein_pct)}g protein
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        swap_key = f"swap_{selected_day}_{meal_key}"

        if st.button(
            f"🔄 Swap {meal_labels[meal_key]}",
            key=swap_key,
        ):
            lists = {
                "breakfast": BREAKFASTS,
                "lunch": LUNCHES,
                "snack": SNACKS,
                "dinner": DINNERS,
            }

            new_meal = adapt_meal(
                random.choice(lists[meal_key]),
                profile["diet"],
            )

            st.session_state.diet_plan[selected_day - 1][meal_key] = new_meal
            st.rerun()

    # -----------------------------------------------------
    # MEAL TRACKING
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("## ☑️ Meal Tracking")

    today_plan = st.session_state.diet_plan[0]

    for meal_key in ["breakfast", "lunch", "snack", "dinner"]:
        status_key = f"{TODAY}_{meal_key}"

        checked = st.checkbox(
            f'{meal_labels[meal_key]} — {today_plan[meal_key]}',
            value=st.session_state.meal_status.get(
                status_key,
                False,
            ),
            key=f"check_{meal_key}",
        )

        st.session_state.meal_status[status_key] = checked

        timer_key = f"{TODAY}_{meal_key}"

        timer_cols = st.columns([1, 1, 3])

        with timer_cols[0]:
            if st.button(
                "▶ Start",
                key=f"start_{meal_key}",
            ):
                st.session_state.meal_timers[timer_key] = {
                    "start": time.time(),
                    "end": None,
                }

        with timer_cols[1]:
            if st.button(
                "■ Stop",
                key=f"stop_{meal_key}",
            ):
                if timer_key in st.session_state.meal_timers:
                    st.session_state.meal_timers[timer_key]["end"] = time.time()

        with timer_cols[2]:
            timer = st.session_state.meal_timers.get(timer_key)

            if timer:
                end = timer["end"] or time.time()
                elapsed = int(end - timer["start"])
                minutes = elapsed // 60
                seconds = elapsed % 60

                st.caption(
                    f"⏱ Meal timer: {minutes:02d}:{seconds:02d}"
                )

    # -----------------------------------------------------
    # SUPPLEMENTS
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("## 💊 Optional Supplements")

    supplements = [
        ("Protein powder", "Use when convenient to help meet protein needs."),
        ("Peanut butter", "Easy calorie and protein addition."),
        ("Creatine", "Commonly used for strength and training support."),
        ("Multivitamin", "Optional; does not replace a varied diet."),
        ("Omega-3", "Optional dietary supplement."),
        ("Electrolytes", "More relevant around heavy sweating or long sessions."),
    ]

    for name, description in supplements:
        key = name.lower().replace(" ", "_")
        value = st.checkbox(
            f"{name} — {description}",
            value=st.session_state.supplements.get(key, False),
            key=f"supp_{key}",
        )
        st.session_state.supplements[key] = value

    # -----------------------------------------------------
    # FOOD LOG
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("## 📋 Today's Food Log")

    if not st.session_state.food_log:
        st.info("Nothing logged yet.")
    else:
        for i, item in enumerate(st.session_state.food_log):
            c1, c2 = st.columns([5, 1])

            with c1:
                st.markdown(
                    f"""
                    <div class="meal">
                        <div class="meal-name">{item["name"]}</div>
                        <div class="meal-food">
                            {item["grams"]:.0f}g ·
                            {item["calories"]:.0f} kcal ·
                            {item["protein"]:.1f}g protein
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                if st.button(
                    "Remove",
                    key=f"remove_food_{i}",
                ):
                    st.session_state.food_log.pop(i)
                    st.rerun()

    # -----------------------------------------------------
    # MICRONUTRIENTS
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("## 🧬 Micronutrients")

    micro = total_nutrition()

    m1, m2, m3, m4, m5 = st.columns(5)

    m1.metric("Vitamin A", f'{micro["vitamin_a"]:.0f} µg')
    m2.metric("Vitamin C", f'{micro["vitamin_c"]:.0f} mg')
    m3.metric("Calcium", f'{micro["calcium"]:.0f} mg')
    m4.metric("Iron", f'{micro["iron"]:.1f} mg')
    m5.metric("Potassium", f'{micro["potassium"]:.0f} mg')

    st.caption(
        "USDA search values are used where available. Piece-based portions are estimates."
    )

# =========================================================
# WORKOUT
# =========================================================

elif st.session_state.page == "Workout":

    profile = st.session_state.profile

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">🏋️ Automatic Workout</div>
            <div class="hero-sub">
                No exercise selection needed. Your routine is generated from
                your goal, activity level and profile.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    title, difficulty, exercises = automatic_workout()

    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">{title}</div>
            <span class="chip">🎯 {profile["goal"]}</span>
            <span class="chip">⚡ {difficulty}</span>
            <span class="chip">⏱ ~35 min</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i, (exercise, prescription) in enumerate(exercises, 1):
        st.markdown(
            f"""
            <div class="meal">
                <div class="meal-name">{i}. {exercise}</div>
                <div class="meal-food">{prescription}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### ⏱ Workout Timer")

    if "workout_timer" not in st.session_state:
        st.session_state.workout_timer = None

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button(
            "▶ Start Workout",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.workout_timer = {
                "start": time.time(),
                "end": None,
            }

    with c2:
        if st.button(
            "■ Stop Timer",
            use_container_width=True,
        ):
            if st.session_state.workout_timer:
                st.session_state.workout_timer["end"] = time.time()

    with c3:
        if st.button(
            "✓ Complete",
            use_container_width=True,
        ):
            st.session_state.workout_history.append({
                "date": TODAY,
                "workout": title,
                "duration": 35,
                "calories": 180,
            })
            st.success("Workout recorded.")

    timer = st.session_state.workout_timer

    if timer:
        end = timer["end"] or time.time()
        elapsed = int(end - timer["start"])

        st.markdown(
            f"""
            <div class="card" style="text-align:center;">
                <div class="muted">Elapsed</div>
                <div style="font-size:48px;font-weight:800;">
                    {elapsed // 60:02d}:{elapsed % 60:02d}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📈 Workout History")

    if st.session_state.workout_history:
        for item in reversed(st.session_state.workout_history):
            st.markdown(
                f"""
                <div class="meal">
                    <b>{item["date"]}</b> · {item["workout"]}
                    <div class="muted">
                        {item["duration"]} min · ~{item["calories"]} kcal
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Complete your first workout to start your history.")

# =========================================================
# PROGRESS
# =========================================================

elif st.session_state.page == "Progress":

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">📊 Body Progress</div>
            <div class="hero-sub">
                Track measurements, trends and body photos over time.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 📏 New Measurement")

    c1, c2, c3 = st.columns(3)

    with c1:
        current_weight = st.number_input(
            "Weight (kg)",
            min_value=20.0,
            max_value=300.0,
            value=float(st.session_state.profile["weight"]),
            step=0.1,
        )

        waist = st.number_input(
            "Waist (cm)",
            min_value=30.0,
            max_value=250.0,
            value=80.0,
            step=0.5,
        )

    with c2:
        chest = st.number_input(
            "Chest (cm)",
            min_value=30.0,
            max_value=250.0,
            value=90.0,
            step=0.5,
        )

        arms = st.number_input(
            "Arms (cm)",
            min_value=10.0,
            max_value=100.0,
            value=30.0,
            step=0.5,
        )

    with c3:
        legs = st.number_input(
            "Legs / thigh (cm)",
            min_value=20.0,
            max_value=150.0,
            value=50.0,
            step=0.5,
        )

        shoulders = st.number_input(
            "Shoulders (cm)",
            min_value=30.0,
            max_value=200.0,
            value=45.0,
            step=0.5,
        )

    if st.button(
        "＋ Save Measurement",
        use_container_width=True,
        type="primary",
    ):
        record = {
            "date": TODAY,
            "weight": current_weight,
            "waist": waist,
            "chest": chest,
            "arms": arms,
            "legs": legs,
            "shoulders": shoulders,
        }

        st.session_state.body_history.append(record)

        if not st.session_state.weight_history or \
                st.session_state.weight_history[-1]["date"] != TODAY:
            st.session_state.weight_history.append({
                "date": TODAY,
                "weight": current_weight,
            })

        if not st.session_state.waist_history or \
                st.session_state.waist_history[-1]["date"] != TODAY:
            st.session_state.waist_history.append({
                "date": TODAY,
                "waist": waist,
            })

        st.session_state.profile["weight"] = current_weight
        st.session_state.targets = calculate_targets(
            st.session_state.profile
        )

        st.success("Measurement saved.")

    # Charts
    if st.session_state.body_history:

        st.markdown("## 📈 Trends")

        try:
            import pandas as pd

            df = pd.DataFrame(
                st.session_state.body_history
            )

            if len(df) > 1:
                st.markdown("### Weight")
                st.line_chart(
                    df.set_index("date")["weight"]
                )

                st.markdown("### Waist")
                st.line_chart(
                    df.set_index("date")["waist"]
                )

                st.markdown("### Body Measurements")
                st.line_chart(
                    df.set_index("date")[
                        ["chest", "arms", "legs", "shoulders"]
                    ]
                )
            else:
                st.info("Add measurements on different days to see trends.")

        except Exception:
            pass

    # Body scan
    st.markdown("---")
    st.markdown("## 📸 Body Scan")

    st.markdown(
        """
        <div class="card">
            <div class="card-title">Camera-based progress system</div>
            <div class="muted">
                Capture consistent front, side and back photos.
                NutriCoach can compare visual progress, while measurements
                provide the reliable numeric trend.
            </div>
            <div style="margin-top:12px;">
                <span class="chip">Front</span>
                <span class="chip">Side</span>
                <span class="chip">Back</span>
                <span class="chip">Posture</span>
                <span class="chip">Proportion</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    angle = st.selectbox(
        "Camera angle",
        ["Front", "Side", "Back"],
    )

    photo = st.camera_input(
        f"Take {angle.lower()} photo"
    )

    if photo is not None:
        photo_bytes = photo.getvalue()

        if st.button(
            f"Save {angle} progress photo",
            use_container_width=True,
        ):
            st.session_state.photos.append({
                "date": TODAY,
                "angle": angle,
                "bytes": photo_bytes,
            })
            st.success(f"{angle} photo saved.")

    # Numeric proportion
    if st.session_state.body_history:
        latest = st.session_state.body_history[-1]

        waist_value = latest["waist"]
        shoulder_value = latest["shoulders"]

        if waist_value > 0:
            proportion = shoulder_value / waist_value

            st.markdown(
                f"""
                <div class="card">
                    <div class="card-title">📐 Current proportion estimate</div>
                    <div class="big-number">{proportion:.2f}</div>
                    <div class="muted">
                        Shoulder-to-waist measurement ratio based on your
                        manually entered measurements.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Photos
    if st.session_state.photos:
        st.markdown("## 🖼️ Progress Photos")

        for saved in reversed(st.session_state.photos[-6:]):
            st.markdown(
                f"**{saved['date']} · {saved['angle']}**"
            )
            st.image(saved["bytes"], width=260)

    st.caption(
        "A normal phone camera cannot reliably determine exact body measurements "
        "in centimetres from a single uncalibrated image. Treat visual scan "
        "outputs as progress references and confirm measurements manually."
    )

# =========================================================
# PROFILE
# =========================================================

elif st.session_state.page == "Profile":

    profile = st.session_state.profile

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">👤 My Profile</div>
            <div class="hero-sub">
                These settings drive your calories, macros, diet and automatic workout.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        age = st.number_input(
            "Age",
            min_value=13,
            max_value=100,
            value=int(profile["age"]),
        )

        sex = st.selectbox(
            "Sex",
            ["Male", "Female"],
            index=["Male", "Female"].index(profile["sex"]),
        )

        height = st.number_input(
            "Height (cm)",
            min_value=100.0,
            max_value=230.0,
            value=float(profile["height"]),
            step=0.5,
        )

        weight = st.number_input(
            "Weight (kg)",
            min_value=30.0,
            max_value=250.0,
            value=float(profile["weight"]),
            step=0.1,
        )

        activity = st.selectbox(
            "Activity level",
            [
                "Sedentary",
                "Lightly Active",
                "Moderately Active",
                "Very Active",
            ],
            index=[
                "Sedentary",
                "Lightly Active",
                "Moderately Active",
                "Very Active",
            ].index(profile["activity"]),
        )

    with c2:
        diet = st.selectbox(
            "Diet preference",
            [
                "Vegetarian",
                "Vegan",
                "Non-Vegetarian",
            ],
            index=[
                "Vegetarian",
                "Vegan",
                "Non-Vegetarian",
            ].index(profile["diet"]),
        )

        budget = st.selectbox(
            "Food budget",
            ["Low", "Medium", "High"],
            index=[
                "Low",
                "Medium",
                "High",
            ].index(profile["budget"]),
        )

        body_type = st.selectbox(
            "Current body type",
            [
                "Slim/Skinny",
                "Skinny Fat",
                "Average",
                "Athletic",
                "Muscular",
                "Higher Body Fat",
            ],
            index=[
                "Slim/Skinny",
                "Skinny Fat",
                "Average",
                "Athletic",
                "Muscular",
                "Higher Body Fat",
            ].index(profile["body_type"]),
        )

        goal = st.selectbox(
            "Body goal",
            [
                "General Fitness",
                "Calisthenics",
                "Greek Body",
                "Aesthetic Body",
                "Muscle Gain",
                "Fat Loss",
                "Strength",
                "Recomposition",
            ],
            index=[
                "General Fitness",
                "Calisthenics",
                "Greek Body",
                "Aesthetic Body",
                "Muscle Gain",
                "Fat Loss",
                "Strength",
                "Recomposition",
            ].index(profile["goal"]),
        )

    if st.button(
        "💾 Save Profile & Recalculate",
        use_container_width=True,
        type="primary",
    ):
        st.session_state.profile = {
            "age": age,
            "sex": sex,
            "height": height,
            "weight": weight,
            "activity": activity,
            "diet": diet,
            "budget": budget,
            "body_type": body_type,
            "goal": goal,
        }

        st.session_state.targets = calculate_targets(
            st.session_state.profile
        )

        # Regenerate plan for the updated diet preference.
        st.session_state.diet_cycle += 1
        st.session_state.diet_plan = generate_diet_plan(
            st.session_state.diet_cycle
        )

        st.success("Profile updated. Nutrition targets and workout updated.")

    st.markdown("---")
    st.markdown("## 🎯 Your Calculated Targets")

    targets = st.session_state.targets

    a, b, c, d = st.columns(4)

    a.metric("Calories", f'{targets["calories"]} kcal')
    b.metric("Protein", f'{targets["protein"]} g')
    c.metric("Carbs", f'{targets["carbs"]} g')
    d.metric("Fat", f'{targets["fat"]} g')

    a, b, c, d = st.columns(4)

    a.metric("Fiber", f'{targets["fiber"]} g')
    b.metric("Water", f'{targets["water_glasses"]} glasses')
    c.metric("BMR", f'{targets["bmr"]} kcal')
    d.metric("Estimated TDEE", f'{targets["tdee"]} kcal')

    st.caption(
        "These are general estimates based on the Mifflin-St Jeor equation and "
        "the profile information you entered. They are not medical prescriptions."
    )

    st.markdown("---")
    st.markdown("## 🧍 Body Type Guide")

    body_descriptions = {
        "Slim/Skinny":
            "Lower body mass with a naturally lean appearance.",
        "Skinny Fat":
            "A user-selected descriptive category for relatively low muscle with "
            "more noticeable fat around the midsection; not a medical diagnosis.",
        "Average":
            "General middle-range body composition.",
        "Athletic":
            "Regular training with noticeable muscle development and conditioning.",
        "Muscular":
            "Higher-than-average muscle development.",
        "Higher Body Fat":
            "Higher visible or measured body-fat levels.",
    }

    for name, description in body_descriptions.items():
        st.markdown(
            f"""
            <div class="meal">
                <div class="meal-name">{name}</div>
                <div class="meal-food">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div style="
        text-align:center;
        color:#667970;
        padding:30px 0 10px;
        font-size:12px;
    ">
        NutriCoach · Personal nutrition + fitness MVP
    </div>
    """,
    unsafe_allow_html=True,
)
