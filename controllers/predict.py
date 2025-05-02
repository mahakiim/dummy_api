# controllers/predict_controller.py
from flask import Blueprint, request, jsonify
import os, joblib, numpy as np

predict_bp = Blueprint('predict', __name__)

# Load model sekali saat module di-import
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'gb_model.pkl')
model = joblib.load(MODEL_PATH)

@predict_bp.route('/predict', methods=['POST'])
def predict():
    """
    Predict jumlah pompa yang menyala (0–3)
    ---
    tags:
      - Prediction
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - curah_hujan_dk
            - curah_hujan_bs
            - debit_sungai
            - tma_sungai
            - tma_kolam
          properties:
            curah_hujan_dk:
              type: number
              description: Curah hujan di daerah 'dk' (mm)
            curah_hujan_bs:
              type: number
              description: Curah hujan di daerah 'bs' (mm)
            debit_sungai:
              type: number
              description: Debit aliran sungai (m³/s)
            tma_sungai:
              type: number
              description: Tinggi muka air sungai (m)
            tma_kolam:
              type: number
              description: Tinggi muka air kolam (m)
          example:
            curah_hujan_dk: 12.5
            curah_hujan_bs: 8.3
            debit_sungai: 25.4
            tma_sungai: 1.2
            tma_kolam: 0.8
    responses:
      200:
        description: Prediksi jumlah pompa yang akan menyala (integer 0–3)
        schema:
          type: object
          properties:
            prediction:
              type: integer
              description: 0 = no pump, 1 = 1 pump, 2 = 2 pumps, 3 = 3 pumps
          example:
            prediction: 2
    """
    data = request.get_json()
    # ambil masing-masing fitur sesuai key
    feats = [
        data['curah_hujan_dk'],
        data['curah_hujan_bs'],
        data['debit_sungai'],
        data['tma_sungai'],
        data['tma_kolam']
    ]
    # reshape -> model.predict
    arr = np.array(feats).reshape(1, -1)
    pred = model.predict(arr)[0]
    return jsonify({'prediction': int(pred)})
