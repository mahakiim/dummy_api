from flask import Flask
from flasgger import Swagger
from controllers.predict import predict_bp
from controllers.bmkg_controller import bmkg_bp

app = Flask(__name__)


app.register_blueprint(predict_bp, url_prefix='/api')
app.register_blueprint(bmkg_bp,    url_prefix='/api')

Swagger(app) 

if __name__ == '__main__':
    app.run()
