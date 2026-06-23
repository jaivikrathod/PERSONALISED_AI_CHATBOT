import json
import pickle
from sentence_transformers import SentenceTransformer

print("Loading FAQ data...")

with open("faq.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

print("Loading embedding model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

faq_questions = [
    faq["question"]
    for faq in faq_data
]

print("Creating embeddings...")

faq_embeddings = model.encode(
    faq_questions,
    convert_to_tensor=True
)

with open("faq_embeddings.pkl", "wb") as f:
    pickle.dump(faq_embeddings, f)

print("Embeddings saved successfully!")
print(f"Total FAQs: {len(faq_data)}")