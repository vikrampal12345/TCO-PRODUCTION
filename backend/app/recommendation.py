from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import faiss
from collections import defaultdict
import os
import re
from app.job_formatter import format_job_name



BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "models", "minilm_model")

INDEX_PATH = os.path.join(BASE_DIR, "models", "resume_index.faiss")

DATA_PATH = os.path.join(BASE_DIR, "models", "resume_database.csv")


print("Loading MiniLM Model...")

# model = SentenceTransformer(MODEL_PATH)
model = None

print("MiniLM Loaded Successfully.")


print("Loading FAISS Index...")

# index = faiss.read_index(INDEX_PATH)
index = None

print("FAISS Loaded Successfully.")

print("Loading Resume Database...")

# resume_df = pd.read_csv(DATA_PATH)
resume_df = None

print("Database Loaded Successfully.")

job_columns = [

    "job_role_1",

    "job_role_2",

    "job_role_3",

    "job_role_4",

    "job_role_5"

]

print()

# print("Total Resume :", len(resume_df))

# print("Total Index :", index.ntotal)

def recommend_jobs(resume_text, top_k=5):
    
    global model, index, resume_df

    if model is None:

        print("Loading MiniLM Model...")

        model = SentenceTransformer(MODEL_PATH)

        print("MiniLM Loaded Successfully.")

    if index is None:

        print("Loading FAISS Index...")

        index = faiss.read_index(INDEX_PATH)

        print("FAISS Loaded Successfully.")

    if resume_df is None:

        print("Loading Resume Database...")

        resume_df = pd.read_csv(DATA_PATH)

        print("Database Loaded Successfully.")

    """
    Recommend Top K Job Roles from Resume Text
    """

    query_embedding = model.encode(
        [resume_text],
        convert_to_numpy=True).astype("float32")

    distance, indices = index.search(
        query_embedding,
        k=20)    

    job_scores = defaultdict(float)    

    job_columns = [
        "job_role_1",
        "job_role_2",
        "job_role_3",
        "job_role_4",
        "job_role_5"]

    for rank, idx in enumerate(indices[0]):

        similarity = 1 / (1 + distance[0][rank])

        for column in job_columns:

            job = resume_df.iloc[idx][column]

            if pd.notna(job):
                job_scores[job] += similarity    

    recommendations = sorted(
        job_scores.items(),
        key=lambda x: x[1],
        reverse=True)[:top_k]         


   
    if not recommendations:
        return []
    max_score = recommendations[0][1]

    result = []

    for rank, (job, score) in enumerate(recommendations, start=1):

        confidence = float(score / max_score) * 100

        result.append({
            "rank":rank,

            "job_role": format_job_name(job),

            "confidence": round(confidence, 2),

            "score": round(float(score), 3)

        })

    return result
if __name__ == "__main__":

    sample_resume = """
    Python
    Machine Learning
    TensorFlow
    SQL
    FastAPI
    Docker
    """

    jobs = recommend_jobs(sample_resume)

    print("\nRecommended Jobs:\n")

    for job in jobs:
        print(job)
