import streamlit as st
import requests
from datetime import date

st.set_page_config(
    page_title="NutriCoach",
    page_icon="🥗",
    layout="wide"
)

st.title("🥗 NutriCoach")
st.caption("Your AI Nutrition & Body Progress Coach")

# =========================================================
# SESSION STATE
# =========================================================

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "food_log" not in st.session_state:
    st.session_state.food_log = []

if "water" not in st.session_state:
    st.session_state.water = 0

if "completed_meals" not in st.session_state:
    st.session_state.completed_meals = set()

# =========================================================
# CALCULATOR
# =========================================================

def calculate_targets(age, sex, height, weight, activity, goal):

    if sex == "Male":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    activity_factors = {
        "Sedentary": 1.20,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725
    }

    tdee = bmr * activity_factors[activity]

    adjustments = {
        "General Fitness": 0,
        "Calisthenics": 100,
        "Greek Body": -100,
        "Aesthetic Body": -100,
        "Muscle Gain": 250,
        "Fat Loss": -400,
        "Strength": 250,
        "Recomposition": -150
    }

    calories = tdee + adjustments[goal]

    if goal in ["Muscle Gain", "Strength", "Calisthenics"]:
        protein = weight * 1.8
    elif goal in [
        "Fat Loss",
        "Recomposition",
        "Greek Body",
        "Aesthetic Body"
    ]:
        protein = weight * 1.7
    else:
        protein = weight * 1.6

    fat = weight * 0.8

    carbs = (
        calories -
        protein * 4 -
        fat * 9
    ) / 4

    fiber = calories / 1000 * 14
    water = weight * 35

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": max(round(calories), 1200),
        "protein": round(protein),
        "carbs": max(round(carbs), 50),
        "fat": round(fat),
        "fiber": round(fiber),
        "water": round(water)
    }

# =========================================================
# USDA
# =========================================================

def search_usda(food_name, api_key):

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {
        "api_key": api_key,
        "query": food_name,
        "pageSize": 8
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            return []

        return response.json().get("foods", [])

    except Exception:
        return []


def get_nutrient(food, name):

    for nutrient in food.get("foodNutrients", []):

        if nutrient.get("nutrientName", "").lower() == name.lower():
            return nutrient.get("value", 0)

    return 0


def get_food_nutrition(food):

    return {
        "calories": get_nutrient(food, "Energy"),
        "protein": get_nutrient(food, "Protein"),
        "carbs": get_nutrient(
            food,
            "Carbohydrate, by difference"
        ),
        "fat": get_nutrient(
            food,
            "Total lipid (fat)"
        ),
        "fiber": get_nutrient(
            food,
            "Fiber, total dietary"
        ),
        "calcium": get_nutrient(
            food,
            "Calcium, Ca"
        ),
        "iron": get_nutrient(
            food,
            "Iron, Fe"
        ),
        "magnesium": get_nutrient(
            food,
            "Magnesium, Mg"
        ),
        "potassium": get_nutrient(
            food,
            "Potassium, K"
        ),
        "zinc": get_nutrient(
            food,
            "Zinc, Zn"
        ),
        "vitamin_a": get_nutrient(
            food,
            "Vitamin A, RAE"
        ),
        "vitamin_c": get_nutrient(
            food,
            "Vitamin C, total ascorbic acid"
        ),
        "vitamin_d": get_nutrient(
            food,
            "Vitamin D (D2 + D3)"
        )
    }


def scale_nutrition(nutrition, grams):

    multiplier = grams / 100

    return {
        key: round(value * multiplier, 2)
        for key, value in nutrition.items()
    }

# =========================================================
# DIET DATABASE
# =========================================================

MEALS = {

    "Vegetarian": {

        "Breakfast": [
            "Oats + milk + banana",
            "Vegetable poha + curd",
            "Paneer paratha + curd",
            "Besan chilla + curd",
            "Idli + sambar",
            "Vegetable upma + milk",
            "Moong dal chilla + curd",
            "Oats + peanut butter + banana",
            "Paneer sandwich",
            "Dalia + milk + fruit",
            "Stuffed roti + curd",
            "Sprouts chaat + toast",
            "Vegetable dosa + sambar",
            "Peanut butter toast + milk"
        ],

        "Lunch": [
            "Rice + dal + vegetables + curd",
            "Roti + paneer + salad",
            "Rajma rice + salad",
            "Chole + roti + curd",
            "Dal khichdi + curd",
            "Roti + dal + mixed vegetables",
            "Paneer rice bowl + salad",
            "Rajma roti + vegetables",
            "Chole rice + salad",
            "Dal + rice + paneer",
            "Roti + soy chunks + vegetables",
            "Vegetable pulao + curd",
            "Dal + roti + paneer",
            "Rice + soy chunks + salad"
        ],

        "Snack": [
            "Banana + peanuts",
            "Roasted chana",
            "Curd + fruit",
            "Peanut butter toast",
            "Sprouts chaat",
            "Milk + banana",
            "Peanuts + fruit",
            "Roasted makhana",
            "Curd + banana",
            "Chana chaat",
            "Milk + oats",
            "Peanut chaat",
            "Fruit + curd",
            "Roasted chana + fruit"
        ],

        "Dinner": [
            "Roti + paneer + vegetables",
            "Dal + rice + salad",
            "Roti + soy chunks + vegetables",
            "Paneer bhurji + roti",
            "Khichdi + curd",
            "Roti + dal + vegetables",
            "Paneer rice bowl",
            "Chole + roti + salad",
            "Rajma + rice",
            "Soy chunks pulao",
            "Dal + paneer + roti",
            "Vegetable khichdi + curd",
            "Roti + paneer tikka + salad",
            "Dal + rice + vegetables"
        ]
    },

    "Vegan": {

        "Breakfast": [
            "Oats + soy milk + banana",
            "Vegetable poha",
            "Besan chilla",
            "Moong dal chilla",
            "Idli + sambar",
            "Vegan oats + peanut butter",
            "Dalia + soy milk",
            "Peanut butter toast + banana",
            "Sprouts chaat + toast",
            "Vegetable upma",
            "Chana chaat + toast",
            "Oats + banana + peanuts",
            "Vegetable dosa + sambar",
            "Poha + peanuts"
        ],

        "Lunch": [
            "Rice + dal + vegetables",
            "Roti + soy chunks + salad",
            "Rajma rice",
            "Chole + roti",
            "Dal khichdi",
            "Roti + dal + vegetables",
            "Soy chunk rice bowl",
            "Rajma roti",
            "Chole rice",
            "Dal + rice + soy chunks",
            "Roti + chana + vegetables",
            "Vegetable pulao + dal",
            "Dal + roti + soy chunks",
            "Rice + chickpeas + salad"
        ],

        "Snack": [
            "Banana + peanuts",
            "Roasted chana",
            "Fruit + peanuts",
            "Peanut butter toast",
            "Sprouts chaat",
            "Banana + peanut butter",
            "Roasted makhana",
            "Chana chaat",
            "Peanuts + fruit",
            "Soy milk + banana",
            "Roasted chana + fruit",
            "Peanut chaat",
            "Sprouts + fruit",
            "Banana + peanuts"
        ],

        "Dinner": [
            "Roti + soy chunks + vegetables",
            "Dal + rice + salad",
            "Chole + roti",
            "Soy chunk pulao",
            "Khichdi + vegetables",
            "Roti + dal + vegetables",
            "Rajma rice",
            "Chana + roti",
            "Soy chunk rice bowl",
            "Dal + roti + vegetables",
            "Chole rice",
            "Vegetable khichdi",
            "Roti + soy chunks",
            "Dal + rice + vegetables"
        ]
    },

    "Non-Vegetarian": {

        "Breakfast": [
            "Oats + milk + banana",
            "Eggs + toast + fruit",
            "Egg bhurji + roti",
            "Omelette + toast",
            "Oats + peanut butter + banana",
            "Egg sandwich",
            "Eggs + roti + fruit",
            "Dalia + eggs",
            "Paneer + eggs + roti",
            "Oats + milk + fruit",
            "Egg bhurji + toast",
            "Boiled eggs + banana + toast",
            "Omelette + roti",
            "Egg sandwich + milk"
        ],

        "Lunch": [
            "Chicken + rice + vegetables",
            "Chicken + roti + salad",
            "Egg curry + rice",
            "Chicken pulao + salad",
            "Dal + chicken + roti",
            "Chicken rice bowl",
            "Egg curry + roti",
            "Chicken + rice + dal",
            "Chicken + roti + vegetables",
            "Egg fried rice",
            "Chicken pulao",
            "Chicken + dal + rice",
            "Egg curry + rice + salad",
            "Chicken + roti + curd"
        ],

        "Snack": [
            "Boiled eggs + fruit",
            "Banana + peanuts",
            "Curd + fruit",
            "Peanut butter toast",
            "Roasted chana",
            "Egg sandwich",
            "Milk + banana",
            "Boiled eggs",
            "Fruit + peanuts",
            "Chicken sandwich",
            "Curd + banana",
            "Roasted chana + fruit",
            "Eggs + toast",
            "Milk + oats"
        ],

        "Dinner": [
            "Chicken + roti + vegetables",
            "Chicken + rice + salad",
            "Egg curry + roti",
            "Chicken pulao",
            "Chicken + dal + rice",
            "Chicken + roti + vegetables",
            "Egg bhurji + roti",
            "Chicken rice bowl",
            "Chicken curry + rice",
            "Egg curry + rice",
            "Chicken + dal + roti",
            "Chicken pulao + salad",
            "Egg curry + roti",
            "Chicken + rice + vegetables"
        ]
    }
}

# =========================================================
# NAVIGATION
# =========================================================

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "👤 Profile",
        "🍽️ Food",
        "📋 Diet Plan",
        "💧 Water",
        "📊 Progress"
    ]
)

# =========================================================
# HOME
# =========================================================

if page == "🏠 Home":

    st.header("🏠 Today's Dashboard")

    if not st.session_state.profile:

        st.info(
            "Create your profile first to unlock "
            "personalized nutrition targets."
        )

    else:

        profile = st.session_state.profile
        targets = profile["targets"]

        calories = sum(
            x["calories"]
            for x in st.session_state.food_log
        )

        protein = sum(
            x["protein"]
            for x in st.session_state.food_log
        )

        carbs = sum(
            x["carbs"]
            for x in st.session_state.food_log
        )

        fat = sum(
            x["fat"]
            for x in st.session_state.food_log
        )

        fiber = sum(
            x["fiber"]
            for x in st.session_state.food_log
        )

        st.subheader(
            f"🎯 Goal: {profile['goal']}"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Calories",
            f"{calories:.0f} / {targets['calories']}"
        )

        c2.metric(
            "Protein",
            f"{protein:.1f} / {targets['protein']}g"
        )

        c3.metric(
            "Carbs",
            f"{carbs:.1f} / {targets['carbs']}g"
        )

        c4.metric(
            "Fat",
            f"{fat:.1f} / {targets['fat']}g"
        )

        c5.metric(
            "Fiber",
            f"{fiber:.1f} / {targets['fiber']}g"
        )

        st.divider()

        st.subheader("💧 Water")

        st.progress(
            min(
                st.session_state.water /
                targets["water"],
                1.0
            )
        )

        st.write(
            f"{st.session_state.water} / "
            f"{targets['water']} ml"
        )

        st.divider()

        st.subheader("🤖 NutriCoach Recommendation")

        remaining_protein = targets["protein"] - protein
        remaining_calories = targets["calories"] - calories

        if remaining_protein > 30:

            st.info(
                f"You still need approximately "
                f"**{remaining_protein:.0f}g protein** today. "
                "Consider eggs, curd, paneer, tofu, soy chunks, "
                "dal or chicken depending on your diet."
            )

        elif remaining_calories > 300:

            st.info(
                f"You have approximately "
                f"**{remaining_calories:.0f} kcal** remaining today. "
                "Choose a balanced meal with protein, vegetables "
                "and a carbohydrate source."
            )

        else:

            st.success(
                "Your nutrition intake is getting close "
                "to today's target. 🎉"
            )

# =========================================================
# PROFILE
# =========================================================

elif page == "👤 Profile":

    st.header("👤 Personal Profile")

    col1, col2 = st.columns(2)

    with col1:

        age = st.number_input(
            "Age",
            13,
            100,
            20
        )

        sex = st.selectbox(
            "Sex",
            ["Male", "Female"]
        )

        height = st.number_input(
            "Height (cm)",
            100.0,
            230.0,
            170.0
        )

        weight = st.number_input(
            "Weight (kg)",
            30.0,
            250.0,
            65.0
        )

        activity = st.selectbox(
            "Activity Level",
            [
                "Sedentary",
                "Lightly Active",
                "Moderately Active",
                "Very Active"
            ]
        )

    with col2:

        diet = st.selectbox(
            "Diet Preference",
            [
                "Non-Vegetarian",
                "Vegetarian",
                "Vegan"
            ]
        )

        budget = st.selectbox(
            "Food Budget",
            [
                "Low",
                "Medium",
                "High"
            ]
        )

        body_type = st.selectbox(
            "Current Body Type",
            [
                "Slim / Skinny",
                "Skinny Fat",
                "Average",
                "Athletic",
                "Muscular",
                "Higher Body Fat"
            ]
        )

        goal = st.selectbox(
            "Body Goal",
            [
                "General Fitness",
                "Calisthenics",
                "Greek Body",
                "Aesthetic Body",
                "Muscle Gain",
                "Fat Loss",
                "Strength",
                "Recomposition"
            ]
        )

    if st.button(
        "💾 Save Profile",
        type="primary"
    ):

        targets = calculate_targets(
            age,
            sex,
            height,
            weight,
            activity,
            goal
        )

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
            "targets": targets
        }

        st.success("Profile saved! 🎉")

        st.subheader("🎯 Your Targets")

        a, b, c, d = st.columns(4)

        a.metric(
            "Calories",
            f"{targets['calories']} kcal"
        )

        b.metric(
            "Protein",
            f"{targets['protein']} g"
        )

        c.metric(
            "Carbs",
            f"{targets['carbs']} g"
        )

        d.metric(
            "Fat",
            f"{targets['fat']} g"
        )

        st.write(
            f"Fiber: **{targets['fiber']} g/day**"
        )

        st.write(
            f"Water: approximately **{targets['water']} ml/day**"
        )

        st.caption(
            "These values are estimates for general fitness "
            "planning."
        )

# =========================================================
# FOOD
# =========================================================

elif page == "🍽️ Food":

    st.header("🍽️ Food Tracker")

    try:
        api_key = st.secrets["FDC_API_KEY"]
    except Exception:
        api_key = ""

    if not api_key:

        st.warning(
            "USDA API key is not configured."
        )

    food_name = st.text_input(
        "🔎 Search USDA FoodData Central",
        placeholder="egg, rice, chicken breast..."
    )

    if st.button("🔍 Search"):

        if not food_name:

            st.warning("Enter a food name.")

        elif not api_key:

            st.error(
                "USDA API key is missing."
            )

        else:

            results = search_usda(
                food_name,
                api_key
            )

            if results:

                st.session_state.usda_results = results

                st.success(
                    f"Found {len(results)} results."
                )

            else:

                st.error(
                    "No results found."
                )

    if "usda_results" in st.session_state:

        results = st.session_state.usda_results

        options = [
            f"{x.get('description', 'Food')} "
            f"({x.get('dataType', '')})"
            for x in results
        ]

        selected = st.selectbox(
            "Select the exact food",
            range(len(options)),
            format_func=lambda x: options[x]
        )

        food = results[selected]

        nutrition = get_food_nutrition(food)

        st.subheader("Nutrition per 100g")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Calories",
            f"{nutrition['calories']:.0f}"
        )

        c2.metric(
            "Protein",
            f"{nutrition['protein']:.1f}g"
        )

        c3.metric(
            "Carbs",
            f"{nutrition['carbs']:.1f}g"
        )

        c4.metric(
            "Fat",
            f"{nutrition['fat']:.1f}g"
        )

        c5.metric(
            "Fiber",
            f"{nutrition['fiber']:.1f}g"
        )

        quantity_type = st.radio(
            "Quantity",
            ["Grams", "Pieces"],
            horizontal=True
        )

        if quantity_type == "Grams":

            grams = st.number_input(
                "Amount (grams)",
                1.0,
                5000.0,
                100.0
            )

        else:

            pieces = st.number_input(
                "Number of pieces",
                1,
                100,
                1
            )

            food_lower = food_name.lower()

            piece_weights = {
                "egg": 50,
                "banana": 118,
                "apple": 182,
                "orange": 130,
                "roti": 40,
                "chapati": 40
            }

            grams_per_piece = 100

            for key, value in piece_weights.items():

                if key in food_lower:

                    grams_per_piece = value
                    break

            grams = pieces * grams_per_piece

            st.info(
                f"Estimated {grams_per_piece}g per piece "
                f"→ {grams}g total."
            )

        meal = st.selectbox(
            "Meal",
            [
                "Breakfast",
                "Lunch",
                "Snack",
                "Dinner"
            ]
        )

        scaled = scale_nutrition(
            nutrition,
            grams
        )

        st.subheader("Your Amount")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Calories",
            f"{scaled['calories']:.0f}"
        )

        c2.metric(
            "Protein",
            f"{scaled['protein']:.1f}g"
        )

        c3.metric(
            "Carbs",
            f"{scaled['carbs']:.1f}g"
        )

        c4.metric(
            "Fat",
            f"{scaled['fat']:.1f}g"
        )

        if st.button(
            "➕ Add to Today's Log",
            type="primary"
        ):

            st.session_state.food_log.append({
                "name": food.get(
                    "description",
                    food_name
                ),
                "meal": meal,
                "grams": grams,
                "calories": scaled["calories"],
                "protein": scaled["protein"],
                "carbs": scaled["carbs"],
                "fat": scaled["fat"],
                "fiber": scaled["fiber"]
            })

            st.success(
                "Food added! ✅"
            )

    st.divider()

    st.subheader("📋 Today's Food Log")

    if not st.session_state.food_log:

        st.info("No food logged yet.")

    else:

        for i, item in enumerate(
            st.session_state.food_log
        ):

            st.write(
                f"**{item['name']}** — "
                f"{item['meal']} — "
                f"{item['grams']:.0f}g"
            )

            st.caption(
                f"{item['calories']:.0f} kcal | "
                f"P {item['protein']:.1f}g | "
                f"C {item['carbs']:.1f}g | "
                f"F {item['fat']:.1f}g"
            )

            if st.button(
                "🗑️ Remove",
                key=f"remove_{i}"
            ):

                st.session_state.food_log.pop(i)
                st.rerun()

# =========================================================
# 14 DAY DIET PLAN
# =========================================================

elif page == "📋 Diet Plan":

    st.header("📋 14-Day Diet Plan")

    if not st.session_state.profile:

        st.warning(
            "Create your profile first."
        )

    else:

        profile = st.session_state.profile

        diet = profile["diet"]
        budget = profile["budget"]
        goal = profile["goal"]

        st.write(
            f"**Goal:** {goal}  |  "
            f"**Diet:** {diet}  |  "
            f"**Budget:** {budget}"
        )

        st.info(
            "Meals are examples for planning. "
            "Portions should be adjusted to your individual "
            "nutrition targets."
        )

        for day in range(1, 15):

            st.subheader(f"📅 Day {day}")

            day_number = day - 1

            breakfast = MEALS[diet]["Breakfast"][
                day_number
            ]

            lunch = MEALS[diet]["Lunch"][
                day_number
            ]

            snack = MEALS[diet]["Snack"][
                day_number
            ]

            dinner = MEALS[diet]["Dinner"][
                day_number
            ]

            meals = [
                ("Breakfast", breakfast),
                ("Lunch", lunch),
                ("Snack", snack),
                ("Dinner", dinner)
            ]

            for meal_name, meal in meals:

                key = f"day{day}_{meal_name}"

                checked = key in st.session_state.completed_meals

                new_value = st.checkbox(
                    f"{meal_name}: {meal}",
                    value=checked,
                    key=key
                )

                if new_value:
                    st.session_state.completed_meals.add(key)
                else:
                    st.session_state.completed_meals.discard(key)

            st.divider()

# =========================================================
# WATER
# =========================================================

elif page == "💧 Water":

    st.header("💧 Water Tracker")

    if not st.session_state.profile:

        st.warning(
            "Create your profile first."
        )

    else:

        target = st.session_state.profile[
            "targets"
        ]["water"]

        st.metric(
            "Daily Target",
            f"{target} ml"
        )

        st.metric(
            "Consumed",
            f"{st.session_state.water} ml"
        )

        st.progress(
            min(
                st.session_state.water / target,
                1.0
            )
        )

        st.subheader("🥤 Add Water")

        c1, c2, c3, c4 = st.columns(4)

        if c1.button("🥛 250 ml"):
            st.session_state.water += 250
            st.rerun()

        if c2.button("🥤 500 ml"):
            st.session_state.water += 500
            st.rerun()

        if c3.button("💧 750 ml"):
            st.session_state.water += 750
            st.rerun()

        if c4.button("🫗 1000 ml"):
            st.session_state.water += 1000
            st.rerun()

        if st.button("Reset"):

            st.session_state.water = 0
            st.rerun()

# =========================================================
# PROGRESS
# =========================================================

elif page == "📊 Progress":

    st.header("📊 Body Progress")

    st.write(
        "Track your measurements over time."
    )

    weight = st.number_input(
        "Weight (kg)",
        20.0,
        300.0,
        65.0
    )

    waist = st.number_input(
        "Waist (cm)",
        30.0,
        200.0,
        80.0
    )

    chest = st.number_input(
        "Chest (cm)",
        30.0,
        200.0,
        90.0
    )

    arms = st.number_input(
        "Arms (cm)",
        10.0,
        100.0,
        30.0
    )

    legs = st.number_input(
        "Legs (cm)",
        20.0,
        150.0,
        50.0
    )

    if st.button(
        "💾 Save Progress",
        type="primary"
    ):

        if "progress" not in st.session_state:
            st.session_state.progress = []

        st.session_state.progress.append({
            "date": str(date.today()),
            "weight": weight,
            "waist": waist,
            "chest": chest,
            "arms": arms,
            "legs": legs
        })

        st.success(
            "Progress saved! 📈"
        )

    if "progress" in st.session_state:

        st.subheader("History")

        for item in reversed(
            st.session_state.progress
        ):

            st.write(
                f"**{item['date']}** | "
                f"Weight {item['weight']} kg | "
                f"Waist {item['waist']} cm | "
                f"Chest {item['chest']} cm | "
                f"Arms {item['arms']} cm | "
                f"Legs {item['legs']} cm"
            )

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🥗 NutriCoach — Nutrition estimates are intended "
    "for general fitness planning."
)
