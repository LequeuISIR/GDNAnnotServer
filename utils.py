import json
import datetime
from collections import defaultdict
from const import ALL_ANNOTATIONS_OUTPUT_FILE, RESULTS_EXAMPLES

def get_new_batch() :
    NotImplemented
    

def extract_argument(opinion_text, segments, theme, llm):
    """Use the LLM to extract the argument from the text."""

    texts = {"claim": "",
            "premise": "",
            "solution": ""
            }

    for id, segment in segments.items() :
        segtype = segment["type"]
        if texts[segtype] :
            texts[segtype] += " [...] " 
        texts[segtype] += segment["text"]

        

    prompt = f"""Etant donnée l-opinion:\n
    {opinion_text}
    \n\n
    sur le thème {theme}
    \n\n
    Extrait, en une phrase, l'argument soujacent composé de:\n"""

    if texts["claim"] :
        claim = texts["claim"]
        prompt += f"- affirmation(s): {claim}\n"
    if texts["premise"] :
        premise = texts["premise"]
        prompt += f"- argument(s): {premise}\n"
    if texts["solution"] :
        solution = texts["solution"]
        prompt += f"- solution(s): {solution}\n"
    
    
    argument = llm.query(prompt)

    return argument

def process_segments(segments) :
    # group the segments per color (instead of hex)
    segments_per_colors = defaultdict(dict)
    for segmentId, segment in segments.items() :
        segments_per_colors[segment["color"]][segmentId] = segment

    return segments_per_colors

def get_token(request) :
    try : 
        token = request.headers.get("Authorization")
        token = token.split(" ")[-1]
        return token
    except :
        return None


def load_admin_opinion_results(path: str = ALL_ANNOTATIONS_OUTPUT_FILE):
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():  # avoid empty lines
                dict = json.loads(line)
                del dict
                results.append(json.loads(line))
    return results

def token_is_admin(token):
    with open("./annotators/admin_tokens.txt") as f:
        admin_tokens = [line.rstrip() for line in f]
    
    if token in admin_tokens :
        return True

    return False

def is_valid_example(example_output) :
    expected = RESULTS_EXAMPLES[example_output["opinion"]["opinionId"]]
    num_argumentative_units = len(example_output["results"])
    all_segments = [res["segments"] for res in example_output["results"]]
    num_premises= 0
    num_claims=0
    num_solutions=0
    for segments in all_segments :
        num_claims += len([seg for seg in segments.values() if seg["type"] == "claim"])
        num_premises += len([seg for seg in segments.values() if seg["type"] == "premise"])
        num_solutions += len([seg for seg in segments.values() if seg["type"] == "solution"])

    print(num_argumentative_units, num_claims, num_premises, num_solutions, expected)
    if ((expected["num_argumentative_units"] != num_argumentative_units) 
        or (expected["num_claims"] != num_claims) 
        or (expected["num_premises"] != num_premises) 
        or (expected["num_solutions"] != num_solutions)) :
        return False

    return True