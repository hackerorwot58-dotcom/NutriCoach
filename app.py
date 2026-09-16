import streamlit as st
import requests
from datetime import date

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="NutriCoach",
    page_icon="🥗",
    layout="wide",
)

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: 800;
}
.subtitle {
    color: #666;
    font-size: 18px;
}
.card {
    padding: 18px;
    border-radius: 16px;
    border: 1px solid #ddd;
    margin-bottom: 12px;
}
.small {
    color: #666;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="main-title">🥗 NutriCoach</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Your AI Nutrition & Body Progress Coach</div>',
    unsafe_allow_html=True
)

# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "profile": {},
    "food_log": [],
    "water": 0,
    "workout_log": [],
    "progress": [],
    "supplements": [],
    "completed_meals": set(),
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =========================================================
# CALCULATOR
# =========================================================

def calculate_targets(age, sex, height, weight, activity, goal):

    if sex == "Male":
        bmr = (
            10 * weight
            + 6.25 * height
            - 5 * age
            + 5
        )
    else:
        bmr = (
            10 * weight
            + 6.25 * height
            - 5 * age
            - 161
        )

    activity_factor = {
        "Sedentary": 1.20,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
    }[activity]

    tdee = bmr * activity_factor

    adjustment = {
        "General Fitness": 0,
        "Calisthenics": 100,
        "Greek Body": -100,
        "Aesthetic Body": -100,
        "Muscle Gain": 250,
        "Fat Loss": -400,
        "Strength": 250,
        "Recomposition": -150,
    }[goal]

    calories = tdee + adjustment

    if goal in ["Muscle Gain", "Strength", "Calisthenics"]:
        protein = weight * 1.8
    elif goal in [
        "Fat Loss",
        "Recomposition",
        "Greek Body",
        "Aesthetic Body",
    ]:
        protein = weight * 1.7
    else:
        protein = weight * 1.6

    fat = weight * 0.8

    carbs = (
        calories
        - protein * 4
        - fat * 9
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
        "water": round(water),
    }

# =========================================================
# USDA
# =========================================================

def search_usda(query, api_key):

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {
        "api_key": api_key,
        "query": query,
        "pageSize": 10,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15,
        )

        if response.status_code != 200:
            return []

        return response.json().get("foods", [])

    except Exception:
        return []


def nutrient(food, name):

    for item in food.get("foodNutrients", []):

        if item.get("nutrientName", "").lower() == name.lower():
            return item.get("value", 0) or 0

    return 0


def food_nutrition(food):

    return {
        "calories": nutrient(food, "Energy"),
        "protein": nutrient(food, "Protein"),
        "carbs": nutrient(
            food,
            "Carbohydrate, by difference"
        ),
        "fat": nutrient(
            food,
            "Total lipid (fat)"
        ),
        "fiber": nutrient(
            food,
            "Fiber, total dietary"
        ),
        "calcium": nutrient(
            food,
            "Calcium, Ca"
        ),
        "iron": nutrient(
            food,
            "Iron, Fe"
        ),
        "magnesium": nutrient(
            food,
            "Magnesium, Mg"
        ),
        "potassium": nutrient(
            food,
            "Potassium, K"
        ),
        "zinc": nutrient(
            food,
            "Zinc, Zn"
        ),
        "vitamin_a": nutrient(
            food,
            "Vitamin A, RAE"
        ),
        "vitamin_c": nutrient(
            food,
            "Vitamin C, total ascorbic acid"
        ),
        "vitamin_d": nutrient(
            food,
            "Vitamin D (D2 + D3)"
        ),
    }


def scale_nutrition(data, grams):

    multiplier = grams / 100

    return {
        key: round(value * multiplier, 2)
        for key, value in data.items()
    }

# =========================================================
# DIET DATA
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
"Peanut butter toast + milk",
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
"Rice + soy chunks + salad",
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
"Roasted chana + fruit",
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
"Dal + rice + vegetables",
],
},

"Vegan": {

"Breakfast": [
"Oats + soy milk + banana",
"Vegetable poha",
"Besan chilla",
"Moong dal chilla",
"Idli + sambar",
"Oats + peanut butter",
"Dalia + soy milk",
"Peanut butter toast + banana",
"Sprouts chaat + toast",
"Vegetable upma",
"Chana chaat + toast",
"Oats + banana + peanuts",
"Vegetable dosa + sambar",
"Poha + peanuts",
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
"Rice + chickpeas + salad",
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
"Banana + peanuts",
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
"Dal + rice + vegetables",
],
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
"Egg sandwich + milk",
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
"Chicken + roti + curd",
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
"Milk + oats",
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
"Chicken + rice + vegetables",
],
}
}

# =========================================================
# WORKOUT DATA
# =========================================================

WORKOUTS = {

"Walking": {
"Low": 3,
"Medium": 4,
"High": 5,
},

"Running": {
"Low": 7,
"Medium": 10,
"High": 13,
},

"Cycling": {
"Low": 5,
"Medium": 8,
"High": 11,
},

"Strength Training": {
"Low": 4,
"Medium": 6,
"High": 8,
},

"Calisthenics": {
"Low": 5,
"Medium": 7,
"High": 9,
},

"Yoga": {
"Low": 2.5,
"Medium": 3.5,
"High": 5,
},

"Sports": {
"Low": 5,
"Medium": 8,
"High": 11,
},
}

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🥗 NutriCoach")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "👤 Profile",
        "🍽️ Food",
        "📋 Diet Plan",
        "🏋️ Workout",
        "💧 Water",
        "📊 Progress",
        "💊 Supplements",
        "📸 Camera",
        "🤖 AI Coach",
    ],
)

# =========================================================
# HOME
# =========================================================

if page == "🏠 Home":

    st.header("🏠 Today's Dashboard")

    if not st.session_state.profile:

        st.info(
            "Welcome to NutriCoach! "
            "Create your profile to get started."
        )

    else:

        profile = st.session_state.profile
        targets = profile["targets"]

        total_calories = sum(
            x["calories"]
            for x in st.session_state.food_log
        )

        total_protein = sum(
            x["protein"]
            for x in st.session_state.food_log
        )

        total_carbs = sum(
            x["carbs"]
            for x in st.session_state.food_log
        )

        total_fat = sum(
            x["fat"]
            for x in st.session_state.food_log
        )

        total_fiber = sum(
            x["fiber"]
            for x in st.session_state.food_log
        )

        exercise = sum(
            x["calories"]
            for x in st.session_state.workout_log
        )

        st.subheader(
            f"🎯 Goal: {profile['goal']}"
        )

        a, b, c, d, e = st.columns(5)

        a.metric(
            "Calories",
            f"{total_calories:.0f} / {targets['calories']}"
        )

        b.metric(
            "Protein",
            f"{total_protein:.1f} / {targets['protein']}g"
        )

        c.metric(
            "Carbs",
            f"{total_carbs:.1f} / {targets['carbs']}g"
        )

        d.metric(
            "Fat",
            f"{total_fat:.1f} / {targets['fat']}g"
        )

        e.metric(
            "Exercise",
            f"{exercise:.0f} kcal"
        )

        st.divider()

        st.subheader("📈 Nutrition Progress")

        st.write("Calories")
        st.progress(
            min(
                total_calories /
                targets["calories"],
                1.0
            )
        )

        st.write("Protein")
        st.progress(
            min(
                total_protein /
                targets["protein"],
                1.0
            )
        )

        st.write("Fiber")
        st.progress(
            min(
                total_fiber /
                targets["fiber"],
                1.0
            )
        )

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

        st.subheader("🤖 Today's Recommendation")

        protein_remaining = (
            targets["protein"] -
            total_protein
        )

        calorie_remaining = (
            targets["calories"] -
            total_calories
        )

        if protein_remaining > 30:

            st.info(
                f"You still need about "
                f"**{protein_remaining:.0f}g protein** today."
            )

        elif calorie_remaining > 300:

            st.info(
                f"You have around "
                f"**{calorie_remaining:.0f} kcal** remaining."
            )

        else:

            st.success(
                "You're getting close to today's nutrition targets! 🎉"
            )

# =========================================================
# PROFILE
# =========================================================

elif page == "👤 Profile":

    st.header("👤 Personal Profile")

    c1, c2 = st.columns(2)

    with c1:

        age = st.number_input(
            "Age",
            min_value=13,
            max_value=100,
            value=20,
        )

        sex = st.selectbox(
            "Sex",
            ["Male", "Female"],
        )

        height = st.number_input(
            "Height (cm)",
            min_value=100.0,
            max_value=230.0,
            value=170.0,
        )

        weight = st.number_input(
            "Weight (kg)",
            min_value=30.0,
            max_value=250.0,
            value=65.0,
        )

        activity = st.selectbox(
            "Activity Level",
            [
                "Sedentary",
                "Lightly Active",
                "Moderately Active",
                "Very Active",
            ],
        )

    with c2:

        diet = st.selectbox(
            "Diet Preference",
            [
                "Non-Vegetarian",
                "Vegetarian",
                "Vegan",
            ],
        )

        budget = st.selectbox(
            "Food Budget",
            [
                "Low",
                "Medium",
                "High",
            ],
        )

        body_type = st.selectbox(
            "Current Body Type",
            [
                "Slim / Skinny",
                "Skinny Fat",
                "Average",
                "Athletic",
                "Muscular",
                "Higher Body Fat",
            ],
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
                "Recomposition",
            ],
        )

    if st.button(
        "💾 Save Profile",
        type="primary",
    ):

        targets = calculate_targets(
            age,
            sex,
            height,
            weight,
            activity,
            goal,
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
            "targets": targets,
        }

        st.success(
            "Profile saved successfully! 🎉"
        )

        st.subheader("🎯 Estimated Daily Targets")

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
            f"Water: approximately "
            f"**{targets['water']} ml/day**"
        )

        st.caption(
            "These are estimates for general fitness planning."
        )

# =========================================================
# FOOD
# =========================================================

elif page == "🍽️ Food":

    st.header("🍽️ Food & Nutrition Tracking")

    try:
        api_key = st.secrets["FDC_API_KEY"]
    except Exception:
        api_key = ""

    if not api_key:

        st.warning(
            "USDA API key is not configured."
        )

        st.info(
            "Add FDC_API_KEY in Streamlit Cloud → "
            "Settings → Secrets."
        )

    search = st.text_input(
        "🔎 Search USDA FoodData Central",
        placeholder="egg, rice, chicken breast, banana..."
    )

    if st.button("🔍 Search USDA"):

        if not search:

            st.warning(
                "Enter a food name."
            )

        elif not api_key:

            st.error(
                "USDA API key is missing."
            )

        else:

            results = search_usda(
                search,
                api_key
            )

            if results:

                st.session_state.usda_results = results

                st.success(
                    f"Found {len(results)} foods."
                )

            else:

                st.error(
                    "No foods found."
                )

    if "usda_results" in st.session_state:

        results = st.session_state.usda_results

        names = [
            f"{food.get('description', 'Food')} "
            f"({food.get('dataType', '')})"
            for food in results
        ]

        selected = st.selectbox(
            "Select the exact USDA food",
            range(len(names)),
            format_func=lambda x: names[x],
        )

        food = results[selected]

        nutrition = food_nutrition(food)

        st.subheader("Nutrition per 100g")

        a, b, c, d, e = st.columns(5)

        a.metric(
            "Calories",
            f"{nutrition['calories']:.0f}"
        )

        b.metric(
            "Protein",
            f"{nutrition['protein']:.1f}g"
        )

        c.metric(
            "Carbs",
            f"{nutrition['carbs']:.1f}g"
        )

        d.metric(
            "Fat",
            f"{nutrition['fat']:.1f}g"
        )

        e.metric(
            "Fiber",
            f"{nutrition['fiber']:.1f}g"
        )

        quantity_type = st.radio(
            "Quantity",
            ["Grams", "Pieces"],
            horizontal=True,
        )

        if quantity_type == "Grams":

            grams = st.number_input(
                "Amount in grams",
                min_value=1.0,
                max_value=5000.0,
                value=100.0,
            )

        else:

            pieces = st.number_input(
                "Number of pieces",
                min_value=1,
                max_value=100,
                value=1,
            )

            lower = search.lower()

            piece_weights = {
                "egg": 50,
                "banana": 118,
                "apple": 182,
                "orange": 130,
                "roti": 40,
                "chapati": 40,
            }

            grams_per_piece = 100

            for key, value in piece_weights.items():

                if key in lower:
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
                "Dinner",
            ],
        )

        scaled = scale_nutrition(
            nutrition,
            grams,
        )

        st.subheader("Your Food Amount")

        a, b, c, d, e = st.columns(5)

        a.metric(
            "Calories",
            f"{scaled['calories']:.0f}"
        )

        b.metric(
            "Protein",
            f"{scaled['protein']:.1f}g"
        )

        c.metric(
            "Carbs",
            f"{scaled['carbs']:.1f}g"
        )

        d.metric(
            "Fat",
            f"{scaled['fat']:.1f}g"
        )

        e.metric(
            "Fiber",
            f"{scaled['fiber']:.1f}g"
        )

        if st.button(
            "➕ Add Food to Today",
            type="primary",
        ):

            st.session_state.food_log.append({
                "name": food.get(
                    "description",
                    search,
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
                "vitamin_d": scaled["vitamin_d"],
            })

            st.success(
                "Food added! ✅"
            )

    st.divider()

    st.subheader("📋 Today's Food Log")

    if not st.session_state.food_log:

        st.info(
            "No food logged yet."
        )

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
                f"Protein {item['protein']:.1f}g | "
                f"Carbs {item['carbs']:.1f}g | "
                f"Fat {item['fat']:.1f}g | "
                f"Fiber {item['fiber']:.1f}g"
            )

            if st.button(
                "🗑️ Remove",
                key=f"delete_food_{i}",
            ):

                st.session_state.food_log.pop(i)
                st.rerun()

# =========================================================
# DIET PLAN
# =========================================================

elif page == "📋 Diet Plan":

    st.header("📋 14-Day Personalized Diet Plan")

    if not st.session_state.profile:

        st.warning(
            "Create your profile first."
        )

    else:

        profile = st.session_state.profile

        st.write(
            f"**Goal:** {profile['goal']}  |  "
            f"**Diet:** {profile['diet']}  |  "
            f"**Budget:** {profile['budget']}"
        )

        st.info(
            "Portions should be adjusted to your calorie "
            "and protein targets."
        )

        for day in range(1, 15):

            st.subheader(
                f"📅 Day {day}"
            )

            meals = [
                (
                    "Breakfast",
                    MEALS[profile["diet"]]["Breakfast"][day - 1]
                ),
                (
                    "Lunch",
                    MEALS[profile["diet"]]["Lunch"][day - 1]
                ),
                (
                    "Snack",
                    MEALS[profile["diet"]]["Snack"][day - 1]
                ),
                (
                    "Dinner",
                    MEALS[profile["diet"]]["Dinner"][day - 1]
                ),
            ]

            for meal_name, meal in meals:

                key = f"meal_{day}_{meal_name}"

                checked = st.checkbox(
                    f"{meal_name}: {meal}",
                    value=key in st.session_state.completed_meals,
                    key=key,
                )

                if checked:
                    st.session_state.completed_meals.add(key)
                else:
                    st.session_state.completed_meals.discard(key)

            st.divider()

# =========================================================
# WORKOUT
# =========================================================

elif page == "🏋️ Workout":

    st.header("🏋️ Exercise Tracking")

    if not st.session_state.profile:

        st.warning(
            "Create your profile first."
        )

    else:

        weight = st.session_state.profile["weight"]

        exercise = st.selectbox(
            "Exercise",
            list(WORKOUTS.keys())
        )

        intensity = st.selectbox(
            "Intensity",
            [
                "Low",
                "Medium",
                "High",
            ]
        )

        duration = st.number_input(
            "Duration (minutes)",
            min_value=1,
            max_value=300,
            value=30,
        )

        burn_rate = WORKOUTS[
            exercise
        ][intensity]

        estimated_burn = (
            burn_rate
            * weight
            * duration
            / 60
        )

        st.metric(
            "Estimated Calories Burned",
            f"{estimated_burn:.0f} kcal"
        )

        st.caption(
            "Exercise calorie values are estimates."
        )

        if st.button(
            "➕ Add Workout",
            type="primary",
        ):

            st.session_state.workout_log.append({
                "date": str(date.today()),
                "exercise": exercise,
                "intensity": intensity,
                "duration": duration,
                "calories": round(estimated_burn),
            })

            st.success(
                "Workout added! 💪"
            )

        st.divider()

        st.subheader(
            "📋 Today's Workouts"
        )

        if not st.session_state.workout_log:

            st.info(
                "No workouts logged yet."
            )

        else:

            for i, item in enumerate(
                st.session_state.workout_log
            ):

                st.write(
                    f"**{item['exercise']}** — "
                    f"{item['duration']} min — "
                    f"{item['intensity']} — "
                    f"{item['calories']} kcal"
                )

                if st.button(
                    "🗑️ Remove",
                    key=f"delete_workout_{i}",
                ):

                    st.session_state.workout_log.pop(i)
                    st.rerun()

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

        current = st.session_state.water

        st.metric(
            "Daily Target",
            f"{target} ml"
        )

        st.metric(
            "Consumed",
            f"{current} ml"
        )

        st.progress(
            min(
                current / target,
                1.0
            )
        )

        st.subheader(
            "🥤 Add Water"
        )

        a, b, c, d = st.columns(4)

        if a.button("🥛 250 ml"):
            st.session_state.water += 250
            st.rerun()

        if b.button("🥤 500 ml"):
            st.session_state.water += 500
            st.rerun()

        if c.button("💧 750 ml"):
            st.session_state.water += 750
            st.rerun()

        if d.button("🫗 1000 ml"):
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
        "Record your measurements over time."
    )

    weight = st.number_input(
        "Weight (kg)",
        min_value=20.0,
        max_value=300.0,
        value=65.0,
    )

    waist = st.number_input(
        "Waist (cm)",
        min_value=30.0,
        max_value=200.0,
        value=80.0,
    )

    chest = st.number_input(
        "Chest (cm)",
        min_value=30.0,
        max_value=200.0,
        value=90.0,
    )

    arms = st.number_input(
        "Arms (cm)",
        min_value=10.0,
        max_value=100.0,
        value=30.0,
    )

    legs = st.number_input(
        "Legs (cm)",
        min_value=20.0,
        max_value=150.0,
        value=50.0,
    )

    if st.button(
        "💾 Save Measurements",
        type="primary",
    ):

        st.session_state.progress.append({
            "date": str(date.today()),
            "weight": weight,
            "waist": waist,
            "chest": chest,
            "arms": arms,
            "legs": legs,
        })

        st.success(
            "Progress saved! 📈"
        )

    if st.session_state.progress:

        st.subheader(
            "📋 Progress History"
        )

        for item in reversed(
            st.session_state.progress
        ):

            st.write(
                f"**{item['date']}** — "
                f"Weight {item['weight']} kg | "
                f"Waist {item['waist']} cm | "
                f"Chest {item['chest']} cm | "
                f"Arms {item['arms']} cm | "
                f"Legs {item['legs']} cm"
            )

# =========================================================
# SUPPLEMENTS
# =========================================================

elif page == "💊 Supplements":

    st.header("💊 Supplement Tracker")

    st.write(
        "Track supplements you choose to use."
    )

    supplement = st.selectbox(
        "Supplement",
        [
            "Protein Powder",
            "Peanut Butter",
            "Creatine",
            "Multivitamin",
            "Omega-3",
            "Electrolytes",
        ],
    )

    amount = st.text_input(
        "Amount / serving",
        placeholder="Example: 1 scoop"
    )

    if st.button(
        "➕ Add Supplement",
        type="primary",
    ):

        st.session_state.supplements.append({
            "name": supplement,
            "amount": amount,
            "date": str(date.today()),
        })

        st.success(
            "Supplement added."
        )

    st.divider()

    st.subheader(
        "Today's Supplements"
    )

    if not st.session_state.supplements:

        st.info(
            "No supplements logged."
        )

    else:

        for i, item in enumerate(
            st.session_state.supplements
        ):

            st.write(
                f"**{item['name']}** — "
                f"{item['amount']}"
            )

            if st.button(
                "🗑️ Remove",
                key=f"delete_supplement_{i}",
            ):

                st.session_state.supplements.pop(i)
                st.rerun()

# =========================================================
# CAMERA
# =========================================================

elif page == "📸 Camera":

    st.header("📸 Camera Body Progress")

    st.write(
        "Use your camera to capture progress photos."
    )

    st.info(
        "A normal camera cannot reliably measure exact "
        "body dimensions in centimetres without a known "
        "reference or calibration."
    )

    photo_type = st.selectbox(
        "Photo",
        [
            "Front",
            "Side",
            "Back",
        ],
    )

    photo = st.camera_input(
        f"Take {photo_type} Photo"
    )

    if photo:

        st.success(
            f"{photo_type} photo captured! 📸"
        )

        st.image(
            photo,
            caption=f"{photo_type} progress photo",
        )

        st.checkbox(
            "I confirm this photo is suitable for progress tracking."
        )

    st.subheader(
        "📏 Manual Measurements"
    )

    st.write(
        "For accurate progress tracking, enter your "
        "measurements manually in the Progress section."
    )

# =========================================================
# AI COACH
# =========================================================

elif page == "🤖 AI Coach":

    st.header("🤖 Complete My Nutrition")

    if not st.session_state.profile:

        st.warning(
            "Create your profile first."
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

        remaining_calories = (
            targets["calories"] -
            calories
        )

        remaining_protein = (
            targets["protein"] -
            protein
        )

        remaining_carbs = (
            targets["carbs"] -
            carbs
        )

        remaining_fat = (
            targets["fat"] -
            fat
        )

        remaining_fiber = (
            targets["fiber"] -
            fiber
        )

        st.subheader(
            "📊 Your Current Nutrition"
        )

        a, b, c, d = st.columns(4)

        a.metric(
            "Calories Left",
            f"{max(remaining_calories, 0):.0f}"
        )

        b.metric(
            "Protein Left",
            f"{max(remaining_protein, 0):.1f}g"
        )

        c.metric(
            "Carbs Left",
            f"{max(remaining_carbs, 0):.1f}g"
        )

        d.metric(
            "Fat Left",
            f"{max(remaining_fat, 0):.1f}g"
        )

        st.divider()

        st.subheader(
            "💡 NutriCoach Recommendation"
        )

        if remaining_protein > 40:

            if profile["diet"] == "Vegan":

                st.success(
                    f"You still need about "
                    f"**{remaining_protein:.0f}g protein**. "
                    "Consider soy chunks, tofu, lentils, "
                    "beans or a plant protein powder."
                )

            elif profile["diet"] == "Vegetarian":

                st.success(
                    f"You still need about "
                    f"**{remaining_protein:.0f}g protein**. "
                    "Consider paneer, curd, milk, soy chunks "
                    "or dal."
                )

            else:

                st.success(
                    f"You still need about "
                    f"**{remaining_protein:.0f}g protein**. "
                    "Consider eggs, chicken, curd, paneer "
                    "or dal."
                )

        elif remaining_fiber > 10:

            st.info(
                f"You still need about "
                f"**{remaining_fiber:.0f}g fiber**. "
                "Add vegetables, fruit, oats, legumes "
                "or whole grains."
            )

        elif remaining_calories > 300:

            st.info(
                f"You have about "
                f"**{remaining_calories:.0f} kcal** remaining. "
                "Choose a balanced meal containing protein, "
                "carbohydrates and vegetables."
            )

        else:

            st.success(
                "Your nutrition intake is close to today's targets! 🎉"
            )

        st.subheader(
            "🧠 Personalized Context"
        )

        st.write(
            f"**Goal:** {profile['goal']}"
        )

        st.write(
            f"**Diet:** {profile['diet']}"
        )

        st.write(
            f"**Budget:** {profile['budget']}"
        )

        st.write(
            f"**Body Type:** {profile['body_type']}"
        )

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🥗 NutriCoach • Nutrition values are estimates for "
    "general fitness planning and are not medical advice."
)
