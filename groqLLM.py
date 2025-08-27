import requests
from typing import Optional
import os

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
INSTRUCTION = "Tu es un portail de clarification d'argument. L'utilisateur va te donner une opinion écrite sur un thème donné, \
ainsi que la segmentation d'un des arguments de cette opinion en trois types de segments: affirmation(s), argument(s) et solution(s).\n \
Extrait, en une phrase, l'argument clair et auto-suffisant sous-jacent à cette segmentation. priorise la solution, et inclus les arguments \
et affirmations seulement si ils te semblent pertinents. Tu peux utiliser le contexte de l'opinion entière pour t'aider, mais n'inclus \
aucune information qui n'est pas présente dans les segments. Ne répond qu'avec l'argument clair et auto-suffisant, et rien d'autre. \
Si l'argument est déjà clair et bien écrit, tu peux renvoyer directement cet argument."

class GroqLLM:
    def __init__(self, model: str = "mixtral-8x7b-32768"):
        self.model = model

        if "gpt" in model:
            self.api_key = OPENAI_API_KEY
            self.api_url = "https://api.openai.com/v1/chat/completions"
        else:
            self.api_key = GROQ_API_KEY
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"

        self.instruction = INSTRUCTION
        

    
    def query(self, prompt: str, temperature: float = 0.3, max_tokens: int = 150) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if (("qwen" in self.model)) :
            data["reasoning_format"] = "hidden"
            data["reasoning_effort"] = "none"

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            print("got results by", self.model)
            print(result["choices"][0]["message"])
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as http_err:
            try:
                error_detail = response.json()
                print(f"Groq API error: {error_detail}")
            except Exception:
                print(f"HTTP error: {http_err}")
            return None
        except Exception as e:
            print(f"Error querying Groq LLM: {e}")
            return None 
    
