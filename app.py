from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from flasgger import Swagger
from controllers.predict import predict_bp,schedule_predict
# from controllers.bmkg_controller import bmkg_bp
from controllers.weather_controller import weather_bp, schedule_job
from flask_cors import CORS

app = Flask(__name__)

CORS(app)
Swagger(app)

app.register_blueprint(predict_bp, url_prefix='/api')
# app.register_blueprint(bmkg_bp,    url_prefix='/api')
app.register_blueprint(weather_bp,  url_prefix='/api')


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    schedule_predict(scheduler)   # job dari controllers/predict.py
    schedule_job(scheduler)   # job dari controllers/weather_controller.py
    scheduler.start()
    app.run(host="0.0.0.0", port=5000, debug=True)
