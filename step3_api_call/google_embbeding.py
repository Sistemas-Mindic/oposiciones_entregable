from dotenv import load_dotenv
import os
import google.generativeai as genai

import pandas as pd
df = pd.read_csv("resultados_enlaces.csv", sep=",", header=0,
                 names=["Enlace", "Contenido", "Convocatoria"])

print(df.head(10))
##PENDIENTE FILTRAR TRUE ----> CREAR EMBBEDING GUARDAR DATASET, Y CORRELACION DE 5 MEJORES (MODELO DE PRUEBA) 
# load_dotenv(dotenv_path="API_GOOGLE.env")
# api_key_google = os.getenv("GOOGLE_API_KEY")
# genai.configure(api_key=api_key_google)

# result = genai.embed_content(
#     model="gemini-embedding-001",
#     content=
# )
# print(result["embedding"])
