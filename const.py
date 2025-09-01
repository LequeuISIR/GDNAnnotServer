from pathlib import Path

DATA_FILE = Path("/data/lequeu/granddebat/granddebat_filtered.jsonl")

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
    "llama3-70b-8192",
    "llama3-8b-8192",
    # "deepseek-r1-distill-llama-70b",
    "qwen/qwen3-32b",
    "gpt-4.1"

]
