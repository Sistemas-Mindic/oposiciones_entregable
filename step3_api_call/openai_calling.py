import os
from dotenv import load_dotenv
from openai import OpenAI

#print("Working dir:", os.getcwd())
load_dotenv("API_OPENAI.env")  # Carga el .env de esa ruta

#print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))

# Leer la clave desde la variable OPENAI_KEY
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

response = client.responses.create(
    model="gpt-5.1",
    input="Write a short bedtime story about a unicorn."
)

print(response.output_text)

