from flask import Flask, Blueprint

app = Flask(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

@app.route('/health', methods=['GET'])
def health():
    return {"status": "ok"}

@app.get('/items/<id>')
def get_item(id):
    return {"id": id}

@app.post('/items')
def create_item():
    return {}, 201

@api_bp.route('/users', methods=['GET', 'POST'])
def users():
    pass
