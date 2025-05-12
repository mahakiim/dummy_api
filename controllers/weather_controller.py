# controllers/weather_controller.py

from flask import Blueprint, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from model.fb_client import upload_to_firebase
from model.bmkg_api import fetch_all_locations   # import func

weather_bp = Blueprint("weather", __name__)

@weather_bp.route("/trigger", methods=["POST"])
def manual_trigger():
    """
    Trigger manual upload data cuaca ke Firebase.
    ---
    tags:
      - Weather
    responses:
      200:
        description: upload sukses
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Data cuaca berhasil diupload ke Firebase
      500:
        description: upload gagal
    """
    try:
        upload_to_firebase()
        return jsonify({
            "status": "success",
            "message": "Data cuaca berhasil diupload ke Firebase"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Gagal upload: {e}"
        }), 500

@weather_bp.route("/curah-hujan", methods=["GET"])
def get_curah_hujan():
    """
    Ambil prakiraan curah hujan terbaru dari BMKG.
    ---
    tags:
      - Weather
    responses:
      200:
        description: data cuaca BMKG
        schema:
          type: object
          additionalProperties:   # lokasi dinamis (bojongsoang, dayeuhkolot)
            type: object
            additionalProperties:
              type: number
          example:
            bojongsoang:
              "2025-05-10T15:00:00+07:00": 4.5
            dayeuhkolot:
              "2025-05-10T15:00:00+07:00": 3.2
    """
    data = fetch_all_locations()
    return jsonify(data)

def schedule_job(scheduler: BackgroundScheduler):
    scheduler.add_job(
        func=upload_to_firebase,
        trigger="interval",
        minutes=5,
        id="weather_upload_job",
        replace_existing=True
    )
