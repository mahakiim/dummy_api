# controllers/predict_controller.py

from flask import Blueprint, jsonify, request
import os
import joblib
import numpy as np
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

predict_bp = Blueprint('predict', __name__)

# Inisialisasi Firebase Admin
base_dir = os.path.dirname(__file__)
service_account = os.path.join(
    base_dir, '..',
    'floody-252ef-firebase-adminsdk-fbsvc-2b5138719e.json'
)
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://floody-252ef-default-rtdb.asia-southeast1.firebasedatabase.app'
    })
    logger.info('Firebase Admin initialized')

# Load multi-output model
model_path = os.path.join(base_dir, '..', 'model', 'gb_model2.pkl')
model = joblib.load(model_path)
logger.info(f'Model loaded from {model_path}')

# Helper to get latest value
def latest_value(node_dict):
    if not isinstance(node_dict, dict) or not node_dict:
        return 0
    last_ts = sorted(node_dict.keys())[-1]
    return node_dict.get(last_ts, 0)

# Core predict logic (fetch, predict, save)
def run_prediction():
    logger.info('Running scheduled prediction...')
    root_ref = db.reference('/Polder')

    # Fetch latest sensor values
    rain_bs = latest_value(root_ref.child('bojongsoang').get())
    rain_dk = latest_value(root_ref.child('dayeuhkolot').get())
    debit_cip = latest_value(root_ref.child('debit_cipalasari').get())
    debit_cit = latest_value(root_ref.child('debit_citarum').get())
    debit_hil = latest_value(root_ref.child('debit_hilir').get())
    tma_hil = latest_value(root_ref.child('TMA_Hilir').get())
    tma_kol = latest_value(root_ref.child('TMA_Kolam').get())
    tma_sun = latest_value(root_ref.child('TMA_Sungai').get())
    logger.info(f'Sensor values: BS={rain_bs}, DK={rain_dk}, CIP={debit_cip}, CIT={debit_cit}, HIL={debit_hil}, TMA_H={tma_hil}, TMA_K={tma_kol}, TMA_S={tma_sun}')

    # Prepare features
    features = [rain_bs, rain_dk, debit_cip, debit_cit, debit_hil, tma_hil, tma_kol, tma_sun]
    arr = np.array(features, dtype=float).reshape(1, -1)

    # Predict
    pump_pred, alert_pred = model.predict(arr)[0]
    logger.info(f'Predictions: pump_on={pump_pred}, alert_level={alert_pred}')

    # Save predictions
    ts = datetime.utcnow().strftime('%Y-%m-%d-%H_%M_%S')
    pump_ref = root_ref.child('pump_on')
    status_ref = root_ref.child('status_banjir')
    pump_ref.child(ts).set(int(pump_pred))
    status_ref.child(ts).set(int(alert_pred))
    logger.info(f'Predictions saved at {ts}')

# Schedule job every 5 minutes
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_prediction, 'interval', minutes=5, next_run_time=datetime.utcnow())
    scheduler.start()
    logger.info('Scheduler started: prediction every 5 minutes')

# Start scheduler on import
start_scheduler()

@predict_bp.route('/predict', methods=['GET', 'POST'])
def predict():
    logger.info('Endpoint /predict called')
    # If POST, run on-demand with input override
    if request.method == 'POST':
        data = request.get_json() or {}
        logger.info(f'Using POST payload: {data}')
        rain_bs = data.get('bojongsoang', 0)
        rain_dk = data.get('dayeuhkolot', 0)
        debit_cip = data.get('debit_cipalasari', 0)
        debit_cit = data.get('debit_citarum', 0)
        debit_hil = data.get('debit_hilir', 0)
        tma_hil = data.get('tma_hilir', 0)
        tma_kol = data.get('tma_kolam', 0)
        tma_sun = data.get('tma_sungai', 0)
        features = [rain_bs, rain_dk, debit_cip, debit_cit, debit_hil, tma_hil, tma_kol, tma_sun]
        arr = np.array(features, dtype=float).reshape(1, -1)
        pump_pred, alert_pred = model.predict(arr)[0]
        response = {'pump_on': int(pump_pred), 'alert_level': int(alert_pred)}
        logger.info(f'Returning on-demand response: {response}')
        return jsonify(response)
    # For GET, return last prediction
    root_ref = db.reference('/Polder')
    last_pump = latest_value(root_ref.child('pump_on').get())
    last_alert = latest_value(root_ref.child('status_banjir').get())
    response = {'pump_on': int(last_pump), 'alert_level': int(last_alert)}
    logger.info(f'Returning last saved prediction: {response}')
    return jsonify(response)
