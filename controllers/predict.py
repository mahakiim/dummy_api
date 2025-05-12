# controllers/predict_controller.py

from flask import Blueprint, jsonify, request
import os
import joblib
import numpy as np
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import logging

# Setup logger
t_logging = logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

predict_bp = Blueprint('predict', __name__)

# Inisialisasi Firebase Admin
base_dir = os.path.dirname(__file__)
service_account = os.path.join(
    base_dir, '..',
    'floody-252ef-firebase-adminsdk-fbsvc-8b8b58595a.json'
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

def latest_value(node_dict):
    if not isinstance(node_dict, dict) or not node_dict:
        return 0
    last_ts = sorted(node_dict.keys())[-1]
    return node_dict.get(last_ts, 0)


@predict_bp.route('/predict', methods=['GET', 'POST'])

def predict():
    logger.info('Endpoint /predict called')

    # 1) Dapatkan data sensor
    if request.method == 'POST':
        data = request.get_json() or {}
        logger.info(f'Using POST payload: {data}')
        rain_bs = data.get('bojongsoang', 0)
        rain_dk = data.get('dayeuhkolot', 0)
        debit_cip = data.get('Debit_Cipalasari', 0)
        debit_cit = data.get('Debit_Citarum', 0)
        debit_hil = data.get('Debit_Hilir', 0)
        tma_hil = data.get('TMA_hilir', 0)
        tma_kol = data.get('TMA_kolam', 0)
        tma_sun = data.get('TMA_sungai', 0)
    else:
        logger.info('Fetching latest sensor data from /Polder')
        root_ref = db.reference('/Polder')
        # Baca setiap node fitur dan ambil nilai terakhir
        rain_bs = latest_value(root_ref.child('bojongsoang').get())
        rain_dk = latest_value(root_ref.child('dayeuhkolot').get())
        debit_cip = latest_value(root_ref.child('Debit_Cipalasari').get())
        debit_cit = latest_value(root_ref.child('Debit_Citarum').get())
        debit_hil = latest_value(root_ref.child('Debit_Hilir').get())
        tma_hil = latest_value(root_ref.child('TMA_Hilir').get())
        tma_kol = latest_value(root_ref.child('TMA_Kolam').get())
        tma_sun = latest_value(root_ref.child('TMA_Sungai').get())
        logger.info(f'Latest sensor values: BS={rain_bs}, DK={rain_dk}, cip={debit_cip}, cit={debit_cit}, hil={debit_hil}, tma_hil={tma_hil}, tma_kol={tma_kol}, tma_sun={tma_sun}')

    # 2) Siapkan fitur array
    features = [rain_bs, rain_dk, debit_cip, debit_cit, debit_hil, tma_hil, tma_kol, tma_sun]
    arr = np.array(features, dtype=float).reshape(1, -1)
    logger.info(f'Feature array: {features}')

    # 3) Prediksi
    pump_pred, alert_pred = model.predict(arr)[0]
    logger.info(f'Predictions - pump_on: {pump_pred}, alert_level: {alert_pred}')

    # 4) Simpan hasil prediksi dengan key timestamp
    ts = datetime.utcnow().strftime('%Y-%m-%d-%H_%M_%S')
    polder_ref = db.reference('/Polder')
    polder_ref.child('pump_on').child(ts).set(int(pump_pred))
    polder_ref.child('status_banjir').child(ts).set(int(alert_pred))
    logger.info(f'Saved predictions at {ts}')

    # 5) Kembalikan hasil
    response = {'pump_on': int(pump_pred), 'alert_level': int(alert_pred)}
    return jsonify(response)
