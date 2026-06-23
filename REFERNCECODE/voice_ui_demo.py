import json
import speech_recognition as sr
from sentence_transformers import SentenceTransformer, util

CONFIDENCE_THRESHOLD = 0.35

print("Loading component library...")
with open("code.json", "r", encoding="utf-8") as f:
    components = json.load(f)

print("Loading model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Embed the matchable text of every component once, up front.
intents = [c["intent"] for c in components]
intent_embeddings = model.encode(intents, convert_to_tensor=True)

recognizer = sr.Recognizer()


def listen():
    with sr.Microphone() as source:
        print("\nSpeak the component you want...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError:
        print("Internet connection issue")
    return None


while True:
    text = listen()
    if not text:
        continue

    print("You said:", text)
    if text.lower().strip() in ("exit", "quit", "stop"):
        break

    query = model.encode(text, convert_to_tensor=True)
    scores = util.cos_sim(query, intent_embeddings)[0]
    best_idx = int(scores.argmax())
    best_score = float(scores[best_idx])

    if best_score < CONFIDENCE_THRESHOLD:
        print(f"No confident match ({best_score:.2f}). Try rephrasing.")
        continue

    comp = components[best_idx]
    print(f"\nMatched: {comp['intent']}  ({best_score:.2f})\n")
    print("--- HTML ---")
    print(comp["html"])
    print("\n--- CSS ---")
    print(comp["css"])

    # Optionally append the rendered component to a live preview file.
    with open("preview.html", "a", encoding="utf-8") as out:
        out.write(f"<style>{comp['css']}</style>\n{comp['html']}\n")
