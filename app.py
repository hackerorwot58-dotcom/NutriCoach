import streamlit as st
import requests
from datetime import date

# ============================================================
# NUTRICOACH - PYTHON STREAMLIT WEBSITE
# ============================================================

st.set_page_config(
    page_title="NutriCoach",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# CSS
# -----------------------------

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7f4;
    }

    .main-title {
        font-size: 42px;
        font-weight: 800;
        color: #173b2c;
        margin-bottom: 0;
    }

    .subtitle {
        color: #6b756f;
        font-size: 17px;
        margin-bottom: 25px;
    }

    .card {
        background: white;
        padding: 22px;
        border-radius: 20px;
        border: 1px solid #e5ebe6;
        box-shadow: 0 4px 18px rgba(20, 50, 35, 0.06);
        margin-bottom: 16px;
    }

    .big-number {
        font-size: 32px;
        font-weight: 800;
        color: #173b2c;
    }

    .small-label {
        color: #748078;
        font-size: 14px;
    }

    .coach {
        background: linear-gradient(135deg, #173b2c, #2f7253);
        color: white;
        padding: 25px;
        border-radius: 22px;
        margin: 10px 0 20px 0;
    }

    .coach h2 {
        color: white;
        margin-bottom: 8px;
    }

    .food-row {
        padding: 12px;
        border-bottom: 1px solid #edf0ed;
    }

    div.stButton > button {
        border-radius: 12px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Session state
# -----------------------------

if "profile" not in st.session_state:
    st.session_state.profile = {
        "name": "My Profile",
        "age": 25,
        "sex": "Male",
        "height": 170,
        "weight": 70,
        "activity": "Moderately Active",
        "diet": "Non-vegetarian",
        "budget": 500,
        "body_type": "Average",
        "goal": "General Fitness",
    }

if "food_log" not in st.session_state:
    st.session_state.food_log = []

if "water" not in st.session_state:
    st.session_state.water = 0

if "measurements" not in st.session_state:
    st.session_state.measurements = []

if "workout_done" not in st.session_state:
    st.session_state.workout_done = False


# ============================================================
# NUTRITION ENGINE
# ============================================================

def calculate_targets(profile):
    age = profile["age"]
    weight = profile["weight"]
    height = profile["height"]
    sex = profile["sex"]
    activity = profile["activity"]
    goal = profile["goal"]

    if sex == "Male":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    activity_values = {
        "Sedentary": 1.20,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
    }

    maintenance = bmr * activity_values.get(activity, 1.55)

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

    calories = maintenance + adjustments.get(goal, 0)

    protein_factor = 1.6

    if goal in ["Muscle Gain", "Strength", "Calisthenics"]:
        protein_factor = 1.8
    elif goal in [
        "Fat Loss",
        "Recomposition",
        "Aesthetic Body",
        "Greek Body",
    ]:
        protein_factor = 1.7

    protein = weight * protein_factor
    fat = weight * 0.8

    remaining_calories = calories - (protein * 4) - (fat * 9)
    carbs = max(0, remaining_calories / 4)

    fiber = calories / 1000 * 14
    water_ml = weight * 35

    return {
        "calories": round(calories),
        "protein": round(protein),
        "carbs": round(carbs),
        "fat": round(fat),
        "fiber": round(fiber),
        "water": round(water_ml),
        "bmr": round(bmr),
        "maintenance": round(maintenance),
    }


# ============================================================
# FOOD ENGINE
# ============================================================

def search_usda(food_name):
    try:
        api_key = st.secrets["FDC_API_KEY"]
    except Exception:
        return None, "USDA API key not found."

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {
        "api_key": api_key,
        "query": food_name,
        "pageSize": 8,
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None, "USDA service returned an error."

        return response.json().get("foods", []), None

    except requests.RequestException:
        return None, "Could not connect to USDA."


def extract_nutrients(food):
    values = {}

    for nutrient in food.get("foodNutrients", []):
        name = nutrient.get("nutrientName")
        value = nutrient.get("value")

        if name:
            values[name] = value

    return {
        "calories": values.get("Energy", 0) or 0,
        "protein": values.get("Protein", 0) or 0,
        "carbs": values.get("Carbohydrate, by difference", 0) or 0,
        "fat": values.get("Total lipid (fat)", 0) or 0,
        "fiber": values.get("Fiber, total dietary", 0) or 0,
        "sugar": values.get("Total Sugars", 0) or 0,
        "sodium": values.get("Sodium, Na", 0) or 0,
        "calcium": values.get("Calcium, Ca", 0) or 0,
        "iron": values.get("Iron, Fe", 0) or 0,
        "magnesium": values.get("Magnesium, Mg", 0) or 0,
        "potassium": values.get("Potassium, K", 0) or 0,
        "zinc": values.get("Zinc, Zn", 0) or 0,
        "vitamin_a": values.get("Vitamin A, RAE", 0) or 0,
        "vitamin_c": values.get(
            "Vitamin C, total ascorbic acid", 0
        ) or 0,
        "vitamin_d": values.get("Vitamin D (D2 + D3)", 0) or 0,
        "vitamin_e": values.get("Vitamin E (alpha-tocopherol)", 0) or 0,
        "vitamin_k": values.get("Vitamin K (phylloquinone)", 0) or 0,
    }


def scale_nutrients(nutrients, grams):
    multiplier = grams / 100

    return {
        key: value * multiplier
        for key, value in nutrients.items()
    }


def totals():
    result = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "fiber": 0,
    }

    for item in st.session_state.food_log:
        for key in result:
            result[key] += item.get(key, 0)

    return result


# ============================================================
# AUTOMATIC WORKOUT ENGINE
# ============================================================

def generate_workout(profile):
    goal = profile["goal"]
    activity = profile["activity"]

    if goal == "Muscle Gain":
        exercises = [
            ("Push-ups", 4, "10-15"),
            ("Bodyweight Squats", 4, "12-15"),
            ("Lunges", 3, "10 each leg"),
            ("Pike Push-ups", 3, "8-12"),
            ("Plank", 3, "30-60 sec"),
        ]

    elif goal == "Calisthenics":
        exercises = [
            ("Push-ups", 4, "8-15"),
            ("Bodyweight Squats", 4, "12-20"),
            ("Mountain Climbers", 3, "30 sec"),
            ("Glute Bridge", 3, "15"),
            ("Plank", 3, "45 sec"),
        ]

    elif goal == "Fat Loss":
        exercises = [
            ("Brisk Walking", 1, "20 min"),
            ("Bodyweight Squats", 3, "15"),
            ("Push-ups", 3, "10"),
            ("Mountain Climbers", 3, "30 sec"),
            ("Plank", 3, "30 sec"),
        ]

    elif goal == "Strength":
        exercises = [
            ("Push-ups", 5, "6-12"),
            ("Squats", 5, "8-12"),
            ("Lunges", 4, "8 each leg"),
            ("Pike Push-ups", 4, "6-10"),
            ("Plank", 4, "45-60 sec"),
        ]

    else:
        exercises = [
            ("Brisk Walking", 1, "20 min"),
            ("Bodyweight Squats", 3, "12"),
            ("Push-ups", 3, "10"),
            ("Lunges", 3, "10 each leg"),
            ("Plank", 3, "30 sec"),
        ]

    if activity == "Sedentary":
        exercises = exercises[:4]

    return exercises


# ============================================================
# COACH ENGINE
# ============================================================

def coach_message(targets, current):
    calorie_gap = targets["calories"] - current["calories"]
    protein_gap = targets["protein"] - current["protein"]
    water_gap = targets["water"] - st.session_state.water

    if protein_gap > 20:
        return (
            f"You are about {protein_gap:.0f}g short on protein today. "
            "Your next meal should prioritize a protein-rich food."
        )

    if calorie_gap > 600:
        return (
            f"You still have about {calorie_gap:.0f} kcal available today. "
            "A balanced meal with protein, vegetables and carbohydrates would fit."
        )

    if water_gap > 500:
        return (
            f"You are about {water_gap:.0f} ml below your water target. "
            "Have another glass of water."
        )

    if protein_gap > 0:
        return (
            f"You need about {protein_gap:.0f}g more protein "
            "to reach today's target."
        )

    return "Your nutrition is currently close to today's targets. Keep going."


# ============================================================
# PROFILE
# ============================================================

profile = st.session_state.profile
targets = calculate_targets(profile)
current = totals()


# ============================================================
# NAVIGATION
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "Home"

nav = st.columns(5)

pages = [
    ("🏠", "Home"),
    ("🍽️", "Food"),
    ("🏋️", "Workout"),
    ("📊", "Progress"),
    ("👤", "Profile"),
]

for column, (icon, page) in zip(nav, pages):
    with column:
        if st.button(
            f"{icon} {page}",
            use_container_width=True,
            key=f"nav_{page}",
        ):
            st.session_state.page = page


# ============================================================
# HOME
# ============================================================

if st.session_state.page == "Home":

    st.markdown(
        '<div class="main-title">NutriCoach</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="subtitle">Your food. Your body. Your plan. '
        "One intelligent coach.</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="coach">
            <h2>🧠 Your Next Best Action</h2>
            <p>{coach_message(targets, current)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="card">
                <div class="small-label">Calories</div>
                <div class="big-number">
                    {current['calories']:.0f}
                </div>
                <div class="small-label">
                    of {targets['calories']} kcal
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="card">
                <div class="small-label">Protein</div>
                <div class="big-number">
                    {current['protein']:.0f}g
                </div>
                <div class="small-label">
                    of {targets['protein']}g
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="card">
                <div class="small-label">Water</div>
                <div class="big-number">
                    {st.session_state.water / 1000:.1f}L
                </div>
                <div class="small-label">
                    of {targets['water'] / 1000:.1f}L
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="card">
                <div class="small-label">Goal</div>
                <div class="big-number" style="font-size:20px;">
                    {profile['goal']}
                </div>
                <div class="small-label">
                    {profile['weight']} kg
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Today's nutrition")

    progress_cols = st.columns(4)

    metrics = [
        ("Calories", current["calories"], targets["calories"]),
        ("Protein", current["protein"], targets["protein"]),
        ("Carbs", current["carbs"], targets["carbs"]),
        ("Fat", current["fat"], targets["fat"]),
    ]

    for col, (name, value, target) in zip(progress_cols, metrics):
        with col:
            st.write(f"**{name}**")
            st.progress(
                min(1.0, max(0.0, value / max(target, 1)))
            )
            st.caption(f"{value:.0f} / {target:.0f}")

    st.subheader("💧 Water")

    water_col1, water_col2 = st.columns([3, 1])

    with water_col1:
        st.progress(
            min(
                1.0,
                st.session_state.water / max(targets["water"], 1),
            )
        )

    with water_col2:
        if st.button("＋ 250 ml", use_container_width=True):
            st.session_state.water += 250
            st.rerun()

    st.subheader("🏋️ Today's automatic workout")

    workout = generate_workout(profile)

    for exercise, sets, reps in workout:
        st.write(f"**{exercise}** — {sets} × {reps}")

    if st.button("✅ Complete today's workout"):
        st.session_state.workout_done = True

    if st.session_state.workout_done:
        st.success("Workout completed today. Great work!")


# ============================================================
# FOOD
# ============================================================

elif st.session_state.page == "Food":

    st.title("🍽️ Food")

    st.write(
        "Search food → choose quantity → see nutrition → "
        "add it → immediately see today's remaining targets."
    )

    st.subheader("🔎 Search USDA food")

    search = st.text_input(
        "Food",
        placeholder="Try egg, banana, rice, paneer...",
    )

    if search:

        foods, error = search_usda(search)

        if error:
            st.error(error)

        elif not foods:
            st.warning("No USDA foods found.")

        else:
            food_names = [
                f"{food.get('description', 'Unknown')} "
                f"({food.get('dataType', '')})"
                for food in foods
            ]

            selected_index = st.selectbox(
                "Choose food",
                range(len(food_names)),
                format_func=lambda i: food_names[i],
            )

            selected_food = foods[selected_index]

            nutrients = extract_nutrients(selected_food)

            grams = st.number_input(
                "Serving size (grams)",
                min_value=1.0,
                value=100.0,
                step=10.0,
            )

            scaled = scale_nutrients(nutrients, grams)

            st.subheader("Nutrition")

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric("Calories", f"{scaled['calories']:.0f}")
            c2.metric("Protein", f"{scaled['protein']:.1f} g")
            c3.metric("Carbs", f"{scaled['carbs']:.1f} g")
            c4.metric("Fat", f"{scaled['fat']:.1f} g")
            c5.metric("Fiber", f"{scaled['fiber']:.1f} g")

            remaining_calories = (
                targets["calories"]
                - current["calories"]
                - scaled["calories"]
            )

            remaining_protein = (
                targets["protein"]
                - current["protein"]
                - scaled["protein"]
            )

            st.info(
                f"After adding this food: "
                f"**{remaining_calories:.0f} kcal** and "
                f"**{remaining_protein:.1f}g protein** "
                "would remain."
            )

            if st.button(
                "➕ Add to today's food",
                use_container_width=True,
            ):

                entry = {
                    "name": selected_food.get(
                        "description",
                        "Food",
                    ),
                    "grams": grams,
                    **scaled,
                }

                st.session_state.food_log.append(entry)

                st.success("Food added to today's log.")
                st.rerun()

    st.divider()

    st.subheader("🧮 Personal food calculator")

    calculator_name = st.text_input(
        "Food name",
        key="calculator_name",
        placeholder="Example: homemade paneer",
    )

    calculator_calories = st.number_input(
        "Calories",
        min_value=0.0,
        value=0.0,
        key="calculator_calories",
    )

    calculator_protein = st.number_input(
        "Protein (g)",
        min_value=0.0,
        value=0.0,
        key="calculator_protein",
    )

    calculator_carbs = st.number_input(
        "Carbs (g)",
        min_value=0.0,
        value=0.0,
        key="calculator_carbs",
    )

    calculator_fat = st.number_input(
        "Fat (g)",
        min_value=0.0,
        value=0.0,
        key="calculator_fat",
    )

    if st.button("➕ Add custom food"):
        if calculator_name.strip():
            st.session_state.food_log.append(
                {
                    "name": calculator_name,
                    "grams": 0,
                    "calories": calculator_calories,
                    "protein": calculator_protein,
                    "carbs": calculator_carbs,
                    "fat": calculator_fat,
                    "fiber": 0,
                }
            )
            st.success("Custom food added.")
            st.rerun()

    st.divider()

    st.subheader("📋 Today's food")

    if not st.session_state.food_log:
        st.info("Nothing logged yet.")

    else:
        for index, item in enumerate(
            st.session_state.food_log
        ):

            col1, col2, col3, col4 = st.columns(
                [3, 1, 1, 1]
            )

            with col1:
                st.write(
                    f"**{item['name']}** "
                    f"({item.get('grams', 0):.0f}g)"
                )

            with col2:
                st.write(
                    f"{item['calories']:.0f} kcal"
                )

            with col3:
                st.write(
                    f"{item['protein']:.1f}g protein"
                )

            with col4:
                if st.button(
                    "Remove",
                    key=f"remove_{index}",
                ):
                    st.session_state.food_log.pop(index)
                    st.rerun()

    st.divider()

    st.subheader("🥦 Micronutrients today")

    micro_keys = [
        "fiber",
        "sugar",
        "sodium",
        "calcium",
        "iron",
        "magnesium",
        "potassium",
        "zinc",
    ]

    micro_totals = {}

    for key in micro_keys:
        micro_totals[key] = sum(
            item.get(key, 0)
            for item in st.session_state.food_log
        )

    micro_cols = st.columns(4)

    for col, key in zip(micro_cols * 2, micro_keys):
        with col:
            st.metric(
                key.title(),
                f"{micro_totals[key]:.1f}",
            )


# ============================================================
# WORKOUT
# ============================================================

elif st.session_state.page == "Workout":

    st.title("🏋️ Automatic Workout")

    st.write(
        "NutriCoach generates your workout from your profile "
        "and goal. You do not need to manually select exercises."
    )

    workout = generate_workout(profile)

    st.subheader("Today's plan")

    for number, (exercise, sets, reps) in enumerate(
        workout,
        start=1,
    ):

        st.markdown(
            f"""
            <div class="card">
                <b>{number}. {exercise}</b><br>
                {sets} sets · {reps}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button(
        "✅ Mark workout complete",
        use_container_width=True,
    ):
        st.session_state.workout_done = True
        st.success("Workout completed!")

    if st.session_state.workout_done:
        st.success("Today's workout is recorded as completed.")


# ============================================================
# PROGRESS
# ============================================================

elif st.session_state.page == "Progress":

    st.title("📊 Progress")

    st.subheader("Add today's measurements")

    weight = st.number_input(
        "Weight (kg)",
        min_value=20.0,
        max_value=300.0,
        value=float(profile["weight"]),
    )

    waist = st.number_input(
        "Waist (cm)",
        min_value=30.0,
        max_value=250.0,
        value=80.0,
    )

    chest = st.number_input(
        "Chest (cm)",
        min_value=30.0,
        max_value=250.0,
        value=90.0,
    )

    if st.button("Save measurements"):
        st.session_state.measurements.append(
            {
                "date": str(date.today()),
                "weight": weight,
                "waist": waist,
                "chest": chest,
            }
        )

        st.success("Progress saved.")

    st.divider()

    if st.session_state.measurements:

        st.subheader("Weight history")

        for item in reversed(
            st.session_state.measurements
        ):
            st.write(
                f"**{item['date']}** — "
                f"{item['weight']} kg · "
                f"Waist {item['waist']} cm · "
                f"Chest {item['chest']} cm"
            )

    else:
        st.info(
            "Add your first measurement to start "
            "building your progress history."
        )

    st.divider()

    st.subheader("📸 Body Scan")

    st.info(
        "MVP limitation: an ordinary camera cannot reliably "
        "measure exact body dimensions in centimeters without "
        "calibration. Use this area for progress photos and "
        "manual measurements rather than fabricated measurements."
    )

    photo = st.camera_input(
        "Take a progress photo"
    )

    if photo:
        st.image(
            photo,
            caption="Progress photo",
            use_container_width=True,
        )


# ============================================================
# PROFILE
# ============================================================

elif st.session_state.page == "Profile":

    st.title("👤 My Profile")

    with st.form("profile_form"):

        name = st.text_input(
            "Name",
            value=profile["name"],
        )

        age = st.number_input(
            "Age",
            min_value=18,
            max_value=100,
            value=profile["age"],
        )

        sex = st.selectbox(
            "Sex",
            ["Male", "Female"],
            index=0 if profile["sex"] == "Male" else 1,
        )

        height = st.number_input(
            "Height (cm)",
            min_value=100,
            max_value=230,
            value=profile["height"],
        )

        weight = st.number_input(
            "Weight (kg)",
            min_value=30.0,
            max_value=250.0,
            value=float(profile["weight"]),
        )

        activity_options = [
            "Sedentary",
            "Lightly Active",
            "Moderately Active",
            "Very Active",
        ]

        activity = st.selectbox(
            "Activity level",
            activity_options,
            index=activity_options.index(
                profile["activity"]
            ),
        )

        diet_options = [
            "Vegetarian",
            "Vegan",
            "Non-vegetarian",
            "Egg vegetarian",
        ]

        diet = st.selectbox(
            "Diet",
            diet_options,
            index=(
                diet_options.index(profile["diet"])
                if profile["diet"] in diet_options
                else 2
            ),
        )

        body_options = [
            "Slim/Skinny",
            "Skinny Fat",
            "Average",
            "Athletic",
            "Muscular",
            "Higher Body Fat",
        ]

        body_type = st.selectbox(
            "Body type",
            body_options,
            index=(
                body_options.index(profile["body_type"])
                if profile["body_type"] in body_options
                else 2
            ),
        )

        goal_options = [
            "General Fitness",
            "Calisthenics",
            "Greek Body",
            "Aesthetic Body",
            "Muscle Gain",
            "Fat Loss",
            "Strength",
            "Recomposition",
        ]

        goal = st.selectbox(
            "Goal",
            goal_options,
            index=goal_options.index(
                profile["goal"]
            ),
        )

        budget = st.number_input(
            "Daily food budget",
            min_value=0,
            value=int(profile["budget"]),
        )

        submitted = st.form_submit_button(
            "Save profile",
            use_container_width=True,
        )

        if submitted:

            st.session_state.profile = {
                "name": name,
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

            st.success(
                "Profile updated. Your nutrition targets "
                "and workout will adapt."
            )

            st.rerun()

    st.divider()

    st.subheader("🎯 Your calculated targets")

    target_cols = st.columns(4)

    target_cols[0].metric(
        "Calories",
        f"{targets['calories']} kcal",
    )

    target_cols[1].metric(
        "Protein",
        f"{targets['protein']} g",
    )

    target_cols[2].metric(
        "Carbs",
        f"{targets['carbs']} g",
    )

    target_cols[3].metric(
        "Fat",
        f"{targets['fat']} g",
    )

    st.caption(
        "These are estimates for general fitness guidance, "
        "not medical prescriptions."
    )
