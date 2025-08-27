from flask import Flask, request, Response, jsonify
from logging.config import dictConfig
from flask_cors import CORS, cross_origin
import argparse
import random
from groqLLM import GroqLLM
from user import User
from utils import process_segments, extract_argument, get_token
from data import GDNData
from const import REPORT_FR_TO_EN, ALL_MODELS
import os

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=3002)
args = parser.parse_args()

all_llms = {model: GroqLLM(model) for model in ALL_MODELS}

print("loading data...")
all_data = GDNData()

os.makedirs("logs/", exist_ok=True)
dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        },
        "detailed": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d]: %(message)s",
        },
    },
    "handlers": {
        "console": {  # Keep console logging
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
        "info_file_handler": {
            "class": "logging.FileHandler",
            "formatter": "detailed",
            "filename": "./logs/info.log",
            "mode": "a",
            "level": "INFO",
        },
        "error_file_handler": {
            "class": "logging.FileHandler",
            "formatter": "detailed",
            "filename": "./logs/error.log",
            "mode": "a",
            "level": "ERROR",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "info_file_handler", "error_file_handler"],
    },
})


app = Flask(__name__)
CORS(app,
     supports_credentials=True,
     resources={r"/*": {"origins": "http://localhost:3001"}},
     allow_headers=["Content-Type", "Authorization"])

# --- Logging Middleware ---
@app.before_request
def log_request():
    token = None
    try:
        token = get_token(request)
    except Exception:
        pass  # some requests may not carry a token
    app.logger.info(
        f"➡️ Request {request.method} {request.path} "
        f"Token={token} "
        f"Size={request.content_length}B"
    )

@app.after_request
def log_response(response):
    app.logger.info(
        f"⬅️ Response {request.method} {request.path} "
        f"Status={response.status_code}"
    )
    return response

@app.errorhandler(Exception)
def log_exception(e):
    app.logger.exception(f"💥 Unhandled exception at {request.path}: {e}")
    return jsonify({"error": "Internal server error"}), 500

# --- End Middleware ---

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = Response()
        res.headers['X-Content-Type-Options'] = '*'
        res.headers.add('Access-Control-Allow-Origin', 'http://localhost:3001')
        res.headers.add('Access-Control-Allow-Credentials', 'true')
        res.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return res

latest_data_point = None

@app.route('/')
def index():
    return jsonify({'data': latest_data_point})

### GET NEW DATA FOR USER
@app.route('/next-data', methods=['GET'])
@cross_origin(origins="http://localhost:3001", allow_headers=["Content-Type", "Authorization"])
def get_next():
    token = get_token(request)
    user: User = User.load_user(token)
    app.logger.info(f"Fetching next data for user {token}, current={user.current_annotation}")

    if user.current_annotation:
        data_point = all_data.get_data_from_id(user.current_annotation)
        app.logger.debug(f"User {token} resumes annotation {user.current_annotation}")
    else:
        try:
            data_point = all_data.next_data(user)
            app.logger.info(f"User {token} assigned new annotation {data_point['opinionId']}")
            user.new_opinion(data_point)
        except OverflowError:
            app.logger.warning(f"User {token} has no more opinions to annotate")
            return jsonify({'error': 'No more opinion to annotate.'}), 400

    return jsonify(data_point)

@app.route('/data-from-id', methods=['POST'])
def get_data_from_id():
    token = get_token(request)
    user: User = User.load_user(token)
    data = request.json

    new_opinion_id = int(data.get("opinionId"))
    app.logger.info(f"User {token} switching to opinion {new_opinion_id}")

    new_opinion = all_data.get_data_from_id(new_opinion_id)
    all_data.set_opinion_annotation(new_opinion_id)

    current_opinion_id = user.current_annotation
    all_data.cancel_opinion_annotation(current_opinion_id)

    user.new_opinion(new_opinion)
    return jsonify(new_opinion)

@app.route('/report', methods=['POST'])
def report():
    data = request.json
    token = get_token(request)
    user: User = User.load_user(token)

    opinion = data.get("opinion")
    reason = data.get("reason")
    reason = REPORT_FR_TO_EN.get(reason)

    app.logger.info(f"User {token} reporting opinion {opinion.get('opinionId')} for reason={reason}")

    output = {
        "opinion": opinion,
        "reason": reason
    }

    all_data.add_reported_annotation(output)
    user.report_data(output)

    return jsonify({'message': 'opinion reported successfully'})

@app.route('/opinion-response', methods=['POST'])
def process_opinion():
    data = request.json
    latest_data_point = data
    token = get_token(request)
    user: User = User.load_user(token)

    opinion_id = int(data.get("opinionId"))
    text = data.get('full_text')
    theme = data.get('authorName')
    segments = data.get('segments', [])

    if not segments or not text:
        app.logger.warning(f"User {token} sent invalid opinion response: missing text or segments")
        return jsonify({'error': 'Missing opinionId or segments'}), 400

    used_models = all_data.get_used_llm(opinion_id)
    random_llm = random.choice([model for model in ALL_MODELS if model not in used_models])
    app.logger.info(f"User {token} processing opinion {opinion_id} with model={random_llm}")

    color_grouped_segments = process_segments(segments)
    results = []
    for color, segs in color_grouped_segments.items():
        app.logger.debug(f"Processing color {color} with {len(segs)} segments")
        argument = extract_argument(text, segs, theme, all_llms[random_llm])
        results.append({
            'segments': segs,
            'color': color,
            'LLMtext': argument,
            'text': argument
        })

    user.save_last_llm(random_llm)
    return jsonify({'results': results})

@app.route('/user-info', methods=["GET"])
def get_user_info():
    token = get_token(request)
    user: User = User.load_user(token)
    done_annotations = {
        annotation_id: all_data.get_data_from_id(annotation_id)["text"]
        for annotation_id in user.done_annotations
    }
    current_annotation_text = all_data.get_data_from_id(user.current_annotation)["text"]

    app.logger.info(f"User {token} requested user-info (done={len(done_annotations)})")

    return jsonify({
        "token": token,
        "current_annotation": user.current_annotation,
        "current_annotation_text": current_annotation_text,
        "done_annotations": done_annotations
    })

@app.route('/summaries', methods=['POST'])
def save_summaries():
    data = request.json
    token = get_token(request)
    user: User = User.load_user(token)
    used_llm = user.last_used_llm

    data["llm"] = used_llm

    if data["opinion"]["opinionId"] == "introductionExample":
        app.logger.info("Skipping introductionExample summary save")
        return jsonify({'message': 'Summaries saved successfully'})

    all_data.add_finished_annotation(data)
    user.save_annotation(data)
    app.logger.info(f"User {token} saved summaries for opinion {data['opinion']['opinionId']} using {used_llm}")

    return jsonify({'message': 'Summaries saved successfully'})

@app.route('/check-token', methods=['POST'])
def check_token():
    data = request.json
    with open("./annotators/all_tokens.txt") as f:
        tokens = [line.rstrip() for line in f]
    token = data.get("token")

    app.logger.info(f"User connecting with token={token}")

    if User.token_already_exist(token):
        user = User.load_user(token)
    else:
        user = User(token)
        user.save_user()

    return jsonify({'message': 'user successfully connected'})

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=args.port)

    # app.run(host='0.0.0.0', port=3002, debug=True)
