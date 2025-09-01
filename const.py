from pathlib import Path

DATA_FILE = Path("/home/lequeu/data/granddebat_filtered.jsonl")

ANNOTATORS_DIR = Path("./annotators/")
ALL_ANNOTATIONS_OUTPUT_FILE = Path("./annotators/all_annotations.jsonl")
ALL_REPORTS_OUTPUT_FILE = Path("./annotators/all_reports.jsonl")

NUM_ANNOTATIONS_BEFORE_SHARED = 8

REPORT_FR_TO_EN = {
    "discours de haine": "hate speech",
    "incomprehensible": "incomprehensible",
    "trop d'unités argumentatives": "too long",
    "autre": "other"
}
ALL_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    # "deepseek-r1-distill-llama-70b",
    "qwen/qwen3-32b",
    "gpt-4.1"

]
