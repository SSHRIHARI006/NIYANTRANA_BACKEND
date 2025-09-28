import pandas as pd
from Train import Train
from datetime import date, timedelta
from typing import List
import pulp
import random
from prediction_pipeline import PredictionPipeline # Import the reusable class

# --- 1. Main Configuration Block ---
# --- System Parameters ---
TOTAL_TRAINS = 25
PROTOTYPE_RUN_DATE = date(2026, 1, 28) # Must match the end date of your historical data

# --- Optimization Parameters ---
SERVICE_PICK_COUNT = 15
STANDBY_PICK_COUNT = 5

# --- MILP Objective Function Weights (Tunable) ---
BETA_BRANDING = 0.60         # Reward for branding urgency
ALPHA_MILEAGE = 0.25         # Penalty for high mileage
GAMMA_FAILURE_RISK = 1.20    # Penalty for high AI-predicted failure risk
DELTA_DIRTINESS = 0.40       # Penalty for high AI-predicted dirtiness

# --- Historical Data File Paths ---
HISTORICAL_MAINTENANCE_DATA = 'Predictive_Maintenance_Training_Data.csv'
HISTORICAL_CLEANING_DATA = 'Deep_Cleaning_Training_Data.csv'

# --- Maintenance Model Artifact Paths ---
MAINTENANCE_MODEL_PATH = 'bidirectional_gru_maintenance_model.h5'
MAINTENANCE_FEATURE_SCALER = 'feature_scaler.pkl'
MAINTENANCE_TARGET_SCALER = 'target_scaler.pkl'

# --- Cleaning Model Artifact Paths ---
CLEANING_MODEL_PATH = 'bidirectional_gru_cleaning_model.h5'
CLEANING_FEATURE_SCALER = 'cleaning_feature_scaler.pkl'
CLEANING_TARGET_SCALER = 'cleaning_target_scaler.pkl'


# --- 2. Core Data Structure ---

# --- 3. Scoring and Helper Functions ---
def get_branding_score(train: Train, ws=0.6, wu=0.4):
    """Calculates a score for branding urgency and completion."""
    if not train.has_branding or not train.branding_expiry_date or train.branding_days_required == 0:
        return 0.0
    needed = max(0, train.branding_days_required - train.branding_days_completed)
    if needed == 0: return 0.0
    days_left = (train.branding_expiry_date - PROTOTYPE_RUN_DATE).days
    if days_left <= 0: return 1.0
    shortfall_score = needed / train.branding_days_required
    required_rate = needed / days_left
    urgency_score = min(1.0, required_rate)
    score = (shortfall_score * ws) + (urgency_score * wu)
    return min(1.0, max(0.0, score))

def get_mileage_score(train: Train):
    """Normalizes the monthly mileage to a 0-1 penalty score."""
    MAX_MONTHLY_KMS = 9000
    return min(1.0, train.mileage_kms_this_month / MAX_MONTHLY_KMS)

def get_static_train_features(train_id):
    """Generates the non-AI features like branding and mileage for a train."""
    is_fit = random.random() > 0.1 # 90% chance of being fit
    mileage_this_month = random.randint(2000, 7500)
    has_branding = random.random() < 0.4
    branding_days_completed, branding_days_required, branding_expiry = 0, 0, None
    if has_branding:
        branding_days_completed = random.randint(5, 25)
        days_remaining = random.randint(2, 30)
        branding_days_required = branding_days_completed + days_remaining
        branding_expiry = PROTOTYPE_RUN_DATE + timedelta(days=days_remaining)
    return {
        'is_fit_for_service': is_fit, 'mileage_kms_this_month': mileage_this_month,
        'has_branding': has_branding, 'branding_days_completed': branding_days_completed,
        'branding_days_required': branding_days_required, 'branding_expiry_date': branding_expiry
    }


# --- 4. The Core MILP Optimization Engine ---
def run_optimization(all_trains: List[Train]):
    """
    Takes a list of Train objects and assigns them to 'SERVICE', 'STANDBY',
    or 'MAINTENANCE' using a two-stage filtering and optimization process.
    """
    eligible_for_service = []
    maintenance_trains = []

    # Stage 1: Hard-coded business rules for absolute filtering
    print("\n--- Stage 1: Applying Hard Business Rules ---")
    for train in all_trains:
        if (not train.is_fit_for_service or
            train.predicted_failure_risk > 0.75 or # Critical risk threshold
            train.predicted_dirtiness_score > 0.85): # Extremely dirty threshold
            train.status = "MAINTENANCE"
            maintenance_trains.append(train)
        else:
            eligible_for_service.append(train)
    print(f"Result: {len(maintenance_trains)} trains assigned to Maintenance.")
    
    # Stage 2: MILP Optimization for the remaining eligible pool
    print("\n--- Stage 2: Running MILP Optimization ---")
    model = pulp.LpProblem("Select_Trains_for_Service", pulp.LpMaximize)
    y = pulp.LpVariable.dicts("y", {t.train_id: t for t in eligible_for_service}, cat="Binary")
    
    objective_terms = []
    for train in eligible_for_service:
        score = (BETA_BRANDING * get_branding_score(train)) - \
                (ALPHA_MILEAGE * get_mileage_score(train)) - \
                (GAMMA_FAILURE_RISK * train.predicted_failure_risk) - \
                (DELTA_DIRTINESS * train.predicted_dirtiness_score) + \
                (train.train_id * 1e-6) # Tie-breaker
        objective_terms.append(score * y[train.train_id])

    model += pulp.lpSum(objective_terms)
    model += pulp.lpSum([y[train.train_id] for train in eligible_for_service]) == SERVICE_PICK_COUNT
    model.solve(pulp.PULP_CBC_CMD(msg=False))
    
    service_trains, standby_trains = [], []
    for train in eligible_for_service:
        if pulp.value(y[train.train_id]) > 0.5:
            train.status = "SERVICE"
            service_trains.append(train)
        else:
            train.status = "STANDBY"
            standby_trains.append(train)
            
    print("Result: Optimization complete.")
    return service_trains, standby_trains, maintenance_trains