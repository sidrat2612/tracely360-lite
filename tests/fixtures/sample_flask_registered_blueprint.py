from flask import Blueprint, Flask

app = Flask(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')
app.register_blueprint(api_bp, url_prefix='/v1')


@api_bp.get('/users')
def list_users():
    return []