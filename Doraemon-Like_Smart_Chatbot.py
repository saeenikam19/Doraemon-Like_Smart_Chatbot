import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
import webbrowser
import re
import requests
import os
import time
import json

# ---------------- CONFIG ----------------
genai.configure(api_key="YOUR_API")
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat(history=[])

engine = pyttsx3.init()
engine.setProperty("rate", 140)
engine.setProperty("volume", 1.0)
voices = engine.getProperty("voices")
engine.setProperty("voice", voices[0].id)


PROFILE_FILE = "profile.json"

# ---------------- SYLLABUS ----------------
SYLLABUS = {
    "6": ["Math", "Science", "English", "History"],
    "7": ["Math", "Science", "English", "Geography"],
    "8": ["Math", "Science", "English", "History"],
    "9": ["Math", "Physics", "Chemistry", "Biology", "English"],
    "10": ["Math", "Physics", "Chemistry", "Biology", "English", "History"]
}

OFF_TOPIC = [
    "pubg", "free fire", "fortnite", "cricket", "football", "movie",
    "song", "music", "dance", "instagram", "whatsapp", "tiktok",
    "girlfriend", "boyfriend", "car", "bike", "money", "gaming", "game"
]

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"
}

# active profile
profile = {"name": "Guest", "standard": "8", "subject": None, "topic": None}

# ---------------- UTILITIES ----------------
def save_profile():
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f)

def load_profile():
    global profile
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as f:
            profile = json.load(f)

def clean_text(text):
    return re.sub(r"[*_#>`~]", "", text)

def speak(text):
    text = clean_text(str(text))
    print("🤖 Gemini:", text)
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("TTS error:", e)

def stop_all():

        os.system("taskkill /im chrome.exe /f >nul 2>&1")
        os.system("taskkill /im msedge.exe /f >nul 2>&1")


def listen(timeout=10, phrase_time_limit=15):
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        text = r.recognize_google(audio).lower()
        print("👤 You said:", text)
        return text
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print("⚠️ Mic error:", e)
        return None

def get_chat_response(prompt):
    try:
        words = prompt.strip().split()
        if len(words) <= 2:  
            return f"Can you please ask a more complete question about {profile.get('topic')}?"

        instruction = f"Answer briefly for Standard {profile['standard']} student in simple language. Max 4 sentences. "
        resp = chat.send_message(f"{instruction}{prompt}")
        return resp.text
    except Exception as e:
        print("Gemini error:", e)
        return "Sorry, I had trouble processing that."

# ---------------- IMAGE HANDLER ----------------
def show_image(query):
    search_query = re.sub(r"^(show me|show|please)\s*", "", query, flags=re.I)
    search_url = f"https://www.google.com/search?tbm=isch&q={requests.utils.requote_uri(search_query)}"

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(search_url, timeout=8, headers=headers).text

        # Try to find first image
        match = re.search(r'"ou":"(.*?)"', html)
        if not match:
            match = re.search(r'"https://[^"]+\.(jpg|png|jpeg)"', html)

        if match:
            first_img = match.group(0).replace('"', "").replace("\\u003d", "=").replace("\\u0026", "&")
            webbrowser.open(first_img)
            return f"Showing first image for {search_query}"
        else:
            webbrowser.open(search_url)
            return f"Could not fetch image directly. Showing search results for {search_query}"

    except Exception as e:
        print("Image error:", e)
        webbrowser.open(search_url)
        return f"Error occurred. Showing search results for {search_query}"

# ---------------- VIDEO HANDLER ----------------
def show_video(query):
    search_query = re.sub(r"^(show me|show|please|play)\s*", "", query, flags=re.I)
    search_url = f"https://www.youtube.com/results?search_query={requests.utils.requote_uri(search_query)}"
    try:
        html = requests.get(search_url, timeout=6).text
        ids = re.findall(r"watch\?v=(\S{11})", html)
        if ids:
            vid = ids[0]
            embed = f"https://www.youtube.com/embed/{vid}?autoplay=1&rel=0&modestbranding=1"
            webbrowser.open(embed)
            return f"Playing video for {search_query}"
        else:
            return "Sorry, I couldn't find a video."
    except Exception as e:
        print("Video error:", e)
        return "Error finding video."

def normalize_standard(text):
    if not text:
        return None
    text = text.lower()
    m = re.search(r"\d+", text)
    if m:
        return m.group(0)
    for w, n in NUMBER_WORDS.items():
        if w in text:
            return n
    return None

# ---------------- NAME + STANDARD EXTRACTION ----------------
def extract_name_and_standard(text):
    name = None
    std = None
    text = text.lower()

    match = re.search(r"my name is (\w+)", text)
    if match:
        name = match.group(1)

    if not name:
        words = text.split()
        if len(words) > 0:
            name = words[-1]

    s = normalize_standard(text)
    if s and s in SYLLABUS:
        std = s

    return name.title() if name else None, std

# ---------------- INTERACTIVE FLOW ----------------
def create_profile(first_time=True):
    global profile

    if first_time:
        speak("Hello! Please tell me your name and standard together. Example: My name is Rahul and I am in Standard eight.")
        text = listen()
        if not text:
            text = input("Enter name and standard: ").strip()

        name, std = extract_name_and_standard(text)

        while not name or not std:
            speak("Sorry, I didn’t catch that. Please say again like: My name is Anjali and I am in Standard 9.")
            text = listen()
            if not text:
                text = input("Enter name and standard: ").strip()
            name, std = extract_name_and_standard(text)

        profile["name"] = name
        profile["standard"] = std
        profile["subject"] = None
        profile["topic"] = None

        speak(f"Welcome {profile['name']}. I will help you with Standard {profile['standard']}.")
        save_profile()
        choose_subject_and_topic()

    else:
        speak(f"Welcome back {profile['name']} from Standard {profile['standard']}. Do you want to continue with {profile.get('subject')} - {profile.get('topic')} or reset your profile?")
        choice = listen()
        if not choice:
            choice = input("Continue or reset? ").strip().lower()

        if "reset" in choice:
            profile.update({"name": "Guest", "standard": "8", "subject": None, "topic": None})
            save_profile()
            create_profile(first_time=True)
        else:
            speak(f"Okay! Continuing with {profile.get('subject')} - {profile.get('topic')}.")

def choose_subject_and_topic():
    subjects = SYLLABUS.get(profile["standard"], [])
    while True:
        speak("Which subject would you like to learn? Your subjects are: " + ", ".join(subjects))
        subj_text = listen()
        if not subj_text:
            subj_text = input("Enter subject: ").strip().lower()
        chosen = None
        for s in subjects:
            if s.lower() in subj_text:
                chosen = s
                break
        if chosen:
            profile["subject"] = chosen
            break
        else:
            speak("I did not understand that subject. Please try again.")

    speak(f"Which topic in {profile['subject']} do you want to learn?")
    topic_text = listen()
    if not topic_text:
        topic_text = input("Enter topic: ").strip().lower()
    profile["topic"] = topic_text
    save_profile()

# ---------------- MAIN LOOP ----------------
def voice_mode():
    if os.path.exists(PROFILE_FILE):
        load_profile()
        create_profile(first_time=False)
    else:
        create_profile(first_time=True)

    speak("Ask your syllabus related questions now.")
    while True:
        command = listen()
        if command is None:
            command = input("⌨️ Please type your question (or 'exit'): ").strip().lower()

        if any(word in command for word in ["exit", "quit", "bye", "stop"]):
            speak("You're welcome! Goodbye. We’ll continue next time.")
            stop_all()
            continue

        # --- OFF TOPIC CHECK ---
        if any(bad in command for bad in OFF_TOPIC):
            speak("Sorry, I cannot answer off-topic questions. Please ask syllabus related queries.")
            continue

        # --- NEW FEATURE: change subject/topic ---
        if "change subject" in command:
            profile["subject"] = None
            profile["topic"] = None
            save_profile()
            choose_subject_and_topic()
            speak(f"Subject has been updated to {profile['subject']} - {profile['topic']}.")
            speak(f"Now you can ask your syllabus related questions on {profile['subject']} - {profile['topic']}.")
            continue

        if "change topic" in command:
            profile["topic"] = None
            save_profile()
            speak(f"Which topic in {profile['subject']} do you want to learn?")
            topic_text = listen()
            if not topic_text:
                topic_text = input("Enter topic: ").strip().lower()
            profile["topic"] = topic_text
            save_profile()
            speak(f"Topic changed to {profile['subject']} - {profile['topic']}.")
            speak(f"Now you can ask your syllabus related questions on {profile['subject']} - {profile['topic']}.")
            continue

        # diagram / example / practice
        if profile.get("topic") and "diagram" in command:
            speak(show_image(f"diagram of {profile['topic']}"))
            continue
        if profile.get("topic") and "example" in command:
            resp = get_chat_response(f"Give a simple example of {profile['topic']} for Standard {profile['standard']}.")
            speak(resp)
            continue
        if profile.get("topic") and "practice" in command:
            resp = get_chat_response(f"Give one simple practice question on {profile['topic']} for Standard {profile['standard']}.")
            speak(resp)
            continue

        # image/video requests
        if "image" in command or "picture" in command:
            speak(show_image(command))
            continue
        if "video" in command or "play" in command:
            speak(show_video(command))
            continue

        # default Gemini response
        resp = get_chat_response(command)
        speak(resp)

if __name__ == "__main__":
    voice_mode()
