# model/fb_client.py

import firebase_admin
from firebase_admin import credentials, db
from model.bmkg_api import fetch_all_locations

# Inisialisasi Firebase cuma sekali
if not firebase_admin._apps:
    cred = credentials.Certificate(
        "floody-252ef-firebase-adminsdk-fbsvc-2b5138719e.json"
    )
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://floody-252ef-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

def upload_to_firebase() -> None:
   
    ref = db.reference("/Polder")
    all_data = fetch_all_locations()

    for lokasi, data in all_data.items():
        loc_ref = ref.child(lokasi)
        # Kalau ada error, set object; kalau bukan, loop child per timestamp
        if "error" in data:
            loc_ref.set(data)
        else:
            for waktu_iso, tp in data.items():
                loc_ref.child(waktu_iso).set(tp)

    print("✅ Data cuaca berhasil diupload ke Firebase")


