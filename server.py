from flask import Flask , request, session, redirect, url_for
from dotenv import load_dotenv, find_dotenv
from datetime import timedelta, datetime

from mongoManager import DBMngr
from flask_cors  import cross_origin, CORS
from Train import Train
from classify_trains import run_optimization
from slot_classifier import assign_slots
from flask import jsonify
import os
from prediction_pipeline import PredictionPipeline
import pandas as pd
from classify_trains import HISTORICAL_MAINTENANCE_DATA, HISTORICAL_CLEANING_DATA

app = Flask(
    __name__
)

dbmngr = DBMngr()

# Initialize prediction pipelines once (reuse across requests)
# Paths are relative to backend/ as the working directory for the app
MAINT_MODEL = os.path.join(os.path.dirname(__file__), 'bidirectional_gru_maintenance_model.h5')
MAINT_FEATURE_SCALER = os.path.join(os.path.dirname(__file__), 'feature_scaler.pkl')
MAINT_TARGET_SCALER = os.path.join(os.path.dirname(__file__), 'target_scaler.pkl')

CLEAN_MODEL = os.path.join(os.path.dirname(__file__), 'bidirectional_gru_cleaning_model.h5')
CLEAN_FEATURE_SCALER = os.path.join(os.path.dirname(__file__), 'cleaning_feature_scaler.pkl')
CLEAN_TARGET_SCALER = os.path.join(os.path.dirname(__file__), 'cleaning_target_scaler.pkl')

try:
    maintenance_pipeline = PredictionPipeline(MAINT_MODEL, MAINT_FEATURE_SCALER, MAINT_TARGET_SCALER)
except Exception:
    maintenance_pipeline = None

try:
    cleaning_pipeline = PredictionPipeline(CLEAN_MODEL, CLEAN_FEATURE_SCALER, CLEAN_TARGET_SCALER)
except Exception:
    cleaning_pipeline = None


def _prepare_historical_df(pipeline, csv_path: str, train_id: int):
    """Load historical CSV, filter by train_id and return a DataFrame with exactly
    pipeline.lookback rows (pad by repeating the earliest available row if needed).
    Returns None if pipeline is None or no historical rows exist for the train.
    """
    if pipeline is None:
        return None
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Could not read historical CSV {csv_path}: {e}")
        return None

    # filter rows for this train
    if 'train_id' not in df.columns:
        return None
    df_t = df[df['train_id'] == int(train_id)].copy()
    if df_t.empty:
        return None

    # determine time column to sort by
    time_cols = ['snapshot_timestamp', 'log_date', 'record_date', 'date']
    sort_col = None
    for c in time_cols:
        if c in df_t.columns:
            sort_col = c
            break
    if sort_col:
        try:
            df_t[sort_col] = pd.to_datetime(df_t[sort_col])
            df_t = df_t.sort_values(by=sort_col)
        except Exception:
            df_t = df_t.sort_index()
    else:
        df_t = df_t.sort_index()

    feature_names = list(getattr(pipeline, 'feature_names', []))
    # if pipeline feature names are unavailable, fall back to numeric columns except label
    if not feature_names:
        feature_names = [c for c in df_t.select_dtypes(include=['number']).columns if c not in ('record_id', 'train_id', 'actual_failure_risk_score', 'actual_dirtiness_score')]

    # keep only the features present in df
    feature_names = [c for c in feature_names if c in df_t.columns]
    if not feature_names:
        return None

    df_features = df_t[feature_names].copy()

    lookback = int(getattr(pipeline, 'lookback', 1))
    last_n = df_features.tail(lookback)
    if len(last_n) < lookback:
        # pad by repeating the first row of last_n (or the only row) at the top
        if len(last_n) == 0:
            return None
        rows_needed = lookback - len(last_n)
        pad = pd.DataFrame([last_n.iloc[0].to_dict()] * rows_needed)
        df_final = pd.concat([pad, last_n], ignore_index=True)
    else:
        df_final = last_n.reset_index(drop=True)

    # Ensure column order matches pipeline.feature_names if available
    if hasattr(pipeline, 'feature_names'):
        cols = [c for c in pipeline.feature_names if c in df_final.columns]
        df_final = df_final[cols]

    return df_final

@app.get("/api/get_trains")
@cross_origin()
def get_trains():
    trains = dbmngr.get_all_trains()
    if not trains:
        return []
    return trains

@app.route("/api/addtrain", methods=["POST"])
@cross_origin()
def add_train():
    train = request.json
    train = Train(**train)
    res =  dbmngr.add_train(train)
    if res:
        return "ok"
    else :
        return "error"
    
@app.get("/api/get_current_model_assignment")
@cross_origin()
def get_current_model_assignment():
    print("Sa")
    trains = dbmngr.get_all_trains()
    if not trains:
        return []
    for train in trains:
        train.pop('_id', None)
        if train.get('branding_expiry_date'):
            try:
                train['branding_expiry_date'] = datetime.strptime(train['branding_expiry_date'], "%Y-%m-%d").date()
            except Exception:
                train['branding_expiry_date'] = None
    trains = [ Train(**train) for train in trains]
    # --- Prediction step: compute AI scores for every train ---
    for t in trains:
        # Default to 0 if pipeline unavailable or prediction fails
        try:
            maint_df = _prepare_historical_df(maintenance_pipeline, os.path.join(os.path.dirname(__file__), HISTORICAL_MAINTENANCE_DATA), t.train_id)
            if maintenance_pipeline and maint_df is not None:
                t.predicted_failure_risk = float(maintenance_pipeline.predict(maint_df))
        except Exception as e:
            print(f"Maintenance prediction failed for train {t.train_id}: {e}")
        try:
            clean_df = _prepare_historical_df(cleaning_pipeline, os.path.join(os.path.dirname(__file__), HISTORICAL_CLEANING_DATA), t.train_id)
            if cleaning_pipeline and clean_df is not None:
                t.predicted_dirtiness_score = float(cleaning_pipeline.predict(clean_df))
        except Exception as e:
            print(f"Cleaning prediction failed for train {t.train_id}: {e}")

    run_optimization(trains)
    trains = [ train.toDict() for train in trains]
    
    return trains


@app.get("/api/get_stabling_geometry")
@cross_origin()
def get_stabling_geometry():
    """Return slot assignment mapping generated by slot_classifier.assign_slots.
    Output: JSON object mapping slot -> train_id (or null if unassigned).
    """
    trains = dbmngr.get_all_trains()
    if not trains:
        return jsonify({})

    # Normalize and convert to Train objects (defensive parsing)
    for train in trains:
        train.pop('_id', None)
        if train.get('branding_expiry_date'):
            try:
                train['branding_expiry_date'] = datetime.strptime(train['branding_expiry_date'], "%Y-%m-%d").date()
            except Exception:
                # leave as-is or set to None if parsing fails
                train['branding_expiry_date'] = None

    train_objs = [ Train(**train) for train in trains ]
    # --- Prediction step: compute AI scores for every train ---
    for t in train_objs:
        try:
            maint_df = _prepare_historical_df(maintenance_pipeline, os.path.join(os.path.dirname(__file__), HISTORICAL_MAINTENANCE_DATA), t.train_id)
            if maintenance_pipeline and maint_df is not None:
                t.predicted_failure_risk = float(maintenance_pipeline.predict(maint_df))
        except Exception as e:
            print(f"Maintenance prediction failed for train {t.train_id}: {e}")
        try:
            clean_df = _prepare_historical_df(cleaning_pipeline, os.path.join(os.path.dirname(__file__), HISTORICAL_CLEANING_DATA), t.train_id)
            if cleaning_pipeline and clean_df is not None:
                t.predicted_dirtiness_score = float(cleaning_pipeline.predict(clean_df))
        except Exception as e:
            print(f"Cleaning prediction failed for train {t.train_id}: {e}")

    # Run slot assignment MILP (slot_classifier.assign_slots)
    try:
        slot_map = assign_slots(train_objs)
    except Exception as e:
        # Return an error payload so frontend can show message
        return jsonify({"error": str(e)}), 500

    return jsonify(slot_map)

@app.route("/api/update_status", methods=['POST'])
@cross_origin()
def update_status():
    payload = request.json or {}
    train_code, status = payload.get('train_id'), payload.get('status')
    res = dbmngr.update_status(train_code, status)
    if res:
        return "ok"
    else:
        return "err"
@app.route("/api/resetstatus")
@cross_origin()
def reset_status():
    res =  dbmngr.unassign_all_trains()
    if res:
        return "ok"
    else:
        return "err"



if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 4001)),
        debug=False
    )
