# controllers/predict.py

import os
import joblib
import numpy as np
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, jsonify, request
import firebase_admin
from firebase_admin import credentials, db
from apscheduler.schedulers.background import BackgroundScheduler

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint
predict_bp = Blueprint('predict', __name__)

# === Inisialisasi Firebase Admin ===
base_dir = os.path.dirname(__file__)
service_account = os.path.join(
    base_dir, '..',
    'floody-252ef-firebase-adminsdk-fbsvc-19378a91dd.json'
)
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://floody-252ef-default-rtdb.asia-southeast1.firebasedatabase.app'
    })
    logger.info('🔥 Firebase Admin initialized')

# === Load model ===
model_path = os.path.join(base_dir, '..', 'model', 'gb_model2.pkl')
model = joblib.load(model_path)
logger.info(f'🧠 Model loaded from {model_path}')

def latest_value(node_dict):
    """Ambil nilai terakhir dari dict timestamp → value."""
    if not isinstance(node_dict, dict) or not node_dict:
        return 0
    last_ts = sorted(node_dict.keys())[-1]
    return node_dict.get(last_ts, 0)

def upload_to_firebase():
    """Ambil data terbaru, prediksi, dan upload ke RTDB."""
    logger.info('🔔 Running scheduled prediction/upload')

    root_ref = db.reference('/Polder')
    rain_bs = latest_value(root_ref.child('bojongsoang').get())
    rain_dk = latest_value(root_ref.child('dayeuhkolot').get())
    debit_cip = latest_value(root_ref.child('Debit_Cipalasari').get())
    debit_cit = latest_value(root_ref.child('Debit_Citarum').get())
    debit_hil = latest_value(root_ref.child('Debit_Hilir').get())
    tma_hil = latest_value(root_ref.child('TMA_Hilir').get())
    tma_kol = latest_value(root_ref.child('TMA_Kolam').get())
    tma_sun = latest_value(root_ref.child('TMA_Sungai').get())
    features = [rain_bs, rain_dk, debit_cip, debit_cit, debit_hil, tma_hil, tma_kol, tma_sun]
    logger.info(f'   Sensor values: {features}')

    arr = np.array(features, dtype=float).reshape(1, -1)
    pump_pred, alert_pred = model.predict(arr)[0]
    logger.info(f'   Prediction → pump_on={pump_pred}, alert_level={alert_pred}')

    ts = datetime.now(ZoneInfo("Asia/Jakarta")).strftime('%Y-%m-%d-%H_%M_%S')
    polder_ref = root_ref
    polder_ref.child('pump_on').child(ts).set(int(pump_pred))
    polder_ref.child('status_banjir').child(ts).set(int(alert_pred))
    logger.info(f'   Uploaded at {ts}')

@predict_bp.route('/predict', methods=['GET', 'POST'])
def predict_endpoint():
    """
    Trigger flood prediction and store to Firebase.
    ---
    tags:
      - Prediction
    parameters:
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            bojongsoang:
              type: number
              description: Curah hujan Bojongsoang (mm)
            dayeuhkolot:
              type: number
            Debit_Cipalasari:
              type: number
            Debit_Citarum:
              type: number
            Debit_Hilir:
              type: number
            TMA_hilir:
              type: number
            TMA_kolam:
              type: number
            TMA_sungai:
              type: number
    responses:
      200:
        description: Hasil prediksi
        schema:
          type: object
          properties:
            pump_on:
              type: integer
              description: 1=ON, 0=OFF
            alert_level:
              type: integer
              description: 0=normal, 1=waspada, 2=banyak
    """
    logger.info('🚀 Endpoint /predict called')
    if request.method == 'POST':
        data = request.get_json() or {}
        features = [
            data.get('bojongsoang', 0),
            data.get('dayeuhkolot', 0),
            data.get('Debit_Cipalasari', 0),
            data.get('Debit_Citarum', 0),
            data.get('Debit_Hilir', 0),
            data.get('TMA_hilir', 0),
            data.get('TMA_kolam', 0),
            data.get('TMA_sungai', 0),
        ]
        arr = np.array(features, dtype=float).reshape(1, -1)
        pump_pred, alert_pred = model.predict(arr)[0]

        ts = datetime.now(ZoneInfo("Asia/Jakarta")).strftime('%Y-%m-%d-%H_%M_%S')
        root_ref = db.reference('/Polder')
        root_ref.child('pump_on').child(ts).set(int(pump_pred))
        root_ref.child('status_banjir').child(ts).set(int(alert_pred))
        logger.info(f'   POST upload at {ts}')

        return jsonify({'pump_on': int(pump_pred), 'alert_level': int(alert_pred)})
    else:
        upload_to_firebase()
        return jsonify({'status': 'scheduled run executed'})

def schedule_predict(scheduler1: BackgroundScheduler):
    """
    Tambahkan job interval 5 menit untuk upload_to_firebase().
    Panggil ini dari app.py setelah scheduler dibuat.
    """
    scheduler1.add_job(
        func=upload_to_firebase,
        trigger="interval",
        minutes=5,
        id="predict_upload_job",
        replace_existing=True,
        misfire_grace_time=120
    )
    logger.info("🗓️ Scheduled job 'predict' every 5 minutes")
