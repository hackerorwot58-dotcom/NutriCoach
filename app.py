import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import random
import re

# =========================================================
# NUTRICOACH — POLISHED MVP
# =========================================================

st.set_page_config(
    page_title="NutriCoach",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------------
# STYLE
# -------------------------
st.markdown("""
<style>
    .stApp {
        background: #f6f8fb;
    }

    .block-container {
        max-width: 1250px;
        padding-top: 1rem;
        padding-bottom: 4rem;
    }

    .hero {
        background: linear-gradient(135deg, #111827, #263449);
        color: white;
        padding: 28px;
        border-radius: 24px;
        margin-bottom: 18px;
    }

    .hero h1 {
        margin: 0;
        font-size: 38px;
    }

    .hero p {
        color: #d1d5db;
        margin-top: 8px;
        font-size: 16px;
    }

    .card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.04);
    }

    .coach {
        background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
        border: 1px solid #bbf7d0;
        border-radius: 22px;
        padding: 24px;
        margin: 15px 0 22px 0;
    }

    .coach h2 {
        margin-top: 0;
    }

    .big-number {
        font-size: 30px;
        font-weight: 800;
        margin: 0;
    }

    .muted {
        color: #6b7280;
        font-size: 14px;
    }

    .pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #eef2ff;
        font-size: 12px;
        margin-right: 5px;
    }

    .meal {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 17px;
        border-radius: 18px;
        margin-bottom: 12px;
    }

    .meal-title {
        font-size: 18px;
        font-weight: 750;
    }

    .nav-label {
        text-align: center;
        font-weight: 700;
        font-size: 14px;
    }

    div[data-testid="stMetric"] {
        background: white;
        padding: 12px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
    }

    @media (max-width: 700px) {
        .block-container {
            padding: 0.7rem;
        }

        .hero h1 {
            font-size: 29px;
        }

        .hero {
            padding: 20px;
            border-radius: 20px;
        }

        .card {
            padding: 15px;
            border-radius: 17px;
        }
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE
# =========================================================

def init_state():
    defaults = {
        "page": "Today",
        "profile": {},
        "targets": {},
        "food_log": [],
        "water_glasses": 0,
        "water_target": 8,
        "meal_done": {},
        "weight_history": [],
        "waist_history": [],
        "workout_history": [],
        "body_photos": {},
        "diet_cycle": 1,
        "diet_plan": [],
        "coach_message": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# =========================================================
# HELPERS
# =========================================================

def safe_float(value, default=0):
    try:
        return float(value)
    except:
        return default


def clean_number(value):
    return round(safe_float(value), 1)


def today_string():
    return date.today().isoformat()


def profile_ready():
    required = ["age", "sex", "height", "weight", "activity", "diet", "goal"]
    return all(k in st.session_state.profile for k in required)


def current_totals():
    totals = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "fiber": 0,
        "vitamin_a": 0,
        "vitamin_c": 0,
        "vitamin_d": 0,
        "calcium": 0,
        "iron": 0,
        "magnesium": 0,
        "potassium": 0,
        "zinc": 0,
    }

    for item in st.session_state.food_log:
        for key in totals:
            totals[key] += safe_float(item.get(key, 0))

    return {k: round(v, 1) for k, v in totals.items()}


def remaining_targets():
    totals = current_totals()
    targets = st.session_state.targets

    return {
        key: round(max(0, safe_float(targets.get(key, 0)) - totals.get(key, 0)), 1)
        for key in ["calories", "protein", "carbs", "fat", "fiber"]
    }


def percent(current, target):
    if target <= 0:
        return 0
    return min(100, max(0, current / target * 100))


# =========================================================
# CALORIE / MACRO CALCULATOR
# =========================================================

def calculate_targets(age, sex, height, weight, activity, goal):
    if sex == "Male":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    activity_factor = {
        "Sedentary": 1.20,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
    }

    tdee = bmr * activity_factor.get(activity, 1.2)

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

    calories = tdee + adjustments.get(goal, 0)

    # Conservative floor for this MVP.
    if sex == "Male":
        calories = max(calories, 1500)
    else:
        calories = max(calories, 1300)

    if goal in ["Muscle Gain", "Strength", "Calisthenics"]:
        protein_factor = 1.8
    elif goal in [
        "Fat Loss",
        "Recomposition",
        "Aesthetic Body",
        "Greek Body",
    ]:
        protein_factor = 1.7
    else:
        protein_factor = 1.6

    protein = weight * protein_factor
    fat = weight * 0.8

    remaining_calories = calories - (protein * 4) - (fat * 9)
    carbs = max(80, remaining_calories / 4)

    fiber = calories / 1000 * 14
    water_liters = weight * 0.035

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": round(calories),
        "protein": round(protein),
        "carbs": round(carbs),
        "fat": round(fat),
        "fiber": round(fiber),
        "water_liters": round(water_liters, 1),
        "water_glasses": max(1, round(water_liters / 0.25)),
    }


# =========================================================
# USDA API
# =========================================================

def get_usda_key():
    try:
        return st.secrets["FDC_API_KEY"]
    except:
        return None


def search_usda(query, page_size=8):
    key = get_usda_key()

    if not key:
        return None, "USDA API key not found."

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {
        "api_key": key,
        "query": query,
        "pageSize": page_size,
    }

    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None, f"USDA error: {response.status_code}"

        return response.json().get("foods", []), None

    except Exception as e:
        return None, f"Connection error: {e}"


def get_nutrients(food):
    nutrients = {}

    for nutrient in food.get("foodNutrients", []):
        name = nutrient.get("nutrientName")
        value = nutrient.get("value", 0)

        if name:
            nutrients[name] = safe_float(value)

    return {
        "calories": nutrients.get("Energy", 0),
        "protein": nutrients.get("Protein", 0),
        "carbs": nutrients.get("Carbohydrate, by difference", 0),
        "fat": nutrients.get("Total lipid (fat)", 0),
        "fiber": nutrients.get("Fiber, total dietary", 0),
        "vitamin_a": nutrients.get("Vitamin A, RAE", 0),
        "vitamin_c": nutrients.get(
            "Vitamin C, total ascorbic acid", 0
        ),
        "vitamin_d": nutrients.get("Vitamin D (D2 + D3)", 0),
        "calcium": nutrients.get("Calcium, Ca", 0),
        "iron": nutrients.get("Iron, Fe", 0),
        "magnesium": nutrients.get("Magnesium, Mg", 0),
        "potassium": nutrients.get("Potassium, K", 0),
        "zinc": nutrients.get("Zinc, Zn", 0),
    }


def detect_piece_weight(food_name):
    name = food_name.lower()

    mapping = {
        "egg": 50,
        "banana": 118,
        "apple": 182,
        "orange": 130,
        "roti": 40,
        "chapati": 40,
    }

    for item, grams in mapping.items():
        if item in name:
            return grams

    return 100


# =========================================================
# FOOD RECOMMENDATION ENGINE
# =========================================================

FOOD_OPTIONS = {
    "Vegetarian": [
        "curd",
        "paneer",
        "milk",
        "lentils",
        "chickpeas",
        "roti",
        "rice",
        "oats",
        "banana",
        "vegetables",
    ],
    "Vegan": [
        "soy chunks",
        "tofu",
        "lentils",
        "chickpeas",
        "beans",
        "rice",
        "roti",
        "oats",
        "banana",
        "vegetables",
    ],
    "Non-vegetarian": [
        "eggs",
        "chicken",
        "curd",
        "rice",
        "roti",
        "oats",
        "banana",
        "lentils",
        "vegetables",
    ],
}


def coach_recommendation():
    if not profile_ready():
        return (
            "Complete your profile first. Then I'll calculate your "
            "calorie, protein, fiber and hydration gaps."
        )

    rem = remaining_targets()
    diet = st.session_state.profile.get("diet", "Vegetarian")

    protein_gap = rem["protein"]
    calorie_gap = rem["calories"]

    if protein_gap > 40:
        if diet == "Vegan":
            option = (
                "80g soy chunks + rice + vegetables"
            )
        elif diet == "Vegetarian":
            option = (
                "200g curd + 100g roasted chana + 2 rotis"
            )
        else:
            option = (
                "150g chicken + 2 rotis + salad"
            )

        return (
            f"**You're about {protein_gap:.0f}g short on protein.** "
            f"You have roughly {calorie_gap:.0f} kcal remaining.\n\n"
            f"### 🥗 Your next best action\n"
            f"Try: **{option}**\n\n"
            f"**Why:** protein is currently your largest nutrition gap."
        )

    if rem["fiber"] > 8:
        return (
            f"You're only about {protein_gap:.0f}g away from your "
            f"protein target, but fiber is still low.\n\n"
            "**Next action:** add vegetables, fruit, oats, beans or "
            "whole grains to your next meal."
        )

    if calorie_gap > 500:
        return (
            f"You have about **{calorie_gap:.0f} kcal** left today.\n\n"
            "**Next action:** build a balanced meal around protein + "
            "a carbohydrate source + vegetables."
        )

    if calorie_gap < 150:
        return (
            "You're close to your calorie target. Focus on hydration "
            "and a protein-rich option if you're still hungry."
        )

    return (
        "Your nutrition is looking fairly balanced.\n\n"
        "Keep your next meal protein-focused and continue tracking "
        "water."
    )


# =========================================================
# DIET PLAN
# =========================================================

BASE_MEALS = {
    "Vegetarian": [
        ("Breakfast", "Oats + milk + banana"),
        ("Lunch", "2 rotis + dal + mixed vegetables + curd"),
        ("Snack", "Roasted chana + fruit"),
        ("Dinner", "Paneer + rice + salad"),
    ],
    "Vegan": [
        ("Breakfast", "Oats + soy milk + banana"),
        ("Lunch", "Rice + dal + vegetables"),
        ("Snack", "Roasted chana + fruit"),
        ("Dinner", "Tofu + 2 rotis + salad"),
    ],
    "Non-vegetarian": [
        ("Breakfast", "3 eggs + oats + banana"),
        ("Lunch", "Chicken + rice + vegetables"),
        ("Snack", "Curd + roasted chana"),
        ("Dinner", "Egg bhurji + 2 rotis + salad"),
    ],
}


def create_diet_plan(cycle=1):
    profile = st.session_state.profile
    diet = profile.get("diet", "Vegetarian")
    goal = profile.get("goal", "General Fitness")

    meals = BASE_MEALS[diet].copy()

    alternatives = [
        ("Breakfast", "Poha + eggs/curd + fruit"),
        ("Lunch", "Rajma + rice + salad"),
        ("Snack", "Peanut butter toast + fruit"),
        ("Dinner", "Dal + roti + vegetables + curd"),
        ("Breakfast", "Besan chilla + curd"),
        ("Lunch", "Chole + roti + vegetables"),
        ("Snack", "Milk/soy milk + banana"),
        ("Dinner", "Paneer/tofu bowl + rice + salad"),
    ]

    random.seed(cycle * 999)

    plan = []

    for day in range(1, 15):
        day_meals = meals.copy()

        # Create variety across the 14 days.
        if day > 1:
            extra = random.sample(alternatives, 2)

            day_meals[0] = extra[0]
            day_meals[2] = extra[1]

        # Goal-specific wording.
        if goal in ["Muscle Gain", "Strength", "Calisthenics"]:
            note = "Higher-protein focus"
        elif goal in ["Fat Loss", "Aesthetic Body", "Greek Body"]:
            note = "Protein + volume-focused"
        else:
            note = "Balanced fitness day"

        plan.append({
            "day": day,
            "note": note,
            "meals": day_meals,
        })

    return plan


def swap_meal(day_index, meal_index):
    profile = st.session_state.profile
    diet = profile.get("diet", "Vegetarian")

    choices = [
        "Oats + fruit + milk/soy milk",
        "Besan chilla + curd",
        "Eggs + roti + fruit",
        "Dal + rice + vegetables",
        "Chole + roti + salad",
        "Paneer/tofu + rice + vegetables",
        "Curd + roasted chana + fruit",
        "Peanut butter toast + banana",
    ]

    if diet == "Vegan":
        choices = [
            "Oats + soy milk + banana",
            "Besan chilla + vegetables",
            "Dal + rice + vegetables",
            "Chole + roti + salad",
            "Tofu + rice + vegetables",
            "Soy chunks + roti + salad",
            "Roasted chana + fruit",
        ]

    if diet == "Non-vegetarian":
        choices += [
            "Chicken + rice + vegetables",
            "Egg bhurji + roti + salad",
        ]

    current = st.session_state.diet_plan[
        day_index
    ]["meals"][meal_index][1]

    available = [x for x in choices if x != current]

    replacement = random.choice(available)

    meal_name = st.session_state.diet_plan[
        day_index
    ]["meals"][meal_index][0]

    st.session_state.diet_plan[day_index]["meals"][
        meal_index
    ] = (meal_name, replacement)


# =========================================================
# AUTOMATIC WORKOUT ENGINE
# =========================================================

def generate_workout():
    profile = st.session_state.profile

    goal = profile.get("goal", "General Fitness")
    activity = profile.get("activity", "Moderately Active")

    if goal == "Muscle Gain":
        workouts = [
            ("Full Body Strength", 45, "Moderate"),
            ("Upper Body + Core", 40, "Moderate"),
            ("Lower Body Strength", 45, "Moderate"),
        ]

    elif goal == "Strength":
        workouts = [
            ("Full Body Strength", 50, "High"),
            ("Lower Body + Core", 45, "High"),
            ("Upper Body Strength", 45, "High"),
        ]

    elif goal == "Calisthenics":
        workouts = [
            ("Calisthenics Push + Core", 40, "Moderate"),
            ("Calisthenics Pull + Legs", 45, "Moderate"),
            ("Full Body Calisthenics", 45, "High"),
        ]

    elif goal in ["Fat Loss", "Aesthetic Body", "Greek Body"]:
        workouts = [
            ("Full Body + Conditioning", 45, "Moderate"),
            ("Lower Body + Core", 40, "Moderate"),
            ("Upper Body + Cardio", 45, "Moderate"),
        ]

    else:
        workouts = [
            ("Full Body Fitness", 35, "Light"),
            ("Walk + Mobility", 40, "Light"),
            ("Full Body + Core", 35, "Moderate"),
        ]

    if activity == "Sedentary":
        workouts = [
            (name, max(25, duration - 10), intensity)
            for name, duration, intensity in workouts
        ]

    index = date.today().weekday() % len(workouts)
    return workouts[index]


def estimated_workout_calories(duration, weight, intensity):
    factor = {
        "Light": 4,
        "Moderate": 6,
        "High": 8,
    }.get(intensity, 5)

    return round(duration * weight * factor / 60)


# =========================================================
# NAVIGATION
# =========================================================

st.markdown("""
<div class="hero">
    <h1>🥗 NutriCoach</h1>
    <p>Your personal nutrition, workout and body-progress command center.</p>
</div>
""", unsafe_allow_html=True)

nav_cols = st.columns(5)

pages = [
    ("🏠", "Today"),
    ("🍽️", "Food"),
    ("🏋️", "Workout"),
    ("📊", "Progress"),
    ("👤", "Profile"),
]

for col, (icon, label) in zip(nav_cols, pages):
    with col:
        if st.button(
            f"{icon}\n{label}",
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if st.session_state.page == label else "secondary",
        ):
            st.session_state.page = label
            st.rerun()


# =========================================================
# PROFILE PAGE
# =========================================================

if st.session_state.page == "Profile":

    st.header("👤 Your Personal Profile")
    st.caption(
        "Your profile controls your calorie targets, diet plan, "
        "automatic workouts and coach recommendations."
    )

    p = st.session_state.profile

    with st.container():
        c1, c2 = st.columns(2)

        with c1:
            age = st.number_input(
                "Age",
                min_value=13,
                max_value=100,
                value=int(p.get("age", 20)),
            )

            sex = st.selectbox(
                "Sex",
                ["Male", "Female"],
                index=0 if p.get("sex", "Male") == "Male" else 1,
            )

            height = st.number_input(
                "Height (cm)",
                min_value=100.0,
                max_value=230.0,
                value=float(p.get("height", 170)),
            )

            weight = st.number_input(
                "Weight (kg)",
                min_value=30.0,
                max_value=250.0,
                value=float(p.get("weight", 65)),
            )

        with c2:
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
                ].index(
                    p.get("activity", "Moderately Active")
                ),
            )

            diet = st.selectbox(
                "Diet preference",
                ["Vegetarian", "Vegan", "Non-vegetarian"],
                index=[
                    "Vegetarian",
                    "Vegan",
                    "Non-vegetarian",
                ].index(
                    p.get("diet", "Vegetarian")
                ),
            )

            budget = st.selectbox(
                "Food budget",
                ["Budget", "Moderate", "Flexible"],
                index=[
                    "Budget",
                    "Moderate",
                    "Flexible",
                ].index(
                    p.get("budget", "Budget")
                ),
            )

            body_type = st.selectbox(
                "Current body type",
                [
                    "Slim / Skinny",
                    "Skinny Fat",
                    "Average",
                    "Athletic",
                    "Muscular",
                    "Higher Body Fat",
                ],
                index=[
                    "Slim / Skinny",
                    "Skinny Fat",
                    "Average",
                    "Athletic",
                    "Muscular",
                    "Higher Body Fat",
                ].index(
                    p.get("body_type", "Average")
                ),
            )

    goal = st.selectbox(
        "🎯 Body goal",
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
        ].index(
            p.get("goal", "General Fitness")
        ),
    )

    if st.button(
        "💾 Save Profile & Calculate Targets",
        type="primary",
        use_container_width=True,
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
            age,
            sex,
            height,
            weight,
            activity,
            goal,
        )

        st.session_state.water_target = st.session_state.targets[
            "water_glasses"
        ]

        st.session_state.diet_plan = create_diet_plan(
            st.session_state.diet_cycle
        )

        st.success("Profile saved and personalized targets calculated.")
        st.rerun()

    if profile_ready():
        st.divider()

        st.subheader("🎯 Your calculated targets")

        t = st.session_state.targets

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Calories", f"{t['calories']} kcal")
        c2.metric("Protein", f"{t['protein']} g")
        c3.metric("Carbs", f"{t['carbs']} g")
        c4.metric("Fat", f"{t['fat']} g")

        c1, c2, c3 = st.columns(3)
        c1.metric("Fiber", f"{t['fiber']} g")
        c2.metric("Water", f"{t['water_liters']} L")
        c3.metric("BMR", f"{t['bmr']} kcal")

        st.info(
            "These are estimates for planning and tracking, not medical "
            "advice or an exact prescription."
        )

    # Personal diet calculator
    st.divider()
    st.subheader("🧮 Personal Diet Calculator")
    st.caption(
        "Ate something that wasn't in your plan? Calculate it here "
        "and add it to today's tracking."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        custom_food = st.text_input(
            "Food",
            placeholder="e.g. homemade paneer sandwich",
        )

    with c2:
        custom_calories = st.number_input(
            "Calories",
            min_value=0.0,
            value=0.0,
        )

    with c3:
        custom_protein = st.number_input(
            "Protein (g)",
            min_value=0.0,
            value=0.0,
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        custom_carbs = st.number_input(
            "Carbs (g)",
            min_value=0.0,
            value=0.0,
        )

    with c2:
        custom_fat = st.number_input(
            "Fat (g)",
            min_value=0.0,
            value=0.0,
        )

    with c3:
        custom_fiber = st.number_input(
            "Fiber (g)",
            min_value=0.0,
            value=0.0,
        )

    if st.button(
        "➕ Add Custom Food",
        use_container_width=True,
    ):
        if custom_food.strip():
            st.session_state.food_log.append({
                "name": custom_food,
                "meal": "Custom",
                "grams": 0,
                "calories": custom_calories,
                "protein": custom_protein,
                "carbs": custom_carbs,
                "fat": custom_fat,
                "fiber": custom_fiber,
                "vitamin_a": 0,
                "vitamin_c": 0,
                "vitamin_d": 0,
                "calcium": 0,
                "iron": 0,
                "magnesium": 0,
                "potassium": 0,
                "zinc": 0,
            })

            st.success("Added to today's food log.")
            st.rerun()


# =========================================================
# FOOD PAGE
# =========================================================

elif st.session_state.page == "Food":

    st.header("🍽️ Smart Food Tracker")
    st.caption(
        "Search → choose serving → see nutrition → add → immediately "
        "see how it changes today's targets."
    )

    if not profile_ready():
        st.warning(
            "Complete your profile first so NutriCoach can calculate "
            "your personal targets."
        )

    query = st.text_input(
        "🔎 Search USDA food",
        placeholder="Try egg, banana, rice, chicken, paneer...",
    )

    if st.button(
        "Search Food",
        type="primary",
        use_container_width=True,
    ) and query.strip():

        foods, error = search_usda(query)

        if error:
            st.error(error)
        elif not foods:
            st.warning("No USDA foods found.")
        else:
            st.session_state.search_results = foods

    if "search_results" in st.session_state:

        st.subheader("Search results")

        names = [
            f"{i+1}. {food.get('description', 'Unknown food')}"
            for i, food in enumerate(
                st.session_state.search_results
            )
        ]

        selected_name = st.selectbox(
            "Choose a food",
            names,
        )

        index = names.index(selected_name)

        food = st.session_state.search_results[index]
        nutrition = get_nutrients(food)

        st.markdown(
            f"""
            <div class="card">
                <h3>{food.get("description", "Food")}</h3>
                <span class="pill">USDA</span>
                <span class="pill">Nutrition estimate</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        unit = st.radio(
            "Serving type",
            ["grams", "pieces"],
            horizontal=True,
        )

        if unit == "grams":
            amount = st.number_input(
                "Amount (grams)",
                min_value=1.0,
                value=100.0,
            )
            grams = amount
        else:
            pieces = st.number_input(
                "Number of pieces",
                min_value=1.0,
                value=1.0,
            )

            grams = pieces * detect_piece_weight(
                food.get("description", "")
            )

            st.caption(
                f"Estimated serving weight: {grams:.0f}g"
            )

        multiplier = grams / 100

        calculated = {
            key: round(value * multiplier, 1)
            for key, value in nutrition.items()
        }

        st.subheader("Nutrition for this serving")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Calories",
            f"{calculated['calories']:.0f}",
        )

        c2.metric(
            "Protein",
            f"{calculated['protein']:.1f}g",
        )

        c3.metric(
            "Carbs",
            f"{calculated['carbs']:.1f}g",
        )

        c4.metric(
            "Fat",
            f"{calculated['fat']:.1f}g",
        )

        c5.metric(
            "Fiber",
            f"{calculated['fiber']:.1f}g",
        )

        if profile_ready():

            rem = remaining_targets()

            new_cal = max(
                0,
                rem["calories"] - calculated["calories"],
            )

            new_protein = max(
                0,
                rem["protein"] - calculated["protein"],
            )

            st.markdown(
                f"""
                <div class="coach">
                    <h3>⚡ What happens if you eat this?</h3>
                    <p>
                    Before eating: <b>{rem['calories']:.0f} kcal</b>
                    and <b>{rem['protein']:.1f}g protein</b> remaining.
                    </p>
                    <p>
                    After eating: about
                    <b>{new_cal:.0f} kcal</b> and
                    <b>{new_protein:.1f}g protein</b>
                    would remain.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        meal = st.selectbox(
            "Meal",
            ["Breakfast", "Lunch", "Snack", "Dinner", "Custom"],
        )

        if st.button(
            "➕ Add Food to Today",
            type="primary",
            use_container_width=True,
        ):

            entry = {
                "name": food.get(
                    "description",
                    "Unknown food",
                ),
                "meal": meal,
                "grams": grams,
                **calculated,
            }

            st.session_state.food_log.append(entry)

            st.success(
                "Added! Your remaining targets have been updated."
            )

            st.rerun()

    # Today's food
    st.divider()
    st.subheader("📋 Today's Food")

    if not st.session_state.food_log:
        st.info("Nothing logged yet.")
    else:

        totals = current_totals()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Calories",
            f"{totals['calories']:.0f}",
        )

        c2.metric(
            "Protein",
            f"{totals['protein']:.1f}g",
        )

        c3.metric(
            "Carbs",
            f"{totals['carbs']:.1f}g",
        )

        c4.metric(
            "Fiber",
            f"{totals['fiber']:.1f}g",
        )

        for i, item in enumerate(
            st.session_state.food_log
        ):

            with st.container():
                st.markdown(
                    f"""
                    <div class="meal">
                        <div class="meal-title">
                            {item['name']}
                        </div>
                        <div class="muted">
                            {item['meal']} · {item['grams']:.0f}g
                        </div>
                        <br>
                        {item['calories']:.0f} kcal ·
                        {item['protein']:.1f}g protein ·
                        {item['carbs']:.1f}g carbs ·
                        {item['fat']:.1f}g fat
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    "Remove",
                    key=f"remove_food_{i}",
                ):
                    st.session_state.food_log.pop(i)
                    st.rerun()


# =========================================================
# TODAY PAGE
# =========================================================

elif st.session_state.page == "Today":

    if not profile_ready():

        st.markdown(
            """
            <div class="coach">
                <h2>👋 Welcome to NutriCoach</h2>
                <p>
                Let's personalize your nutrition and training.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "🚀 Set Up My Profile",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.page = "Profile"
            st.rerun()

    else:

        p = st.session_state.profile
        t = st.session_state.targets
        totals = current_totals()

        st.markdown(
            f"""
            <div class="card">
                <h2>Good to see you 👋</h2>
                <p class="muted">
                Goal: <b>{p['goal']}</b> ·
                {p['diet']} ·
                {p['body_type']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Coach centerpiece
        st.markdown(
            f"""
            <div class="coach">
                <h2>🧠 Your next best action</h2>
                <p>{coach_recommendation()}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.subheader("🔥 Today's nutrition")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Calories",
            f"{totals['calories']:.0f} / {t['calories']}",
        )

        c2.metric(
            "Protein",
            f"{totals['protein']:.0f} / {t['protein']:.0f}g",
        )

        c3.metric(
            "Carbs",
            f"{totals['carbs']:.0f} / {t['carbs']:.0f}g",
        )

        c4.metric(
            "Fiber",
            f"{totals['fiber']:.0f} / {t['fiber']:.0f}g",
        )

        st.progress(
            percent(
                totals["calories"],
                t["calories"],
            ) / 100
        )

        st.caption(
            f"{remaining_targets()['calories']:.0f} kcal remaining"
        )

        # Water
        st.subheader("💧 Hydration")

        water_percent = min(
            100,
            st.session_state.water_glasses
            / max(1, st.session_state.water_target)
            * 100,
        )

        st.progress(water_percent / 100)

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Today",
            f"{st.session_state.water_glasses} glasses",
        )

        c2.metric(
            "Target",
            f"{st.session_state.water_target} glasses",
        )

        with c3:
            if st.button(
                "💧 Add Glass",
                use_container_width=True,
            ):
                st.session_state.water_glasses += 1
                st.rerun()

        # Automatic workout
        st.subheader("🏋️ Today's automatic workout")

        workout = generate_workout()

        name, duration, intensity = workout

        calories_burned = estimated_workout_calories(
            duration,
            p["weight"],
            intensity,
        )

        st.markdown(
            f"""
            <div class="card">
                <h3>{name}</h3>
                <p>
                    ⏱️ {duration} minutes ·
                    🔥 ~{calories_burned} kcal ·
                    ⚡ {intensity}
                </p>
                <p class="muted">
                    Automatically selected from your profile and goal.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "✅ Mark Workout Complete",
            use_container_width=True,
        ):
            st.session_state.workout_history.append({
                "date": today_string(),
                "workout": name,
                "minutes": duration,
                "calories": calories_burned,
            })

            st.success("Workout recorded!")
            st.rerun()

        # Quick actions
        st.subheader("⚡ Quick actions")

        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button(
                "🍽️ Log Food",
                use_container_width=True,
            ):
                st.session_state.page = "Food"
                st.rerun()

        with c2:
            if st.button(
                "🍱 View Diet",
                use_container_width=True,
            ):
                st.session_state.show_diet = True

        with c3:
            if st.button(
                "📸 Body Scan",
                use_container_width=True,
            ):
                st.session_state.show_scan = True

        # Diet panel
        if st.session_state.get("show_diet", False):

            st.divider()
            st.subheader("🍱 Today's planned meals")

            if not st.session_state.diet_plan:
                st.session_state.diet_plan = create_diet_plan(
                    st.session_state.diet_cycle
                )

            today_plan = st.session_state.diet_plan[
                date.today().day % 14
            ]

            for meal, food in today_plan["meals"]:
                st.markdown(
                    f"""
                    <div class="meal">
                        <div class="meal-title">
                            {meal}
                        </div>
                        {food}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# =========================================================
# WORKOUT PAGE
# =========================================================

elif st.session_state.page == "Workout":

    st.header("🏋️ Automatic Workout")
    st.caption(
        "No exercise selection required. NutriCoach generates the "
        "session from your profile."
    )

    if not profile_ready():
        st.warning("Complete your profile first.")
    else:

        p = st.session_state.profile
        name, duration, intensity = generate_workout()

        calories = estimated_workout_calories(
            duration,
            p["weight"],
            intensity,
        )

        st.markdown(
            f"""
            <div class="coach">
                <h2>Today's session</h2>
                <h1>{name}</h1>
                <p>
                    ⏱️ {duration} min ·
                    🔥 ~{calories} kcal ·
                    ⚡ {intensity}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.subheader("Workout structure")

        if "Calisthenics" in name:
            exercises = [
                "Warm-up — 5 min",
                "Push-ups — 3 sets",
                "Bodyweight squats — 3 sets",
                "Rows / assisted rows — 3 sets",
                "Lunges — 3 sets",
                "Plank — 3 sets",
                "Cool-down — 5 min",
            ]

        elif "Strength" in name:
            exercises = [
                "Warm-up — 5 min",
                "Squat pattern — 3 sets",
                "Push pattern — 3 sets",
                "Pull pattern — 3 sets",
                "Hip hinge — 3 sets",
                "Core — 3 sets",
                "Cool-down — 5 min",
            ]

        elif "Walk" in name:
            exercises = [
                "Brisk walk — 25 min",
                "Hip mobility — 5 min",
                "Shoulder mobility — 5 min",
                "Breathing / cool-down — 5 min",
            ]

        else:
            exercises = [
                "Warm-up — 5 min",
                "Squat pattern — 3 sets",
                "Push-ups — 3 sets",
                "Rows — 3 sets",
                "Lunges — 3 sets",
                "Core — 3 sets",
                "Cool-down — 5 min",
            ]

        for exercise in exercises:
            st.checkbox(
                exercise,
                key=f"exercise_{exercise}",
            )

        if st.button(
            "🏁 Complete Today's Workout",
            type="primary",
            use_container_width=True,
        ):

            st.session_state.workout_history.append({
                "date": today_string(),
                "workout": name,
                "minutes": duration,
                "calories": calories,
            })

            st.success(
                "Workout complete. Great job!"
            )


# =========================================================
# PROGRESS PAGE
# =========================================================

elif st.session_state.page == "Progress":

    st.header("📊 Body Progress")
    st.caption(
        "Track measurements, nutrition, hydration, workouts and photos."
    )

    if profile_ready():

        p = st.session_state.profile

        st.subheader("📏 Today's measurements")

        c1, c2 = st.columns(2)

        with c1:
            current_weight = st.number_input(
                "Weight (kg)",
                min_value=30.0,
                max_value=250.0,
                value=float(p["weight"]),
            )

        with c2:
            waist = st.number_input(
                "Waist (cm)",
                min_value=30.0,
                max_value=200.0,
                value=80.0,
            )

        c1, c2, c3 = st.columns(3)

        with c1:
            chest = st.number_input(
                "Chest (cm)",
                min_value=40.0,
                max_value=200.0,
                value=90.0,
            )

        with c2:
            arms = st.number_input(
                "Arms (cm)",
                min_value=10.0,
                max_value=100.0,
                value=30.0,
            )

        with c3:
            legs = st.number_input(
                "Legs (cm)",
                min_value=20.0,
                max_value=120.0,
                value=50.0,
            )

        if st.button(
            "📌 Save Measurements",
            type="primary",
            use_container_width=True,
        ):

            st.session_state.weight_history.append({
                "date": today_string(),
                "weight": current_weight,
            })

            st.session_state.waist_history.append({
                "date": today_string(),
                "waist": waist,
            })

            st.success("Progress saved.")

        st.divider()

        # Weight chart
        if st.session_state.weight_history:

            st.subheader("⚖️ Weight trend")

            df_weight = pd.DataFrame(
                st.session_state.weight_history
            )

            df_weight["date"] = pd.to_datetime(
                df_weight["date"]
            )

            df_weight = df_weight.drop_duplicates(
                subset=["date"],
                keep="last",
            )

            st.line_chart(
                df_weight.set_index("date")["weight"]
            )

        # Waist chart
        if st.session_state.waist_history:

            st.subheader("📐 Waist trend")

            df_waist = pd.DataFrame(
                st.session_state.waist_history
            )

            df_waist["date"] = pd.to_datetime(
                df_waist["date"]
            )

            df_waist = df_waist.drop_duplicates(
                subset=["date"],
                keep="last",
            )

            st.line_chart(
                df_waist.set_index("date")["waist"]
            )

        # Nutrition chart
        st.subheader("🥗 Today's nutrition vs target")

        totals = current_totals()
        targets = st.session_state.targets

        nutrition_df = pd.DataFrame({
            "Consumed": [
                totals["calories"],
                totals["protein"],
                totals["carbs"],
                totals["fat"],
                totals["fiber"],
            ],
            "Target": [
                targets["calories"],
                targets["protein"],
                targets["carbs"],
                targets["fat"],
                targets["fiber"],
            ],
        }, index=[
            "Calories",
            "Protein",
            "Carbs",
            "Fat",
            "Fiber",
        ])

        st.bar_chart(nutrition_df)

        # Workout history
        st.subheader("🏋️ Workout history")

        if st.session_state.workout_history:

            workout_df = pd.DataFrame(
                st.session_state.workout_history
            )

            workout_df["date"] = pd.to_datetime(
                workout_df["date"]
            )

            st.bar_chart(
                workout_df.set_index("date")["minutes"]
            )

            st.dataframe(
                workout_df,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info("Complete your first workout to see your history.")

        # Body scan
        st.divider()
        st.subheader("📸 Body Scan")

        st.info(
            "The camera feature below captures progress photos. "
            "A normal phone/laptop camera cannot reliably determine "
            "exact body measurements in centimeters without calibration. "
            "NutriCoach therefore presents proportions and photo progress "
            "as estimates rather than pretending they are exact."
        )

        photo_type = st.selectbox(
            "Photo angle",
            ["Front", "Side", "Back"],
        )

        photo = st.camera_input(
            f"Capture {photo_type} photo"
        )

        if photo is not None:
            st.session_state.body_photos[
                photo_type
            ] = photo

            st.success(
                f"{photo_type} photo captured."
            )

        if st.session_state.body_photos:

            st.subheader("Your progress photos")

            cols = st.columns(
                len(st.session_state.body_photos)
            )

            for col, (angle, image) in zip(
                cols,
                st.session_state.body_photos.items(),
            ):
                with col:
                    st.image(
                        image,
                        caption=angle,
                        use_container_width=True,
                    )

        st.caption(
            "For more accurate measurement tracking, enter your actual "
            "tape measurements above. Camera-based estimates are not "
            "a substitute for calibrated measurement."
        )

    else:
        st.warning("Complete your profile to start tracking progress.")


# =========================================================
# DIET / SECONDARY FEATURE
# =========================================================

# Diet is intentionally accessible from the Today page.
# This keeps the primary navigation limited to five mobile tabs.

if (
    st.session_state.page == "Today"
    and profile_ready()
    and st.session_state.get("show_diet", False)
):

    st.divider()
    st.header("🍱 Your 14-Day Diet Plan")

    if not st.session_state.diet_plan:
        st.session_state.diet_plan = create_diet_plan(
            st.session_state.diet_cycle
        )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "🔄 Generate New 14 Days",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.diet_cycle += 1
            st.session_state.diet_plan = create_diet_plan(
                st.session_state.diet_cycle
            )
            st.rerun()

    with c2:
        st.info(
            f"Cycle {st.session_state.diet_cycle}"
        )

    for day_index, day in enumerate(
        st.session_state.diet_plan
    ):

        with st.expander(
            f"Day {day['day']} · {day['note']}"
        ):

            for meal_index, (meal, food) in enumerate(
                day["meals"]
            ):

                st.markdown(
                    f"""
                    <div class="meal">
                        <div class="meal-title">
                            {meal}
                        </div>
                        {food}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    "🔁 Swap Meal",
                    key=f"swap_{day_index}_{meal_index}",
                ):
                    swap_meal(
                        day_index,
                        meal_index,
                    )
                    st.rerun()


# =========================================================
# FINAL SAFETY / FOOTER
# =========================================================

st.divider()

st.caption(
    "NutriCoach MVP · Nutrition values are estimates from USDA data. "
    "Body measurements and calorie targets should be treated as "
    "planning estimates, not medical advice."
)
