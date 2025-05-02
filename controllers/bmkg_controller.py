from flask import Blueprint, jsonify, current_app
import requests

# Daftar kode wilayah adm4 BMKG untuk dua daerah yang diinginkan\
REGION_CODES = {
    'bojongsoang': '32.04.08.2002',  # Kode wilayah Bojongsoang
    'dayeuhkolot': '32.04.08.2003'    # Ganti dengan kode wilayah Dayeuhkolot yang benar
    }

bmkg_bp = Blueprint('bmkg', __name__)

@bmkg_bp.route('/bmkg-rainfall', methods=['GET'])
def get_rainfall_forecast():
    """
    Ambil prakiraan curah hujan untuk Bojongsoang dan Dayeuhkolot
    ---
    tags:
      - BMKG
    produces:
      - application/json
    responses:
      200:
        description: Curah hujan berhasil diambil untuk kedua wilayah
        schema:
          type: object
          properties:
            bojongsoang:
              type: array
              items:
                type: object
                properties:
                  datetime:
                    type: string
                    format: date-time
                  tp:
                    type: number
                    description: Curah hujan dalam mm
            dayeuhkolot:
              type: array
              items:
                type: object
                properties:
                  datetime:
                    type: string
                    format: date-time
                  tp:
                    type: number
                    description: Curah hujan dalam mm
      502:
        description: Gagal mengambil data BMKG
        schema:
          type: object
          properties:
            error:
              type: string
              example: Gagal mengambil data BMKG
    """
    url = 'https://api.bmkg.go.id/publik/prakiraan-cuaca'
    result = {}

    for name, code in REGION_CODES.items():
        try:
            r = requests.get(url, params={'adm4': code}, timeout=10)
            r.raise_for_status()
            payload = r.json()
            # Flatten array of arrays cuaca -> ambil semua item dalam satu list
            forecast = []
            for period in payload.get('data', []):
                for chunk in period.get('cuaca', []):
                    for entry in chunk:
                        forecast.append({
                            'datetime': entry.get('datetime'),
                            'tp': entry.get('tp')
                        })
            result[name] = forecast
        except requests.RequestException as e:
            current_app.logger.error(f"Error fetching rainfall for {name}: {e}")
            return jsonify({'error': 'Gagal mengambil data BMKG'}), 502

    return jsonify(result), 200
