import json
import datetime
from collections import defaultdict
from const import ALL_ANNOTATIONS_OUTPUT_FILE

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
                results.append(json.loads(line))
    return results

def token_is_admin(token):
    with open("./annotators/admin_tokens.txt") as f:
        admin_tokens = [line.rstrip() for line in f]
    
    if token in admin_tokens :
        return True

    return False
