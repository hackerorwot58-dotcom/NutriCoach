import streamlit as st
import requests
from datetime import date

# =========================================================
# PAGE SETUP
# =========================================================

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

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def calculate_targets(age, sex, height, weight, activity, goal):
    """Calculate estimated daily calorie and macro targets."""

    # Mifflin-St Jeor BMR
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

    goal_adjustments = {
        "General Fitness": 0,
        "Calisthenics": 100,
        "Greek Body": -100,
        "Aesthetic Body": -100,
        "Muscle Gain": 250,
        "Fat Loss": -400,
        "Strength": 250,
        "Recomposition": -150
    }

    calories = tdee + goal_adjustments[goal]

    # Protein target
    if goal in ["Muscle Gain", "Strength", "Calisthenics"]:
        protein = weight * 1.8
    elif goal in ["Fat Loss", "Recomposition", "Greek Body", "Aesthetic Body"]:
        protein = weight * 1.7
    else:
        protein = weight * 1.6

    fat = weight * 0.8

    # Calories remaining for carbohydrates
    carbs = (calories - (protein * 4) - (fat * 9)) / 4

    # Fiber
    fiber = calories / 1000 * 14

    # Water
    water_ml = weight * 35

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": max(round(calories), 1200),
        "protein": round(protein),
        "carbs": max(round(carbs), 50),
        "fat": round(fat),
        "fiber": round(fiber),
        "water": round(water_ml)
    }


def search_usda(food_name, api_key):
    """Search USDA FoodData Central."""

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {
        "api_key": api_key,
        "query": food_name,
        "pageSize": 8
    }

    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return []

        data = response.json()
        return data.get("foods", [])

    except Exception:
        return []


def get_nutrient(food, nutrient_name):
    """Get a nutrient from a USDA food result."""

    for nutrient in food.get("foodNutrients", []):
        name = nutrient.get("nutrientName", "")

        if name.lower() == nutrient_name.lower():
            return nutrient.get("value", 0)

    return 0


def get_food_nutrition(food):
    """Extract nutrition information."""

    return {
        "calories": get_nutrient(food, "Energy"),
        "protein": get_nutrient(food, "Protein"),
        "carbs": get_nutrient(food, "Carbohydrate, by difference"),
        "fat": get_nutrient(food, "Total lipid (fat)"),
        "fiber": get_nutrient(food, "Fiber, total dietary"),
        "calcium": get_nutrient(food, "Calcium, Ca"),
        "iron": get_nutrient(food, "Iron, Fe"),
        "magnesium": get_nutrient(food, "Magnesium, Mg"),
        "potassium": get_nutrient(food, "Potassium, K"),
        "zinc": get_nutrient(food, "Zinc, Zn"),
        "vitamin_a": get_nutrient(food, "Vitamin A, RAE"),
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
    """Scale USDA nutrition values assuming values are per 100g."""

    multiplier = grams / 100

    return {
        key: round(value * multiplier, 2)
        for key, value in nutrition.items()
    }


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

st.sidebar.title("NutriCoach")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "👤 Profile",
        "🍽️ Food",
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
            "Welcome to NutriCoach! Start by creating your profile."
        )

        if st.button("👤 Create My Profile"):
            st.session_state.page = "Profile"
            st.rerun()

    else:

        profile = st.session_state.profile
        targets = profile["targets"]

        st.subheader(
            f"Hello! Your goal: **{profile['goal']}** 🎯"
        )

        # Today's totals
        total_calories = sum(
            item["calories"]
            for item in st.session_state.food_log
        )

        total_protein = sum(
            item["protein"]
            for item in st.session_state.food_log
        )

        total_carbs = sum(
            item["carbs"]
            for item in st.session_state.food_log
        )

        total_fat = sum(
            item["fat"]
            for item in st.session_state.food_log
        )

        total_fiber = sum(
            item["fiber"]
            for item in st.session_state.food_log
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric(
            "Calories",
            f"{round(total_calories)} / {targets['calories']} kcal"
        )

        col2.metric(
            "Protein",
            f"{round(total_protein)} / {targets['protein']} g"
        )

        col3.metric(
            "Carbs",
            f"{round(total_carbs)} / {targets['carbs']} g"
        )

        col4.metric(
            "Fat",
            f"{round(total_fat)} / {targets['fat']} g"
        )

        col5.metric(
            "Fiber",
            f"{round(total_fiber)} / {targets['fiber']} g"
        )

        st.divider()

        # Progress bars
        st.subheader("📈 Nutrition Progress")

        calorie_progress = min(
            total_calories / targets["calories"],
            1.0
        )

        protein_progress = min(
            total_protein / targets["protein"],
            1.0
        )

        st.write("Calories")
        st.progress(calorie_progress)

        st.write("Protein")
        st.progress(protein_progress)

        # Water
        st.subheader("💧 Water")

        water_target = targets["water"]
        water_current = st.session_state.water

        st.write(
            f"{water_current} ml / {water_target} ml"
        )

        st.progress(
            min(water_current / water_target, 1.0)
        )

        st.divider()

        # Food log
        st.subheader("🍽️ Today's Food")

        if not st.session_state.food_log:
            st.info("No food logged yet. Go to Food → Add Food.")
        else:
            for item in st.session_state.food_log:
                st.write(
                    f"**{item['name']}** — "
                    f"{item['calories']} kcal | "
                    f"P {item['protein']}g | "
                    f"C {item['carbs']}g | "
                    f"F {item['fat']}g"
                )

# =========================================================
# PROFILE
# =========================================================

elif page == "👤 Profile":

    st.header("👤 Personal Profile")

    st.write(
        "Enter your information so NutriCoach can estimate "
        "your daily nutrition targets."
    )

    col1, col2 = st.columns(2)

    with col1:

        age = st.number_input(
            "Age",
            min_value=13,
            max_value=100,
            value=20
        )

        sex = st.selectbox(
            "Sex",
            ["Male", "Female"]
        )

        height = st.number_input(
            "Height (cm)",
            min_value=100.0,
            max_value=230.0,
            value=170.0
        )

        weight = st.number_input(
            "Weight (kg)",
            min_value=30.0,
            max_value=250.0,
            value=65.0
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

    if st.button("💾 Save Profile", type="primary"):

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

        st.success("Profile saved successfully! 🎉")

        st.subheader("🎯 Your Estimated Daily Targets")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Calories",
            f"{targets['calories']} kcal"
        )

        c2.metric(
            "Protein",
            f"{targets['protein']} g"
        )

        c3.metric(
            "Carbs",
            f"{targets['carbs']} g"
        )

        c4.metric(
            "Fat",
            f"{targets['fat']} g"
        )

        st.write(
            f"**Fiber:** {targets['fiber']} g/day"
        )

        st.write(
            f"**Water:** approximately {targets['water']} ml/day"
        )

        st.caption(
            "These are estimates for general fitness planning, "
            "not medical prescriptions."
        )

# =========================================================
# FOOD
# =========================================================

elif page == "🍽️ Food":

    st.header("🍽️ Food & Nutrition")

    st.write(
        "Search the USDA FoodData Central database "
        "and add foods to today's log."
    )

    # API key
    try:
        api_key = st.secrets["FDC_API_KEY"]
    except Exception:
        api_key = ""

    if not api_key:

        st.warning(
            "USDA API key is not configured yet."
        )

        st.info(
            "After deploying, add FDC_API_KEY in "
            "Streamlit Cloud → App settings → Secrets."
        )

    food_name = st.text_input(
        "🔎 Search for a food",
        placeholder="Example: egg, rice, chicken breast, banana"
    )

    if st.button("🔍 Search USDA"):

        if not food_name:
            st.warning("Please enter a food name.")

        elif not api_key:
            st.error("USDA API key is missing.")

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
                    "No USDA results found."
                )

    # Results
    if "usda_results" in st.session_state:

        results = st.session_state.usda_results

        options = []

        for food in results:

            description = food.get(
                "description",
                "Unknown food"
            )

            data_type = food.get(
                "dataType",
                ""
            )

            options.append(
                f"{description} ({data_type})"
            )

        selected_index = st.selectbox(
            "Choose the exact food",
            range(len(options)),
            format_func=lambda i: options[i]
        )

        selected_food = results[selected_index]

        nutrition = get_food_nutrition(
            selected_food
        )

        st.subheader("Nutrition per 100g")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Calories",
            f"{nutrition['calories']:.0f}"
        )

        c2.metric(
            "Protein",
            f"{nutrition['protein']:.1f} g"
        )

        c3.metric(
            "Carbs",
            f"{nutrition['carbs']:.1f} g"
        )

        c4.metric(
            "Fat",
            f"{nutrition['fat']:.1f} g"
        )

        c5.metric(
            "Fiber",
            f"{nutrition['fiber']:.1f} g"
        )

        st.divider()

        quantity_type = st.radio(
            "Quantity",
            ["Grams", "Pieces"],
            horizontal=True
        )

        if quantity_type == "Grams":

            grams = st.number_input(
                "Amount (grams)",
                min_value=1.0,
                value=100.0,
                step=1.0
            )

        else:

            pieces = st.number_input(
                "Number of pieces",
                min_value=1,
                value=1,
                step=1
            )

            food_lower = food_name.lower()

            # Common approximate weights
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
                f"Using approximately {grams_per_piece}g "
                f"per piece → {grams}g total. "
                "You can use grams for greater accuracy."
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

        st.subheader("Estimated nutrition for your amount")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Calories",
            f"{scaled['calories']:.0f} kcal"
        )

        c2.metric(
            "Protein",
            f"{scaled['protein']:.1f} g"
        )

        c3.metric(
            "Carbs",
            f"{scaled['carbs']:.1f} g"
        )

        c4.metric(
            "Fat",
            f"{scaled['fat']:.1f} g"
        )

        c5.metric(
            "Fiber",
            f"{scaled['fiber']:.1f} g"
        )

        if st.button(
            "➕ Add Food to Today's Log",
            type="primary"
        ):

            st.session_state.food_log.append({
                "name": selected_food.get(
                    "description",
                    food_name
                ),
                "meal": meal,
                "grams": grams,
                "calories": scaled["calories"],
                "protein": scaled["protein"],
                "carbs": scaled["carbs"],
                "fat": scaled["fat"],
                "fiber": scaled["fiber"],
                "calcium": scaled["calcium"],
                "iron": scaled["iron"],
                "magnesium": scaled["magnesium"],
                "potassium": scaled["potassium"],
                "zinc": scaled["zinc"],
                "vitamin_a": scaled["vitamin_a"],
                "vitamin_c": scaled["vitamin_c"],
                "vitamin_d": scaled["vitamin_d"]
            })

            st.success(
                "Food added to today's log! ✅"
            )

    # Today's food
    st.divider()

    st.subheader("📋 Today's Food Log")

    if not st.session_state.food_log:

        st.info("Nothing logged yet.")

    else:

        for i, item in enumerate(
            st.session_state.food_log
        ):

            col1, col2 = st.columns([5, 1])

            with col1:
                st.write(
                    f"**{item['name']}** "
                    f"({item['meal']}, {item['grams']:.0f}g)"
                )

                st.caption(
                    f"{item['calories']:.0f} kcal | "
                    f"Protein {item['protein']:.1f}g | "
                    f"Carbs {item['carbs']:.1f}g | "
                    f"Fat {item['fat']:.1f}g"
                )

            with col2:

                if st.button(
                    "🗑️",
                    key=f"delete_{i}"
                ):

                    st.session_state.food_log.pop(i)
                    st.rerun()

# =========================================================
# WATER
# =========================================================

elif page == "💧 Water":

    st.header("💧 Water Tracker")

    if not st.session_state.profile:

        st.warning(
            "Create your profile first so NutriCoach "
            "can calculate your water target."
        )

    else:

        target = st.session_state.profile[
            "targets"
        ]["water"]

        current = st.session_state.water

        st.metric(
            "Today's Water",
            f"{current} / {target} ml"
        )

        st.progress(
            min(current / target, 1.0)
        )

        st.subheader("🥤 Add Water")

        col1, col2, col3, col4 = st.columns(4)

        if col1.button("🥛 250 ml"):
            st.session_state.water += 250
            st.rerun()

        if col2.button("🥤 500 ml"):
            st.session_state.water += 500
            st.rerun()

        if col3.button("💧 750 ml"):
            st.session_state.water += 750
            st.rerun()

        if col4.button("🫗 1000 ml"):
            st.session_state.water += 1000
            st.rerun()

        if st.button("Reset Water"):
            st.session_state.water = 0
            st.rerun()

# =========================================================
# PROGRESS
# =========================================================

elif page == "📊 Progress":

    st.header("📊 Body Progress")

    st.write(
        "Record your measurements to track your progress."
    )

    weight = st.number_input(
        "Weight (kg)",
        min_value=20.0,
        max_value=300.0,
        value=65.0
    )

    waist = st.number_input(
        "Waist (cm)",
        min_value=30.0,
        max_value=200.0,
        value=80.0
    )

    chest = st.number_input(
        "Chest (cm)",
        min_value=30.0,
        max_value=200.0,
        value=90.0
    )

    arms = st.number_input(
        "Arms (cm)",
        min_value=10.0,
        max_value=100.0,
        value=30.0
    )

    legs = st.number_input(
        "Legs (cm)",
        min_value=20.0,
        max_value=150.0,
        value=50.0
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

        st.subheader("📋 Progress History")

        for entry in reversed(
            st.session_state.progress
        ):

            st.write(
                f"**{entry['date']}** — "
                f"Weight: {entry['weight']} kg | "
                f"Waist: {entry['waist']} cm | "
                f"Chest: {entry['chest']} cm | "
                f"Arms: {entry['arms']} cm | "
                f"Legs: {entry['legs']} cm"
            )

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🥗 NutriCoach • Nutrition estimates are for general "
    "fitness planning and should not replace professional "
    "medical or dietary advice."
)
