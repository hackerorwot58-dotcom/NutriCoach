You are a senior product architect, UX/UI designer, full-stack engineer, database architect, AI engineer, nutrition/fitness product engineer, security engineer, QA engineer, and DevOps engineer.

Build a production-quality web application called NUTRICOACH.

PRODUCT NAME:
NutriCoach

TAGLINE:
Your food. Your body. Your plan. One intelligent coach.

CORE PRODUCT IDEA:
NutriCoach is not a collection of disconnected tools. It is one connected personal intelligence system that understands:

WHO I AM
+
WHAT I WANT
+
WHAT I ATE
+
WHAT I DID
+
WHAT I HAVE LEFT
+
WHAT I CAN AFFORD
+
HOW I AM PROGRESSING
+
WHAT I PREFER

and converts that information into:

WHAT SHOULD I DO NEXT?

The application must feel modern, premium, simple, attractive, fast, intelligent, personalized, practical, trustworthy, mobile-first, and easy for beginners while still being powerful for advanced users.

DO NOT build a fake prototype.
DO NOT create static mock data pretending to be real.
DO NOT create fake AI.
DO NOT create fake camera measurements.
DO NOT create buttons that do nothing.
DO NOT artificially increase line count with useless code.
DO NOT build disconnected mini-apps.
Every important feature must have real state, real data flow, validation, error handling, or an explicitly labeled MVP limitation.

==================================================
1. CORE ARCHITECTURE
==================================================

Use this architecture:

USER
↓
AUTHENTICATION
↓
USER PROFILE
↓
PROFILE HISTORY
↓
GOAL ENGINE
↓
PREFERENCE / RESTRICTION ENGINE
↓
NUTRITION TARGET ENGINE
↓
DAILY STATE ENGINE
↓
┌─────────────────────────────────────────────┐
│ FOOD ENGINE        DIET ENGINE              │
│ WORKOUT ENGINE     WATER ENGINE             │
│ PROGRESS ENGINE    GROCERY ENGINE           │
│ SUPPLEMENT ENGINE  JOURNAL ENGINE           │
└──────────────────────┬──────────────────────┘
                       ↓
                 ANALYTICS ENGINE
                       ↓
                  SAFETY ENGINE
                       ↓
              RECOMMENDATION ENGINE
                       ↓
                    AI COACH
                       ↓
               NEXT BEST ACTION
                       ↓
                 USER DECISION
                       ↓
                   NEW DATA
                       ↓
                    HISTORY
                       ↓
                  ADAPTATION

The DATABASE is the source of truth.

AI is NOT the source of truth.

Deterministic engines must calculate trusted numbers and enforce hard constraints. AI should explain, personalize, summarize, and communicate those results.

==================================================
2. TECHNOLOGY STACK
==================================================

Use:

- Next.js
- React
- TypeScript
- Tailwind CSS
- PostgreSQL
- Prisma ORM
- Zod validation
- secure authentication/session system
- Recharts or equivalent chart library
- USDA FoodData Central API
- AI API
- private object storage for progress photos
- PWA support
- service worker where appropriate
- background jobs where required
- email provider
- push notification infrastructure where supported
- automated testing
- CI/CD
- monitoring/error tracking

Use a modular architecture.

Suggested structure:

/app
/components
/features
/lib
/services
/database
/api
/types
/validation
/hooks
/utils
/ai
/nutrition
/diet
/workout
/progress
/analytics
/grocery
/storage
/notifications
/security
/tests

Do not put the entire application into one giant component or file.

==================================================
3. PLATFORM
==================================================

Build a responsive web application for:

- mobile phones
- tablets
- laptops
- desktop computers

Mobile is a first-class experience.

Primary mobile navigation:

HOME
FOOD
WORKOUT
PROGRESS
PROFILE

Do not create unnecessary top-level navigation items.

Secondary functionality should be integrated naturally into these five areas.

==================================================
4. USER AGE AND SAFETY
==================================================

MVP is for adults 18+.

Do not automatically apply adult nutrition calculations to minors.

If minor support is added later, create a separate pediatric system with appropriate consent, rules, and calculations.

Do not diagnose medical conditions.

Do not make medical claims.

Nutrition and calorie targets must be presented as estimates and general guidance, not medical prescriptions.

==================================================
5. USER PROFILE
==================================================

Profile must support:

PERSONAL:
- name
- age
- sex
- height
- weight
- timezone
- language
- preferred units

DIET:
- vegetarian
- vegan
- non-vegetarian
- egg vegetarian
- food preferences
- disliked foods
- allergies
- intolerances
- religious/cultural restrictions
- custom restrictions

LIFESTYLE:
- activity level
- occupation/activity pattern
- cooking ability
- cooking frequency
- available equipment
- sleep information where provided

FINANCIAL:
- daily budget
- weekly budget
- monthly budget
- currency

BODY TYPE:
- Slim/Skinny
- Skinny Fat
- Average
- Athletic
- Muscular
- Higher Body Fat

"Skinny Fat" must be treated as a user-selected descriptive category, not a medical diagnosis.

GOALS:
- General Fitness
- Calisthenics
- Greek Body
- Aesthetic Body
- Muscle Gain
- Fat Loss
- Strength
- Recomposition

Each goal must have an explicit internal definition.

Do not allow AI to invent the meaning of a goal.

==================================================
6. GOAL HISTORY
==================================================

Never destroy historical goals.

Store:

Goal
GoalHistory
start_date
end_date
goal_version

Example:

Muscle Gain
→ Fat Loss

must preserve both historical periods.

When a goal changes:

- recalculate targets
- create a new target snapshot
- create a new diet plan version
- create a new workout plan version
- preserve all historical records
- explain what changed

==================================================
7. ONBOARDING
==================================================

Create a polished multi-step onboarding experience:

1. Welcome
2. Personal information
3. Height and weight
4. Activity level
5. Diet preference
6. Allergies/restrictions
7. Body type
8. Goal
9. Budget
10. Cooking ability
11. Available foods
12. Equipment
13. Meal preferences
14. Units/timezone
15. Review
16. Generate personalized plan

Save onboarding progress.

If the user leaves midway, resume later.

Do not ask unnecessary questions.

Explain why important information is required.

After onboarding:

PROFILE
↓
GOAL
↓
TARGETS
↓
14-DAY PLAN
↓
AUTOMATIC WORKOUT
↓
HOME DASHBOARD

==================================================
8. NUTRITION TARGET ENGINE
==================================================

Create a deterministic service:

NutritionTargetEngine

It must calculate:

BMR
→ activity-adjusted expenditure
→ goal adjustment
→ calorie target
→ protein target
→ fat target
→ carbohydrate target
→ fiber target
→ water target

The methodology must be explicitly documented.

Do not allow AI to calculate final trusted targets.

The engine must store:

formula_version
methodology_version
calculation_date
assumptions

Every important calculation must have a version.

Examples:

nutrition_formula_version
macro_formula_version
water_formula_version
workout_estimation_version
body_scan_model_version

Historical calculations must remain reproducible.

==================================================
9. SAFETY CONSTRAINT ENGINE
==================================================

Create:

SafetyConstraintEngine

It must detect potentially unsafe configurations such as:

- extreme calorie restriction
- unreasonable goal configuration
- excessive workout volume
- unsafe progression
- problematic supplement suggestions

If a configuration violates a safety rule:

- clearly explain the issue
- provide a safer alternative
- do not silently modify user values
- do not shame the user

Do not encourage starvation, punishment workouts, or dangerous weight loss.

==================================================
10. NUTRITION DATA REFERENCE SYSTEM
==================================================

Separate:

- food nutrient data
- nutrition calculation methodology
- dietary reference values
- application-specific estimates

Do not let AI decide official nutrition reference values.

Create a canonical nutrient schema.

Support:

energy_kcal
protein_g
carbohydrate_g
fat_g
fiber_g
sugar_g
saturated_fat_g
sodium_mg
calcium_mg
iron_mg
magnesium_mg
potassium_mg
zinc_mg
vitamin_a
vitamin_c
vitamin_d
vitamin_e
vitamin_k
and additional nutrients where available.

Every nutrient value must distinguish:

known
unknown
estimated
not_applicable

Never treat unknown as zero.

==================================================
11. DATABASE
==================================================

Use PostgreSQL + Prisma.

At minimum create models for:

User
Profile
Goal
GoalHistory

NutritionTarget
NutritionTargetSnapshot
CalculationVersion

Food
FoodNutrient
FoodSource
FoodServing
FoodEntry
FoodEntrySnapshot
FoodEntryRevision

Recipe
RecipeIngredient
RecipeVersion
RecipeServing
RecipeYield

MealPlan
MealPlanVersion
MealPlanDay
Meal
PlannedMeal
ActualMeal
MealDeviation

WorkoutPlan
WorkoutPlanVersion
WorkoutDay
Exercise
WorkoutExercise
WorkoutSession
WorkoutSessionExercise

WaterEntry

Measurement
MeasurementHistory

ProgressPhoto
BodyScan
BodyScanSession

Supplement
SupplementLog

GroceryList
GroceryItem
FoodPrice
InventoryItem

JournalEntry

DailyState
DailySummary

AIRecommendation
RecommendationFeedback
RecommendationEvent

Reminder
Notification

Achievement
UserAchievement
Streak

UserPreference
Consent
AuditLog

OnboardingProgress
UserEvent

Subscription
FeatureEntitlement

Integration
SyncEvent

Use appropriate foreign keys, indexes, unique constraints, timestamps, soft deletion where appropriate, and transactional integrity.

==================================================
12. SOURCE OF TRUTH
==================================================

Define one authoritative source for every important piece of data.

Examples:

Calories consumed
→ FoodEntry

Daily target
→ NutritionTargetSnapshot

Workout completion
→ WorkoutSession

Water consumed
→ WaterEntry

Weight
→ Measurement

AI recommendation
→ RecommendationEngine + AI explanation

Never maintain competing sources of truth.

==================================================
13. FOOD DATA PROVENANCE
==================================================

Every nutrition value must have a source.

Supported source types:

USDA
RecipeCalculated
UserEntered
Estimated
Imported

Store:

source_type
source_id
source_name
source_version
retrieved_at
confidence where applicable

Never fabricate nutrition data.

==================================================
14. USDA FOODDATA CENTRAL
==================================================

Integrate USDA FoodData Central.

API key must remain server-side.

Never expose it in frontend code.

Implement:

- search
- pagination
- filtering
- caching
- retries
- timeout handling
- rate-limit handling
- friendly errors
- source information

If USDA is unavailable:

- do not invent nutrition values
- show a useful error
- allow valid user-entered/custom food data if appropriate

==================================================
15. FOOD NORMALIZATION
==================================================

Create an internal food normalization layer.

External food data must map into the canonical nutrition schema.

Support food identity:

- name
- brand
- source
- source ID
- preparation
- raw/cooked state
- serving
- nutrient values

Handle duplicate/similar foods intelligently.

==================================================
16. RAW VS COOKED
==================================================

Explicitly distinguish:

raw
cooked
boiled
fried
grilled
baked
steamed
etc.

Do not silently treat raw and cooked weights as equivalent.

Where yield data exists, support:

raw_weight
cooked_weight
yield_factor

==================================================
17. SERVING ENGINE
==================================================

Support:

grams
kilograms
pieces
servings
bowls
cups
glasses
tablespoons
teaspoons
custom servings

Every conversion must be labeled:

Exact
Estimated
User-defined

Examples:

10 eggs
2 bananas
150g paneer
2 rotis
1 bowl rice

Allow users to override estimated serving weights.

==================================================
18. FOOD ENTRY SNAPSHOTS
==================================================

When a food is logged, save the nutrition snapshot used at that moment.

If USDA changes later, historical logs must not silently change.

Store:

food_id
source
nutrition_snapshot
serving_snapshot
calculation_version
created_at

==================================================
19. FOOD PAGE
==================================================

ALL food functionality must be merged into one powerful Food experience.

Do not create separate top-level pages for:

- food search
- food calculator
- diet
- meal swaps
- food history
- recipes
- micronutrients

They belong together.

Main flow:

SEARCH FOOD
↓
CHOOSE SERVING
↓
SEE NUTRITION
↓
ADD
↓
IMMEDIATELY SEE IMPACT ON TODAY
↓
SEE REMAINING TARGETS

Food page should include:

- search
- serving selector
- nutrition preview
- add to today
- remaining target impact
- personal calculator
- today's food
- planned diet
- meal swaps
- recipes
- saved meals
- quick add
- micronutrients
- grocery integration

==================================================
20. FOOD EXPERIENCE
==================================================

Example:

User searches:

Egg

Selects:

10 pieces

Show:

Calories
Protein
Carbs
Fat
Fiber

Then:

TODAY'S IMPACT

Calories +X
Protein +X
Carbs +X
Fat +X

REMAINING:

Calories X
Protein X
Carbs X
Fat X

Button:

ADD TO TODAY

Update DailyState immediately.

No unnecessary page reload.

==================================================
21. QUICK FOOD LOGGING
==================================================

Provide:

Recent
Favorites
Frequently eaten
Yesterday
Saved meals
Quick add

Allow users to save combinations.

Example:

"My usual breakfast"

3 eggs
2 rotis
curd
banana

One tap adds the entire meal.

==================================================
22. PERSONAL FOOD CALCULATOR
==================================================

Users can calculate food outside their planned diet.

Example:

250g rice
150g chicken
10g oil

Calculate:

total calories
protein
carbs
fat
fiber
micronutrients where available

Then show:

impact on today's remaining targets

Allow:

ADD TO TODAY

==================================================
23. RESTAURANT / ESTIMATED FOOD
==================================================

Allow users to log:

Restaurant meal
Homemade estimate
Unknown portion

Clearly label estimated values.

Never display estimated nutrition as exact laboratory data.

==================================================
24. RECIPES
==================================================

Recipes support:

ingredients
quantity
unit
raw/cooked state
recipe yield
total recipe weight
serving count
serving weight
nutrition
cost
prep time
cook time

Recipe nutrition is calculated from ingredients.

==================================================
25. RECIPE YIELD
==================================================

For foods such as:

rice
pasta
beans
lentils
meat

support:

raw weight
cooked weight
yield factor

A recipe must have a meaningful serving definition.

==================================================
26. OIL AND ADD-ONS
==================================================

Track:

oil
butter
sugar
sauces
dressings
spreads
toppings
other calorie-dense additions

Do not silently ignore these.

==================================================
27. PLANNED VS ACTUAL
==================================================

This is a first-class feature.

Example:

PLANNED:
150g paneer + 2 rotis

ACTUAL:
3 eggs + 3 rotis

Calculate:

planned nutrition
actual nutrition
difference
deviation

Use this for analytics and adaptation.

==================================================
28. MEAL ADHERENCE
==================================================

Meal state should support:

planned
completed
modified
skipped
replaced
unknown

Do not reduce the user to "success/failure".

==================================================
29. 14-DAY DIET PLAN
==================================================

Generate a personalized 14-day plan using:

- calorie target
- macro targets
- fiber
- diet preference
- allergies
- restrictions
- budget
- cooking ability
- available foods
- disliked foods
- meal frequency
- preferences
- workout schedule
- previous meals
- variety
- leftovers
- preparation time

Each day:

Breakfast
Lunch
Snack
Dinner
Optional pre-workout
Optional post-workout

Each meal:

ingredients
quantities
nutrition
cost
prep time
cook time

==================================================
30. DIET VALIDATION
==================================================

Before displaying a plan, validate:

allergies
diet compatibility
calorie range
protein range
macro consistency
fiber
budget
availability
variety
cooking complexity

If invalid:

regenerate or correct through deterministic logic.

Do not rely on AI alone for validation.

==================================================
31. PLAN VERSIONING
==================================================

Never overwrite old plans.

Use:

Plan v1
Plan v2
Plan v3

Store reason:

user_requested
goal_changed
budget_changed
progress_adaptation
food_availability
restriction_changed
preference_changed

Allow users to understand why a new plan was created.

==================================================
32. MEAL SWAPS
==================================================

Every planned meal should have:

SWAP MEAL

Swap engine must preserve:

calorie range
protein target
diet compatibility
allergies
budget
available foods
cooking time

Examples:

Paneer → tofu
Chicken → eggs
Rice → roti

==================================================
33. BUDGET ENGINE
==================================================

Track:

meal cost
daily cost
weekly cost
monthly cost
remaining budget

Every price should be labeled:

User-entered
Imported
Estimated

Never claim a local price is universally accurate.

==================================================
34. INVENTORY ENGINE
==================================================

Allow users to record foods they already have.

Example:

eggs
rice
oats
milk
dal

The diet and grocery engines should prioritize available inventory where possible.

==================================================
35. LEFTOVER ENGINE
==================================================

Use leftovers intelligently.

Example:

Cook 1kg chicken Monday.

Use remaining chicken Tuesday rather than unnecessarily generating another purchase.

==================================================
36. GROCERY ENGINE
==================================================

Automatically generate grocery lists from the meal plan.

Aggregate duplicate ingredients.

Example:

Eggs — 30
Rice — 2.5kg
Milk — 4L
Paneer — 1.2kg

Support:

check item
edit quantity
remove
add item
price
inventory status

==================================================
37. AUTOMATIC WORKOUT ENGINE
==================================================

The user should NOT need to manually select exercises to receive their planned workout.

Generate automatically using:

goal
experience
activity level
available equipment
schedule
previous workouts
progression
recovery
movement restrictions

Workout contains:

warm-up
main workout
cool-down

==================================================
38. WORKOUT SAFETY
==================================================

Track:

experience level
equipment
movement restrictions
injury constraints
exercise safety tags

Do not recommend exercises that conflict with explicit user restrictions.

==================================================
39. WORKOUT PROGRESSION
==================================================

Track:

exercise
sets
reps
weight
duration
difficulty
completion

Use deterministic progression rules.

Do not allow AI to randomly invent progression.

==================================================
40. WORKOUT TIMER
==================================================

Support:

workout timer
rest timer
set timer
exercise duration
completion tracking

Timers must actually function.

==================================================
41. WORKOUT CALORIE ESTIMATES
==================================================

If calories are estimated, display:

Estimated burn

not:

Exact calories burned

Store:

estimation_method
estimation_version
confidence

==================================================
42. RECOVERY
==================================================

Recovery recommendations must only use data actually available.

Potential inputs:

sleep
fatigue
soreness
training load
rest days
user feedback

Do not pretend to know recovery when the required data is unavailable.

==================================================
43. WATER
==================================================

Support:

glass
bottle
custom amount

Show:

daily target
consumed
remaining
progress

Allow reminders.

==================================================
44. SUPPLEMENTS
==================================================

Track optional supplements such as:

protein powder
creatine
multivitamin
omega-3
electrolytes

Do not make supplements mandatory.

Avoid unsupported medical claims.

Track:

name
dose
frequency
timing
taken
notes

==================================================
45. PROGRESS TRACKING
==================================================

Support:

weight
waist
chest
arms
legs
shoulders
custom measurements

Every measurement stores:

value
unit
date
method
source
notes

Sources:

manual
camera estimate
device
imported

Do not silently mix measurement types.

==================================================
46. PROGRESS HISTORY
==================================================

Preserve historical measurements.

If a user entered the wrong value, allow correction without corrupting the audit history.

Support:

daily
weekly
monthly
custom date range

==================================================
47. PROGRESS PHOTOS
==================================================

Support:

front
side
back

Allow:

side-by-side comparison
before/after
date comparison
slider/overlay where appropriate

==================================================
48. CAMERA BODY SCAN
==================================================

The camera feature must be honest.

It may estimate:

- pose
- posture indicators
- shoulder/waist proportion
- visual symmetry indicators
- body landmarks
- photo-to-photo trends

It must NOT claim exact:

- body fat percentage
- muscle mass
- waist centimeters
- medical conditions

from an ordinary camera without proper calibration.

Show clear labels:

Estimated
Confidence
Not a medical measurement

==================================================
49. BODY SCAN DATA
==================================================

Store:

capture_type
camera_permission
pose_quality
image_quality
calibration_status
model_version
confidence
created_at

==================================================
50. CAMERA PRIVACY
==================================================

Progress photos are private sensitive data.

Implement:

private object storage
encryption
signed access
strict authorization
EXIF stripping
image validation
file-size limits
retention controls
deletion
processing consent

If a third-party computer vision provider receives images, clearly disclose this.

==================================================
51. ANALYTICS
==================================================

Nutrition:

calories vs target
protein vs target
carbs vs target
fat vs target
fiber
micronutrient trends

Body:

weight trend
waist trend
measurements

Water:

hydration trend

Workout:

sessions
duration
completion
progression

Adherence:

meal adherence
workout adherence
hydration adherence
logging consistency

==================================================
52. HISTORICAL ANALYTICS
==================================================

Always use the target active on that historical date.

Example:

January target = 2400
March target = 2200

January analytics must compare against 2400.

Never recalculate historical adherence using today's target.

==================================================
53. DAILY SUMMARY
==================================================

At the end of the day show:

Calories
Protein
Water
Workout
Meals
Adherence
Main nutrition gaps
Next recommendation

Use encouraging factual language.

==================================================
54. WEEKLY REVIEW
==================================================

Show:

what went well
nutrition trend
workout trend
water trend
weight trend
waist trend
main gap
next week's focus

Do not shame users.

==================================================
55. JOURNAL
==================================================

Allow:

notes
energy
hunger
sleep
stress
mood
cravings
training notes

These are user-reported observations.

Do not convert them into medical diagnoses.

==================================================
56. RECOMMENDATION ENGINE
==================================================

Create a deterministic:

RecommendationEngine

Priority:

1. Safety
2. Allergies/restrictions
3. Major nutrition gap
4. Hydration
5. Planned meal
6. Workout
7. Recovery
8. Budget
9. Preferences
10. Variety

Return one primary:

NEXT BEST ACTION

Optionally return secondary actions.

Every recommendation must include:

WHAT
WHY
HOW

==================================================
57. RECOMMENDATION PROVENANCE
==================================================

Store:

recommendation_id
daily_state_version
reason_codes
source_food_ids
source_recipe_ids
engine_version
created_at
expires_at
status
accepted_at
dismissed_at

The user should be able to understand:

"Why did NutriCoach recommend this?"

==================================================
58. RECOMMENDATION EXPIRATION
==================================================

Recommendations must not remain indefinitely valid.

Support:

created_at
expires_at
status
accepted_at
dismissed_at

Recalculate when daily state significantly changes.

==================================================
59. AI COACH
==================================================

AI Coach is a personalization and communication layer.

AI receives structured trusted context:

profile summary
current goal
current targets
today's food
remaining nutrition
water
workout
budget
restrictions
available foods
recent progress
recommendation engine result

Do NOT send the entire database blindly.

==================================================
60. AI MUST NOT CALCULATE TRUSTED DATA
==================================================

AI must not be the authoritative source for:

calories
nutrition totals
nutrition targets
allergy validation
budget totals
workout safety
database state
historical measurements

Deterministic systems provide these.

AI explains them.

==================================================
61. AI TOOLS
==================================================

Provide controlled functions/tools such as:

getDailyState()
searchFoods()
getFoodNutrition()
getRecipes()
getMealPlan()
getBudget()
getRestrictions()
getWorkout()
getProgress()

AI should select real food/recipe IDs.

Never allow it to invent IDs or nutrition numbers.

==================================================
62. AI OUTPUT VALIDATION
==================================================

Use structured JSON schema.

Validate:

schema
data types
ranges
food IDs
recipe IDs
allergy constraints
budget constraints
nutrition constraints
recommendation priority

Reject invalid outputs.

Use deterministic fallback.

==================================================
63. AI FAILURE
==================================================

If AI:

times out
fails
reaches quota
returns invalid output

NutriCoach must still work.

Show a deterministic recommendation based on DailyState.

Never let AI availability determine whether the core application works.

==================================================
64. AI PROMPT INJECTION SECURITY
==================================================

Treat all user-generated text as untrusted.

Examples:

journal text
food names
recipe names
notes

must never be able to override trusted system instructions.

Separate trusted system context from untrusted user content.

==================================================
65. AI PRIVACY
==================================================

Document:

what data is sent to AI
what data is not sent
whether images are sent
provider
retention
logging
opt-out controls

Send only the minimum required context.

==================================================
66. FOOD ALLERGY ENGINE
==================================================

Allergy validation happens before AI recommendations.

If user has:

Peanut allergy

the recommendation engine must block peanut-containing foods.

AI cannot override allergy constraints.

==================================================
67. DIET RESTRICTION ENGINE
==================================================

Support:

vegetarian
vegan
non-vegetarian
egg vegetarian
custom restrictions

Restrictions must be deterministic.

==================================================
68. CONFLICT RESOLUTION
==================================================

If sources disagree:

USDA
vs
user recipe
vs
estimated

use a documented source hierarchy.

Never silently alter historical nutrition.

==================================================
69. HOME DASHBOARD
==================================================

Home is the personalized command center.

Header:

Good morning/afternoon/evening, [Name]
Goal: [Goal]

Show:

Today's calories
Protein
Carbs
Fat
Fiber
Water

Main visual:

clean calorie and macro progress

AI centerpiece:

🧠 YOUR NEXT BEST ACTION

Example:

You're approximately 42g short on protein and have 680 kcal remaining.

Budget option:
200g curd + roasted chana + 2 rotis

Vegetarian option:
150g paneer + 2 rotis + salad

Vegan option:
soy chunks + rice + vegetables

Why:
Protein is currently your largest nutrition gap.

Buttons:

Do it
Swap
Later
Not relevant

Also show:

Today's food
Water
Automatic workout
Progress snapshot

==================================================
70. HOME MUST ADAPT DURING THE DAY
==================================================

Morning:

Today's plan

After breakfast:

Lunch recommendation

After workout:

Recovery recommendation

Evening:

Remaining nutrition recommendation

The dashboard should react to the user's current state.

Do not show the same static content all day.

==================================================
71. FOOD UX
==================================================

Food should feel like a personal nutrition calculator, not a database search page.

Main interaction:

Search
→ serving
→ nutrition
→ add
→ immediate daily impact

Keep everything else secondary.

==================================================
72. WORKOUT UX
==================================================

Show:

Today's automatic workout
Why this workout
Warm-up
Exercises
Sets/reps
Rest
Timer
Completion
Progress

The user should not need to design their own workout.

==================================================
73. PROGRESS UX
==================================================

Show:

weight
waist
measurements
charts
photos
camera scan
milestones
trends

Avoid overwhelming the user with excessive charts.

==================================================
74. PROFILE UX
==================================================

Profile contains:

personal information
diet
goal
budget
restrictions
preferences
units
notifications
privacy
account

Do not scatter these settings throughout the app.

==================================================
75. SAVED MEALS
==================================================

Allow users to:

save
rename
edit
duplicate
add to today

Saved meals should be integrated into Food.

==================================================
76. ACHIEVEMENTS
==================================================

Support positive achievements:

7-day logging streak
10 workouts completed
100 meals logged
hydration consistency
protein consistency

Never reward:

lowest calorie intake
extreme weight loss
excessive exercise
skipping meals

==================================================
77. GAMIFICATION SAFETY
==================================================

Do not create incentives for:

starvation
dangerous weight loss
excessive exercise
ignoring hunger
obsessive tracking

==================================================
78. NOTIFICATIONS
==================================================

Support:

water reminder
meal reminder
workout reminder
weekly review
important account notifications

Users control notification preferences.

Track delivery state where appropriate:

queued
sent
failed
opened
dismissed

==================================================
79. EMAIL
==================================================

Support infrastructure for:

email verification
password reset
important security notifications

==================================================
80. CALENDAR / HISTORY
==================================================

Provide:

Day
Week
Month

Allow inspection of:

food
workouts
water
measurements
plans
recommendations

==================================================
81. USER CONTROL
==================================================

Users can:

edit
delete
undo
replace
skip
correct
change goal
change budget
change preferences
change restrictions

AI cannot silently modify user data.

==================================================
82. FEEDBACK LOOP
==================================================

Every recommendation supports:

Accept
Modify
Skip
Replace
Not relevant
Too expensive
Don't like it
Already did this
Not available
Wrong portion
Other

Use feedback for future personalization.

==================================================
83. EVENT HISTORY
==================================================

Important changes must be historically traceable:

weight changed
goal changed
target changed
diet preference changed
budget changed
plan changed
measurement corrected
food corrected

Do not destroy historical context.

==================================================
84. TIMEZONE
==================================================

Store timestamps in UTC.

Interpret daily dates using the user's timezone.

A meal at 11:30 PM must belong to the correct user-local day.

==================================================
85. UNITS
==================================================

Normalize internally.

Display according to user preference.

Support:

kg/lb
cm/ft-in
g/oz
ml/fl oz
currency

Do not mix units internally.

==================================================
86. OFFLINE/PWA
==================================================

If offline support is implemented, provide:

offline indicator
pending sync
sync success
sync failure
conflict handling

Never silently lose offline data.

==================================================
87. DUPLICATE PROTECTION
==================================================

Double-clicking Add Food must not create duplicate entries.

Use:

idempotency keys
unique constraints
transactions

==================================================
88. CONCURRENCY
==================================================

Handle:

multiple browser tabs
phone + laptop
simultaneous edits
duplicate requests

Use appropriate concurrency controls.

==================================================
89. TRANSACTIONS
==================================================

Operations affecting multiple systems must be transactional.

Example:

Add food
→ FoodEntry
→ DailyState
→ recommendation invalidation/recalculation

must not leave partial state.

==================================================
90. SECURITY
==================================================

Implement:

secure authentication
password hashing
secure sessions
secure cookies
authorization
user data isolation
input validation
rate limiting
CSRF protection where applicable
security headers
upload validation
secret management
ORM/database protection
audit logging

Test cross-user access.

==================================================
91. PRIVACY
==================================================

Provide:

data export
account deletion
photo deletion
privacy controls
AI processing preferences
camera consent
notification consent

Do not claim GDPR/HIPAA/DPDP compliance merely because security features exist.

Perform actual compliance assessment according to jurisdiction, business model, and data flows.

==================================================
92. CONSENT
==================================================

Track:

consent_type
policy_version
accepted_at
revoked_at

for relevant permissions.

==================================================
93. PHOTO STORAGE
==================================================

Use private object storage.

Implement:

upload validation
size limits
supported formats
compression
thumbnail generation
EXIF stripping
encryption
signed access
authorization
deletion
retention controls

==================================================
94. API
==================================================

Use clear API contracts.

Define:

request schema
response schema
authentication
authorization
validation
pagination
errors
rate limits
idempotency
versioning

Use Zod and OpenAPI-compatible documentation where appropriate.

==================================================
95. SEARCH
==================================================

Food search should support common terms and variations.

Examples:

egg
eggs
boiled egg
banana
rice
chicken breast
paneer
dal
roti
chapati

Eventually support localized/vernacular search.

==================================================
96. INDIA-FRIENDLY EXPERIENCE
==================================================

Support Indian foods naturally:

roti
chapati
dal
rice
poha
upma
idli
dosa
paneer
curd
chana
rajma
soy chunks

Support household units:

katori
glass
bowl
piece

Keep the architecture internationally extensible.

==================================================
97. LOCALIZATION
==================================================

Architecture must support:

English
Hindi
future languages

Use translation keys.

Support locale-aware:

dates
numbers
currency
pluralization

Do not hardcode language strings throughout components.

==================================================
98. BODY GOALS
==================================================

Goals such as:

Greek Body
Aesthetic Body

must map to explicit system behavior.

Define:

training emphasis
nutrition emphasis
progress metrics

Do not promise a specific appearance.

==================================================
99. LANGUAGE / UX SAFETY
==================================================

Never use shame-based language.

Avoid:

You failed.
You ate badly.
You ruined your diet.
Punish yourself.

Use:

Your intake was different from the plan.
Here's the best next step.

==================================================
100. ERROR STATES
==================================================

Every major operation needs a designed error state.

Examples:

USDA unavailable
AI unavailable
photo upload failed
database unavailable
sync failed
notification failed

Never expose raw stack traces to users.

==================================================
101. LOADING STATES
==================================================

Use:

skeletons
progress indicators
optimistic UI only where safe

Do not freeze the interface.

==================================================
102. EMPTY STATES
==================================================

Examples:

No food:
"Your food log is empty. Add your first meal."

No measurements:
"Add your first measurement to start your progress trend."

No photos:
"Take your first progress photo."

==================================================
103. ACCESSIBILITY
==================================================

Target WCAG 2.2 AA.

Implement:

keyboard navigation
screen reader labels
semantic HTML
visible focus states
adequate contrast
reduced motion
accessible forms
accessible errors
accessible charts
touch-friendly controls
do not rely on color alone

==================================================
104. VISUAL DESIGN
==================================================

Visual style:

modern
premium
clean
minimal
fitness-focused
slightly futuristic
professional

Avoid:

childish UI
excessive gradients
excessive cards
clutter
giant unnecessary typography
fake AI decoration
unnecessary animation

Animations should improve comprehension.

==================================================
105. MOBILE UX
==================================================

Prioritize:

thumb reach
large touch targets
fast food logging
quick water logging
quick workout start
easy camera capture
minimal typing

==================================================
106. CAMERA EXPERIENCE
==================================================

Make camera scan feel futuristic but honest:

BODY SCAN

Front
Side
Back

Preparing scan...
Pose detected...
Photo quality: Good

Estimated:
Shoulder/waist proportion
Posture indicators
Progress comparison

Clearly display:

These are estimates and are not medical measurements.

==================================================
107. PRODUCT ANALYTICS
==================================================

Track product events such as:

signup_completed
onboarding_completed
food_added
meal_completed
workout_completed
recommendation_accepted
recommendation_rejected
plan_generated

Do not send sensitive health/body data to analytics systems unnecessarily.

Minimize data collection.

==================================================
108. PERFORMANCE
==================================================

Optimize:

database queries
USDA requests
AI calls
images
charts
mobile loading
caching

Do not load entire historical datasets unnecessarily.

Use pagination.

==================================================
109. CACHING
==================================================

Cache safe external data where appropriate.

Never allow cached data to leak between users.

Private:

profiles
daily states
recommendations
photos
journal

must remain user-isolated.

==================================================
110. DATABASE MIGRATIONS
==================================================

Use Prisma migrations.

Separate:

development
staging
production

Never experiment directly against production.

==================================================
111. BACKUPS
==================================================

Production must have:

automated backups
retention policy
point-in-time recovery where available
restore testing
disaster recovery procedure

==================================================
112. CI/CD
==================================================

Before deployment run:

format
lint
typecheck
unit tests
integration tests
E2E tests
security checks
build
migration validation

Production deployment must be repeatable.

==================================================
113. TESTING
==================================================

Unit test:

BMR
TDEE
macro calculations
fiber
water
food scaling
piece conversion
raw/cooked conversion
recipe calculation
budget
allergy filtering
diet validation
meal swaps
target snapshots
goal transitions
DailyState
timezone
duplicate protection
workout progression
recommendation priority
AI validation

==================================================
114. SECURITY TESTING
==================================================

Test:

cross-user access
unauthorized API access
invalid tokens
rate limits
malicious uploads
prompt injection
SQL injection attempts
permission escalation
private photo access
account deletion

==================================================
115. END-TO-END TEST
==================================================

Test:

SIGN UP
↓
ONBOARDING
↓
GENERATE PLAN
↓
HOME
↓
SEARCH FOOD
↓
ADD FOOD
↓
DAILY STATE UPDATES
↓
REMAINING TARGET UPDATES
↓
RECOMMENDATION CHANGES
↓
ACCEPT RECOMMENDATION
↓
WORKOUT GENERATED
↓
COMPLETE WORKOUT
↓
ADD WATER
↓
ADD MEASUREMENT
↓
WEEKLY ANALYTICS

This must function as one connected system.

==================================================
116. CRITICAL TEST CASES
==================================================

TEST 1:
User adds 10 eggs.

Expected:
FoodEntry created.
DailyState updates.
Calories update.
Protein updates.
Home updates.
Recommendation context updates.

TEST 2:
User has peanut allergy.

Expected:
Peanut recommendation blocked.

TEST 3:
AI fails.

Expected:
App continues using deterministic recommendation.

TEST 4:
USDA fails.

Expected:
Friendly error.
No fabricated nutrition values.

TEST 5:
User double-clicks Add.

Expected:
Only one food entry.

TEST 6:
Target changes.

Expected:
New target snapshot.
Historical targets remain unchanged.

TEST 7:
User A attempts User B's data.

Expected:
Access denied.

TEST 8:
User deletes account.

Expected:
Deletion workflow processes all applicable data.

==================================================
117. PRODUCT ANALYTICS / HISTORY
==================================================

Preserve enough historical data to understand:

what the user planned
what they actually did
what recommendation was given
why it was given
what they chose
what happened afterward

This enables meaningful adaptation.

==================================================
118. ADAPTIVE SYSTEM
==================================================

NutriCoach may adapt when:

weight trend changes
goal changes
budget changes
food preferences change
user repeatedly skips meals
user repeatedly replaces meals
workout performance changes
equipment changes
feedback changes

Adaptation must be:

explainable
versioned
reversible
controlled

Never silently change major targets.

==================================================
119. HOME EXPERIENCE EXAMPLE
==================================================

Example:

Good evening, Praveen

Your goal:
Muscle Gain

TODAY

2,150 / 2,500 kcal
112 / 150g protein
5 / 8 glasses water

WORKOUT
Upper Body
Completed

AI COACH

You're currently about 38g short on protein.

You have enough calorie room for a protein-focused meal.

Budget option:
curd + roasted chana + roti

Vegetarian:
paneer + roti + salad

Vegan:
soy chunks + rice + vegetables

WHY:
Protein is currently your largest nutrition gap.

[Do it]
[Swap]
[Later]

The actual numbers must come from the user's real DailyState.

==================================================
120. NO FAKE INTELLIGENCE
==================================================

If a feature is rule-based, do not falsely describe it as advanced AI.

A rule-based recommendation engine is acceptable and useful.

The ideal architecture is:

trusted data
+
deterministic engines
+
recommendation engine
+
AI explanation/personalization

==================================================
121. NO FAKE MEASUREMENTS
==================================================

Never produce precise body measurements from ordinary photos without appropriate calibration.

Never claim exact body fat from a normal camera.

Never fabricate progress.

==================================================
122. NO FAKE DATA
==================================================

Mock data may exist during development, but production must clearly use real user data.

Never show fake statistics as real user results.

==================================================
123. NO FAKE COMPLETION
==================================================

A button should only show completed after backend confirmation.

==================================================
124. ADMIN SYSTEM
==================================================

If admin functionality is built:

Use role-based permissions.

Follow least privilege.

Administrators must not automatically have unrestricted access to private nutrition/body/photo information.

Log support/admin access.

==================================================
125. FEATURE FLAGS
==================================================

Support feature flags for:

AI Coach
Camera Scan
Wearables
Hindi
New Diet Engine
New Workout Engine
experimental features

==================================================
126. SUBSCRIPTION ARCHITECTURE
==================================================

Even if payment is not initially implemented, separate:

subscription
entitlement
feature access
usage limits

from core business logic.

==================================================
127. AI COST CONTROL
==================================================

Track:

AI requests
token usage
estimated cost
per-user usage
daily limits

Use deterministic caching where appropriate.

==================================================
128. USDA COST/RATE CONTROL
==================================================

Track:

request count
cache hits
cache misses
rate limits
errors

==================================================
129. OBSERVABILITY
==================================================

Production needs:

structured logs
error tracking
performance monitoring
API latency
database latency
AI failures
USDA failures
notification failures

Never log secrets.

Minimize sensitive information in logs.

==================================================
130. LANDING PAGE
==================================================

Create a polished public landing page.

Sections:

Hero
How it works
Food intelligence
Automatic workouts
Progress tracking
AI Coach
Camera progress
Personalized diet
Budget/grocery
Privacy
FAQ
Sign up
Login

Hero message should communicate:

"Your food. Your body. Your plan. One intelligent coach."

Primary CTA:

Start Your Plan

Secondary CTA:

See How It Works

Do not overwhelm the landing page.

==================================================
131. FIRST-DAY EXPERIENCE
==================================================

New users should not see an empty/broken dashboard.

After onboarding show:

Your plan is ready.
Your first workout is ready.
Your nutrition targets are ready.
Add your first meal to begin.

==================================================
132. SAVED PREFERENCES
==================================================

Users may say:

Replace paneer with tofu whenever possible.

Store this as a preference.

Likewise:

I don't like oats.
I prefer rice.
I cook only twice per week.

Use these preferences in future plans.

==================================================
133. FOOD AVAILABILITY
==================================================

Support user availability:

available
unavailable
seasonal
inventory

Diet generation should respect available foods when possible.

==================================================
134. MEAL PREP
==================================================

Eventually support:

cook once
eat multiple meals

Example:

Sunday batch preparation
→ Monday/Tuesday meals

This should reduce cost and cooking burden.

==================================================
135. REAL-LIFE FLEXIBILITY
==================================================

Users will not follow plans perfectly.

Support:

restaurant meal
travel
festival
birthday
social meal
unexpected food
missed workout

Do not treat deviation as failure.

Help the user return to the plan.

==================================================
136. SLEEP / ACTIVITY INTEGRATION
==================================================

Future integrations should distinguish:

manual data
device data
estimated data
imported data

Do not mix them silently.

==================================================
137. DATA QUALITY
==================================================

Important values should have:

source
timestamp
version
confidence where applicable

This is essential for user trust.

==================================================
138. PRIVACY BY DESIGN
==================================================

Collect only data needed for product functionality.

Do not collect sensitive information merely because it could be useful someday.

==================================================
139. FINAL ARCHITECTURAL PRINCIPLE
==================================================

Do not build the product in this way:

Profile UI
+
Food UI
+
Workout UI
+
AI UI

and connect them later.

Build:

DATABASE
↓
DOMAIN MODELS
↓
DOMAIN ENGINES
↓
DAILY STATE
↓
ANALYTICS
↓
RECOMMENDATION
↓
AI
↓
API
↓
UI

The UI should consume trusted application state.

==================================================
140. DEVELOPMENT PHASES
==================================================

PHASE 1:
Foundation

- project
- authentication
- database
- Prisma
- profile
- security
- design system

PHASE 2:
Core Intelligence

- Goal Engine
- Nutrition Target Engine
- Target Snapshots
- DailyStateEngine
- Safety Engine

PHASE 3:
Food

- USDA
- food search
- serving engine
- food logging
- personal calculator
- recipes
- planned vs actual

PHASE 4:
Diet

- 14-day planner
- validation
- swaps
- budget
- grocery
- inventory
- leftovers

PHASE 5:
Workout

- automatic workout
- progression
- timers
- completion
- recovery

PHASE 6:
Progress

- measurements
- charts
- photos
- camera scan framework

PHASE 7:
Intelligence

- RecommendationEngine
- AI Coach
- AI tools
- validation
- feedback
- adaptation

PHASE 8:
Product Polish

- notifications
- PWA
- offline
- localization
- accessibility
- achievements
- performance

PHASE 9:
Production

- CI/CD
- monitoring
- backups
- security testing
- E2E testing
- privacy
- deployment

==================================================
141. DEFINITION OF DONE
==================================================

NutriCoach is not considered complete until:

Authentication works.
Onboarding works.
Profile works.
Goal engine works.
Nutrition target engine works.
Target snapshots work.
Food search works.
USDA works.
Serving conversion works.
Food logging works.
Food editing works.
Food deletion works.
Undo works.
DailyState updates immediately.
Personal calculator works.
Recipes work.
Planned vs actual works.
14-day plans work.
Meal swaps work.
Budget works.
Grocery works.
Inventory works.
Automatic workout works.
Workout timer works.
Workout progression works.
Water works.
Supplements work.
Measurements work.
Progress photos work.
Camera scan is honestly labeled.
Analytics work.
Weekly review works.
AI Coach works.
AI fallback works.
Recommendation provenance works.
Feedback loop works.
Notifications work where implemented.
PWA works where implemented.
Offline sync is safe where implemented.
Privacy controls work.
Account deletion works.
Data export works.
Authorization is tested.
Cross-user access is blocked.
Database migrations work.
Backups exist.
Monitoring exists.
Accessibility target is implemented.
Mobile UI is polished.
E2E tests pass.

==================================================
142. FINAL USER JOURNEY
==================================================

The complete experience should be:

SIGN UP
↓
ONBOARDING
↓
PROFILE
↓
GOAL
↓
NUTRITION TARGETS
↓
PERSONALIZED 14-DAY DIET
↓
AUTOMATIC WORKOUT
↓
HOME
↓
FOOD SEARCH
↓
SERVING
↓
NUTRITION PREVIEW
↓
ADD FOOD
↓
DAILY STATE UPDATES
↓
REMAINING TARGET UPDATES
↓
RECOMMENDATION UPDATES
↓
AI COACH EXPLAINS
↓
USER ACCEPTS / MODIFIES / SKIPS
↓
WATER + MEALS + WORKOUT
↓
PROGRESS
↓
ANALYTICS
↓
WEEKLY REVIEW
↓
ADAPTATION
↓
NEW PLAN

Everything is connected.

==================================================
143. MOST IMPORTANT RULES
==================================================

1. Correctness > feature count.
2. Real functionality > fake UI.
3. Data integrity > AI creativity.
4. Deterministic calculations > LLM calculations.
5. User control > automation.
6. Safety > engagement.
7. Privacy > unnecessary data collection.
8. Historical accuracy > convenience.
9. Simple UX > feature clutter.
10. Mobile experience is first-class.
11. Every important number must have a source.
12. Every recommendation must have a reason.
13. Every important change must be reversible or historically traceable.
14. Never claim precision the system does not have.
15. Never fabricate nutrition, measurements, progress, or AI results.
16. Never silently override allergies or restrictions.
17. Never allow AI to become the database source of truth.
18. Never let one user's data leak to another user.
19. Never make users feel punished for normal real-life deviations.
20. Do not optimize for line count.

==================================================
144. FINAL PRODUCT DEFINITION
==================================================

NutriCoach is a personal intelligence system that continuously combines:

USER PROFILE
+
GOALS
+
NUTRITION
+
FOOD
+
WORKOUTS
+
HYDRATION
+
BUDGET
+
PREFERENCES
+
MEASUREMENTS
+
PROGRESS
+
HISTORY

to determine:

THE SAFEST AND MOST USEFUL NEXT BEST ACTION.

The system should understand what the user planned, what the user actually did, what has changed, what remains, and what action is most useful now.

The application should continuously learn from user corrections, choices, preferences, and progress without silently changing important information.

The final experience should make the user feel:

"This app actually knows where I am today, what I am trying to achieve, what I have already done, what I have left, and what I should do next."

BUILD NUTRICOACH AS ONE CONNECTED INTELLIGENCE SYSTEM.

DO NOT BUILD IT AS A COLLECTION OF FEATURES.

PRIORITIZE:
ARCHITECTURE
DATA INTEGRITY
SAFETY
SECURITY
PRIVACY
CORRECTNESS
PERFORMANCE
ACCESSIBILITY
MOBILE UX
USER TRUST
REAL FUNCTIONALITY

Do not artificially inflate code size.

A smaller, clean, correctly architected system is better than thousands of lines of duplicate or fake code.
