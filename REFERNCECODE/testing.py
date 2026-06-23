import json
import pickle
from sentence_transformers import SentenceTransformer, util

# ==========================
# LOAD FAQ DATA
# ==========================

with open("faq.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

# ==========================
# LOAD SAVED EMBEDDINGS
# ==========================

with open("faq_embeddings.pkl", "rb") as f:
    faq_embeddings = pickle.load(f)

# ==========================
# LOAD MODEL
# ==========================

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Chatbot Ready!")
print("Type 'exit' to quit.\n")

# ==========================
# CHAT LOOP
# ==========================

while True:

    user_question = input("You: ")

    if user_question.lower() == "exit":
        print("Goodbye!")
        break

    user_embedding = model.encode(
        user_question,
        convert_to_tensor=True
    )

    scores = util.cos_sim(
        user_embedding,
        faq_embeddings
    )[0]

    top_results = scores.argsort(
        descending=True
    )

    best_idx = top_results[0]
    best_score = scores[best_idx]

    CONFIDENCE_THRESHOLD = 0.50

    print("\nTop Matches:")

    for idx in top_results[:3]:
        print(
            f"- {faq_data[idx]['question']} "
            f"({scores[idx]:.4f})"
        )

    print()

    if best_score < CONFIDENCE_THRESHOLD:
        print(
            "Bot: Sorry, I couldn't find a reliable answer.\n"
        )
    else:
        print(
            f"Bot: {faq_data[best_idx]['answer']}\n"
        )