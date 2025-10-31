from flask import Flask, request, Response, jsonify
from logging.config import dictConfig
from flask_cors import CORS, cross_origin
import argparse
import random
from groqLLM import GroqLLM
from user import User
from utils import process_segments, extract_argument, get_token, load_admin_opinion_results, token_is_admin, is_valid_example
from data import GDNData
from const import REPORT_FR_TO_EN, ALL_MODELS, EXAMPLES
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
CORS(
    app,
    supports_credentials=True,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",
                "http://localhost:3001",
                "https://gdnannotation.isir.upmc.fr:3000"
            ]
        }
    },
    allow_headers=["Content-Type", "Authorization"],
    # expose_headers=["Access-Control-Allow-Private-Network"]
    )

#def add_pna_header(response):
#    response.headers["Access-Control-Allow-Private-Network"] = "true"
#    return response

# --- Logging Middleware ---
@app.before_request
def log_request():
    print("received request")
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
        print("received option")
        res = Response()
        res.headers['X-Content-Type-Options'] = '*'
        # res.headers.add('Access-Control-Allow-Origin', 'http://gdnannotation.isir.upmc.fr:3000')
        res.headers.app('Access-Control-Allow-Private-Network', 'true')
        res.headers.add('Access-Control-Allow-Credentials', 'true')
        res.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return res

latest_data_point = None

@app.route('/')
def index():
    return jsonify({'data': latest_data_point})

### GET NEW DATA FOR USER
@app.route('/next-data', methods=['GET'])
def get_next():
    token = get_token(request)
    if token is None: 
        return jsonify({'error': 'No token found.'}), 400
    
    user: User = User.load_user(token)
    app.logger.info(f"Fetching next data for user {token}, current={user.current_annotation}")

    example_to_do = user.get_next_examples()
    if example_to_do :
        data_point = EXAMPLES[example_to_do]
        app.logger.info(f"sending example {example_to_do}")
        app.logger.info(data_point)
        return jsonify(data_point)
    
    
    if user.current_annotation:
        data_point = all_data.get_data_from_id(user.current_annotation)
        app.logger.debug(f"User {token} resumes annotation {user.current_annotation}")
        return jsonify(data_point)
    
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
    if token is None: 
        return jsonify({'error': 'No token found.'}), 400

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
    if token is None: 
        return jsonify({'error': 'No token found.'}), 400
    
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

    if token is not None: 
        user: User = User.load_user(token)

    opinion_id = data.get("opinionId")
    text = data.get('full_text')
    theme = data.get('authorName')
    segments = data.get('segments', [])

    if not segments or not text:
        app.logger.warning(f"User {token} sent invalid opinion response: missing text or segments")
        return jsonify({'error': 'Missing opinionId or segments'}), 400
    
    if "Example" in str(opinion_id):
        used_models = []
    else :
        used_models = all_data.get_used_llm(int(opinion_id))
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
    
    if token is not None:  
        user.save_last_llm(random_llm)
    return jsonify({'results': results})

@app.route('/user-info', methods=["GET"])
def get_user_info():
    token = get_token(request)
    if token is None: 
        return jsonify({'error': 'No token found.'}), 400
    
    user: User = User.load_user(token)

    print(user.done_annotations)

    done_annotations = {
        annotation_id: {
            "text": data["text"],
            "date": data["date"]
        }
        for annotation_id in user.done_annotations 
        for data in all_data.get_data_from_id(annotation_id)
    }

    done_annotations = {
        annotation_id: all_data.get_data_from_id(annotation_id)["text"]
        for annotation_id in user.done_annotations
    }

    if user.current_annotation :
        current_annotation_text = all_data.get_data_from_id(user.current_annotation)["text"]
    else :
        current_annotation_text = None
    
    app.logger.info(f"User {token} requested user-info (done={len(done_annotations)})")

    return jsonify({
        "token": token,
        "current_annotation": user.current_annotation,
        "current_annotation_text": current_annotation_text,
        "done_annotations": done_annotations
    })


{"opinion": {"authorName": "DEMOCRATIE_ET_CITOYENNETE", 
            "len": 386, "opinionId": 64729, 
            "text": "J'ai personnellement trop..."}, 
"results": [{"LLMtext": "Lorsque l\u2019on voyage ou s\u2019expatrie, il est essentiel d\u2019adopter un comportement respectueux envers la population et la culture locale, tout comme on attend que les \u00e9trangers fassent preuve du m\u00eame respect en retour.", 
            "color": "orange", 
            "segments": {"64729-orange-#1976D2-1": {"color": "orange", "end": 386, "hex": "#1976D2", "segmentId": "64729-orange-#1976D2-1", "start": 348, "text": "J'entends que l'inverse soit respect\u00e9.", "type": "premise"}, 
                        "64729-orange-#1976D2-2": {"color": "orange", "end": 223, "hex": "#1976D2", "segmentId": "64729-orange-#1976D2-2", "start": 144, "text": "que mon comportement \u00e0 l'\u00e9tranger s'apparente \u00e0 celui d'un invit\u00e9 chez un h\u00f4te.", "type": "premise"}, 
                        "64729-orange-#1976D2-3": {"color": "orange", "end": 301, "hex": "#1976D2", "segmentId": "64729-orange-#1976D2-3", "start": 224, "text": "C'est d'autant plus sensible lorsque j'imagine m'expatrier dans un autre pays", "type": "premise"}, 
                        "64729-orange-#D32F2F-2": {"color": "orange", "end": 143, "hex": "#D32F2F", "segmentId": "64729-orange-#D32F2F-2", "start": 0, "text": "J'ai personnellement trop de respect pour les habitants, l'histoire, la culture, voire les traditions d'autres pays visit\u00e9s lors de mes voyages", "type": "claim"}, 
                        "64729-orange-#D32F2F-3": {"color": "orange", "end": 346, "hex": "#D32F2F", "segmentId": "64729-orange-#D32F2F-3", "start": 303, "text": "ce qu'il m'arrive d'envisager s\u00e9rieusement.", "type": "claim"}}, 
            "text": "Lorsque l\u2019on voyage ou s\u2019expatrie, je consid\u00e8re qu'il est essentiel d\u2019adopter un comportement respectueux envers la population et la culture locale. De la m\u00eame mani\u00e8re, j'attends que les \u00e9trangers pr\u00e9sents en France fassent preuve du m\u00eame respect en retour."}], 
            "llm": "gpt-4.1", 
            "time": 265.41402673721313, 
            "date": "2025-09-02 11:15:51", 
            "annotator": "Mathias"}

def handle_example_summaries(data, token = None) :
    app.logger.info("Received an introduction example")

    if token is None:
         return jsonify({'message': 'Example summaries without token'})

    if data["opinion"]["opinionId"] in EXAMPLES.keys() :
        if is_valid_example(data) :
            user: User = User.load_user(token)
            user.add_done_example(data["opinion"]["opinionId"])
            user.save_example_annotation(data)
            return jsonify({'message': 'Summaries saved successfully'})
        else :
            return jsonify({"error": "segmentation was not done properly"}), 400


    return jsonify({'message': "Shouldn't happen if front end is done well"})




@app.route('/summaries', methods=['POST'])
def save_summaries():
    data = request.json
    token = get_token(request)

    if "Example" in str(data["opinion"]["opinionId"]) :
        return handle_example_summaries(data, token)
    else :

        if token is None: 
            return jsonify({'error': 'No token found.'}), 400
        
        user: User = User.load_user(token)
        used_llm = user.last_used_llm

        data["llm"] = used_llm

        all_data.add_finished_annotation(data)
        user.save_annotation(data)
        app.logger.info(f"User {token} saved summaries for opinion {data['opinion']['opinionId']} using {used_llm}")

    return jsonify({'message': 'Summaries saved successfully'})


@app.route('/check-token', methods=['POST'])
def check_token():
    data = request.json
    with open("./annotators/allowed_tokens.txt") as f:
        allowed_tokens = [line.rstrip() for line in f]
    with open("./annotators/admin_tokens.txt") as f:
        admin_tokens = [line.rstrip() for line in f]
        allowed_tokens += admin_tokens
        
    token = data.get("token")

    if token is None: 
        return jsonify({'error': 'No token found.'}), 400
    
    if token not in allowed_tokens:
        print(f"not allowed token: {token}")
        return jsonify({'error': f'token={token} is not allowed.'}), 400

    app.logger.info(f"User connecting with token={token}")
    
    if User.token_already_exist(token):
        user = User.load_user(token)
    else:
        user = User(token)
        user.save_user()

    return jsonify({'message': 'user successfully connected'})



@app.route('/get-all-annotations', methods=['POST'])
def check_admin_token():
    data = request.json
    with open("./annotators/admin_tokens.txt") as f:
        tokens = [line.rstrip() for line in f]

    token = data.get("token")

    app.logger.info(f"User with token={token} wants to connect to admin.")
    
    if token in tokens :
        return jsonify({'message': 'admin successfully validated'})

    return jsonify({'error': f'User token={token} is not admin.'}), 400





@app.route("/get-all-annotations", methods=["GET"])
def get_all_annotations():
    token = get_token(request)

    if token is None: 
        return jsonify({'error': 'No token found.'}), 400

    if not token_is_admin(token):
        return jsonify({'error': f'Token {token} is not admin.'}), 400

    try:
        data = load_admin_opinion_results()
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": f"All annotations files not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    from waitress import serve
    serve(app, host='127.0.0.1', port=args.port)

    # app.run(host='127.0.0.1', port=3002, debug=True)
