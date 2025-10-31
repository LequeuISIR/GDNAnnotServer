from pathlib import Path
import os

DATA_FILE = Path(os.environ["ANNOTATION_DATA_FILE"])


ANNOTATORS_DIR = Path("./annotators/")
ALL_ANNOTATIONS_OUTPUT_FILE = Path("./annotators/all_annotations.jsonl")
ALL_REPORTS_OUTPUT_FILE = Path("./annotators/all_reports.jsonl")

NUM_ANNOTATIONS_BEFORE_SHARED = 5

REPORT_FR_TO_EN = {
    "discours de haine": "hate speech",
    "incomprehensible": "incomprehensible",
    "trop d'unités argumentatives": "too long",
    "informations personnelles": "not anonymous",
    "autre": "other"
}

ALL_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    # "deepseek-r1-distill-llama-70b",
    "qwen/qwen3-32b",
    "gpt-4.1"
]


EXAMPLES = {
    "introductionExample1": {
        "opinionId": "introductionExample1",
        "text": "Globalement l'impôt, quel qu'il soit doit être plus équitable. Il faut limiter les possibilités \
        d'y échapper (évasion fiscale / niches fiscales / fraudes). L'impôt doit être simplifié, en limitant le nombre de \
        prélèvement ou de taxes pour faciliter la compréhension de tous. Les aides sociales doivent également être plus lisibles \
        : exemple, une aide familiale reprenant toutes celles existantes. Les dépenses doivent également être réalisées avec plus \
        d'équité (ne pas faire profiter qu'un petite partie de la population).",
        "authorName": "LA_FISCALITE_ET_LES_DEPENSES_PUBLIQUES",
    },
    "introductionExample2": {
        "opinionId": "introductionExample2",
        "text": "Il y a urgence ! Nous sommes responsables de ce que nous allons laissé aux générations futures.",
        "authorName": "LA_TRANSITION_ECOLOGIQUE",
    },
    "introductionExample3": {
        "opinionId": "introductionExample3",
        "text": "-Faire baisser le prix des maisons de retraite -autoriser l'aide à l'euthanasie active pour celui qui le \
        décide pour lui même, dans certains cas -retour de la peine de mort pour les meurtres d'enfants et de mineurs - perte \
        de nationalité pour les bi nationaux récidiviste et les condamnés pour terrorisme -non retour en France des combattants de Daech",
        "authorName": "DEMOCRATIE_ET_CITOYENNETE",
    }
}


RESULTS_EXAMPLES = {
    "introductionExample1" : {
        "num_argumentative_units": 4,
        "num_premises": 4,
        "num_claims": 1,
        "num_solutions": 3 
    },
    "introductionExample2" : {
        "num_argumentative_units": 1,
        "num_premises": 0,
        "num_claims": 1,
        "num_solutions": 0 
    },
    "introductionExample3" : {
        "num_argumentative_units": 5,
        "num_premises": 0,
        "num_claims": 0,
        "num_solutions": 5 
    }
}