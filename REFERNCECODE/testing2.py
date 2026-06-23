import json
import pickle
from sentence_transformers import SentenceTransformer, util
from google import genai


API_KEY = "AQ.Ab8RN6JJr4CH2wlFVVH7rWbCL1jC0a2eH8AGv-QH6CZXckdEcQ"
CONFIDENCE_THRESHOLD = 0.40

client = genai.Client(
    api_key=API_KEY
)

print("Loading FAQ data...")

with open("faq.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

print("Loading embeddings...")

with open("faq_embeddings.pkl", "rb") as f:
    faq_embeddings = pickle.load(f)

print("Loading sentence transformer model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("\nAI Chatbot Ready!")
print("Type 'exit' to quit.\n")

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
    )[:3]

    best_idx = top_results[0]
    best_score = scores[best_idx]

    print("\nTop Matches:")

    for idx in top_results:
        print(
            f"- {faq_data[idx]['question']} "
            f"({float(scores[idx]):.4f})"
        )

    print()

    # ==========================
    # LOW CONFIDENCE
    # ==========================

    if best_score < CONFIDENCE_THRESHOLD:

        print(
            "Bot: Sorry, I couldn't find a reliable answer in the FAQ database.\n"
        )

        continue

    # ==========================
    # BUILD FAQ CONTEXT
    # ==========================

    faq_context = ""

    for idx in top_results:

        faq_context += f"""
Question: {faq_data[idx]['question']}
Answer: {faq_data[idx]['answer']}

"""

    # ==========================
    # GEMINI PROMPT
    # ==========================

    prompt = f"""
You are a helpful customer support assistant.

Use ONLY the FAQ information below.

FAQ Knowledge:

{faq_context}

User Question:
{user_question}

Rules:
1. Answer only from the FAQ knowledge.
2. Do not make up information.
3. If the answer is not available in the FAQ knowledge, reply:
   "Sorry, I could not find that information in our FAQ database."
4. Keep the answer concise and natural.
"""

    # ==========================
    # GEMINI RESPONSE
    # ==========================

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        print(f"Bot: {response.text}\n")

    except Exception as e:

        print(
            f"Bot: Error communicating with Gemini: {str(e)}\n"
        )