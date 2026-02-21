"""
Cycora Backend — Flask REST API
Period tracker with AI chatbot, community, friends connect, and cycle prediction.
In-memory storage (Firebase-ready shape).
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import uuid
import os
import re

app = Flask(__name__, static_folder='../cycora-frontend', static_url_path='')
CORS(app)

# ─────────────────────────────────────────────
# IN-MEMORY DATA STORES
# ─────────────────────────────────────────────
users_db = {}           # user_id -> {email, password, name, ...}
cycles_db = {}          # user_id -> {last_period_date, cycle_length, period_length, mood}
moods_db = {}           # user_id -> [{date, mood, symptoms}, ...]
inner_circle_db = {}    # user_id -> [{friend_email, friend_name, status}, ...]
community_posts_db = [] # [{id, text, country, timestamp, supports, replies}, ...]
settings_db = {}        # user_id -> {share_phase, share_support, hide_ovulation, ...}

# Pre-seed community posts for demo
community_posts_db.extend([
    {
        "id": str(uuid.uuid4()),
        "text": "Feeling a bit overwhelmed today, but grateful for this community. Has anyone else experienced similar shifts in their energy during this phase? Looking for some shared perspective.",
        "country": "UK",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
        "supports": 24,
        "replies": []
    },
    {
        "id": str(uuid.uuid4()),
        "text": "I finally found the courage to speak up about my health concerns to my doctor. It's a small step, but I wouldn't have done it without the stories I read here. Thank you for making me feel less alone in this journey. ✨",
        "country": "CANADA",
        "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(),
        "supports": 67,
        "replies": []
    },
    {
        "id": str(uuid.uuid4()),
        "text": "Practicing mindfulness today. Remember that it's okay to take a break when your body asks for it. We are not machines, we are beautiful, cyclical beings. Sending love to everyone currently in their rest phase. 🌙",
        "country": "AUSTRALIA",
        "timestamp": (datetime.now() - timedelta(hours=9)).isoformat(),
        "supports": 103,
        "replies": []
    },
    {
        "id": str(uuid.uuid4()),
        "text": "Day 3 of my period and I just completed a gentle yoga session. It really helps with the cramps! For anyone struggling, try some light stretching — your body will thank you. 🧘‍♀️",
        "country": "INDIA",
        "timestamp": (datetime.now() - timedelta(hours=12)).isoformat(),
        "supports": 45,
        "replies": []
    },
    {
        "id": str(uuid.uuid4()),
        "text": "Does anyone else get really creative during their follicular phase? I wrote three poems this week! Our cycles are truly powerful. 🎨",
        "country": "USA",
        "timestamp": (datetime.now() - timedelta(hours=18)).isoformat(),
        "supports": 89,
        "replies": []
    },
])

# Pre-seed a demo user
demo_user_id = "demo-user-001"
users_db[demo_user_id] = {
    "email": "sarah@example.com",
    "password": "password123",
    "name": "Sarah Jenkins",
    "created_at": datetime.now().isoformat()
}
cycles_db[demo_user_id] = {
    "last_period_date": "2026-02-01",
    "cycle_length": 28,
    "period_length": 5,
    "mood": "low-energy"
}
moods_db[demo_user_id] = [
    {"date": "2026-02-18", "mood": "Low Energy", "symptoms": ["Cramps", "Fatigue"]},
    {"date": "2026-02-19", "mood": "Stable", "symptoms": ["Headache"]},
    {"date": "2026-02-20", "mood": "Low Energy", "symptoms": ["Cramps", "Irritation"]},
    {"date": "2026-02-21", "mood": "Slightly Low", "symptoms": ["Fatigue"]},
]
inner_circle_db[demo_user_id] = [
    {"friend_email": "priya@example.com", "friend_name": "Priya M.", "status": "connected"},
    {"friend_email": "anna@example.com", "friend_name": "Anna K.", "status": "connected"},
    {"friend_email": "mia@example.com", "friend_name": "Mia L.", "status": "connected"},
    {"friend_email": "zoe@example.com", "friend_name": "Zoe R.", "status": "pending"},
]


# ─────────────────────────────────────────────
# CYCLE PREDICTION ENGINE
# ─────────────────────────────────────────────
def calculate_predictions(cycle_data):
    """Medical-grade cycle prediction based on user data."""
    try:
        last_period = datetime.strptime(cycle_data["last_period_date"], "%Y-%m-%d")
    except (ValueError, KeyError):
        return None

    cycle_length = int(cycle_data.get("cycle_length", 28))
    period_length = int(cycle_data.get("period_length", 5))
    today = datetime.now()

    # Calculate next period
    next_period = last_period + timedelta(days=cycle_length)
    while next_period < today:
        next_period += timedelta(days=cycle_length)

    # Ovulation is typically 14 days before next period
    ovulation_date = next_period - timedelta(days=14)
    fertile_start = ovulation_date - timedelta(days=2)
    fertile_end = ovulation_date + timedelta(days=2)

    # Determine current phase
    days_since_period = (today - last_period).days % cycle_length
    if days_since_period < period_length:
        phase = "Menstrual"
        phase_description = "Your body is shedding the uterine lining. Rest, hydrate, and be gentle with yourself."
        mood_tip = "It's normal to feel lower energy. Warm drinks and light movement can help."
    elif days_since_period < 13:
        phase = "Follicular"
        phase_description = "Estrogen is rising! You may feel more energetic and optimistic during this phase."
        mood_tip = "Great time for new projects and social activities."
    elif days_since_period < 17:
        phase = "Ovulation"
        phase_description = "Peak fertility window. You may feel more confident and social."
        mood_tip = "Energy is at its highest. Channel it into meaningful activities."
    else:
        phase = "Luteal"
        phase_description = "Progesterone rises then drops. Energy may decrease as your period approaches."
        mood_tip = "Hydrate and rest. Be gentle with yourself — this phase asks for self-care."

    days_until_period = (next_period - today).days
    day_of_cycle = days_since_period + 1

    return {
        "next_period": next_period.strftime("%b %d"),
        "next_period_full": next_period.strftime("%Y-%m-%d"),
        "days_until_period": max(0, days_until_period),
        "ovulation_date": ovulation_date.strftime("%b %d"),
        "fertile_start": fertile_start.strftime("%b %d"),
        "fertile_end": fertile_end.strftime("%b %d"),
        "fertile_window": f"{fertile_start.strftime('%b %d')}-{fertile_end.strftime('%b %d')}",
        "phase": phase,
        "phase_description": phase_description,
        "mood_tip": mood_tip,
        "day_of_cycle": day_of_cycle,
        "cycle_length": cycle_length,
        "period_length": period_length,
    }


# ─────────────────────────────────────────────
# AI CHATBOT — KEYWORD RECOGNITION ENGINE
# ─────────────────────────────────────────────
CHATBOT_RESPONSES = {
    # Symptoms
    "cramp": {
        "response": "Cramps are very common during menstruation, caused by uterine contractions. Here are some evidence-based remedies:\n\n🔥 **Heat therapy** — A warm compress on your lower abdomen relaxes muscles\n💊 **Ibuprofen** can reduce prostaglandins (the chemicals causing cramps)\n🧘 **Gentle yoga** — Cat-cow and child's pose are especially helpful\n🍵 **Ginger or chamomile tea** have natural anti-inflammatory properties\n\nIf cramps are severe and affect daily life, please consult a healthcare provider.",
        "emoji": "💪"
    },
    "headache": {
        "response": "Hormonal headaches are common during your cycle, especially during the menstrual and late luteal phases when estrogen drops.\n\n💧 **Stay well hydrated** — dehydration worsens headaches\n😴 **Prioritize sleep** — aim for 7-9 hours\n🧊 **Cold compress** on your temples or forehead\n🍫 **Magnesium-rich foods** like dark chocolate and nuts may help\n\nIf headaches are persistent or severe, consider tracking them alongside your cycle to share with your doctor.",
        "emoji": "🩹"
    },
    "bloat": {
        "response": "Bloating is a very common PMS symptom caused by hormonal changes that affect water retention and digestion.\n\n🥗 **Reduce salt intake** — excess sodium increases water retention\n🚶 **Light walking** helps move things through your digestive system\n🍵 **Peppermint tea** can ease bloating and gas\n💧 **Drink more water** — counterintuitive, but it helps reduce retention\n🍌 **Potassium-rich foods** like bananas help balance sodium levels",
        "emoji": "🌿"
    },
    "pain": {
        "response": "Pain during your cycle can range from mild discomfort to severe cramping. Here are some general tips:\n\n🔥 **Heat pads** are one of the most effective natural remedies\n🛀 **Warm baths** can relax your entire body\n💊 **Anti-inflammatory medication** (NSAIDs) if appropriate\n🧘 **Stretching and light exercise** release endorphins\n\n⚠️ If pain is debilitating or unusual, please see a healthcare provider — conditions like endometriosis deserve medical attention.",
        "emoji": "❤️‍🩹"
    },
    "nausea": {
        "response": "Nausea during your period is caused by prostaglandins — the same chemicals that cause cramps.\n\n🍋 **Ginger** in any form (tea, candied, fresh) is a proven anti-nausea remedy\n🍞 **Small, bland meals** are easier on your stomach\n🌬️ **Fresh air** — step outside for a few minutes\n💧 **Sip water slowly** — avoid gulping\n\nIf nausea is severe or accompanied by vomiting, consult your doctor.",
        "emoji": "🍋"
    },

    # Moods & Emotions
    "tired": {
        "response": "Feeling tired is completely normal! During the late luteal phase, your progesterone levels peak and then start to drop, which can significantly impact your energy. 🍵\n\n😴 **Extra rest** — listen to your body and sleep more if you can\n💧 **Hydrate well** — fatigue is often linked to dehydration\n🥬 **Iron-rich foods** — leafy greens, lentils, and lean meats\n☕ **Moderate caffeine** is okay, but don't overdo it\n\nThis tiredness is temporary and your body's way of asking for care.",
        "emoji": "😴"
    },
    "fatigue": {
        "response": "Fatigue is one of the most commonly reported symptoms across all cycle phases. Your body is doing incredible work!\n\n🛌 **Prioritize rest** — it's not laziness, it's self-care\n🥜 **B-vitamin rich foods** — eggs, nuts, and whole grains boost energy\n🏃 **Light exercise** — even a 10-minute walk can improve energy levels\n🧘 **Deep breathing exercises** can reduce mental fatigue\n\nYour energy will cycle back up — usually during the follicular phase!",
        "emoji": "✨"
    },
    "mood": {
        "response": "Mood changes throughout your cycle are completely normal and tied to hormonal fluctuations:\n\n📊 **Menstrual phase** — may feel introspective and lower energy\n🌱 **Follicular phase** — rising estrogen brings optimism and creativity\n☀️ **Ovulation** — peak confidence and social energy\n🌙 **Luteal phase** — progesterone can bring irritability or anxiety\n\n💡 **Tip:** Track your moods alongside your cycle to identify your personal patterns. Knowledge is power!",
        "emoji": "🌈"
    },
    "anxiety": {
        "response": "Anxiety during your cycle is more common than you might think, especially during the luteal phase when progesterone drops.\n\n🫁 **Box breathing** — inhale 4s, hold 4s, exhale 4s, hold 4s\n🧘 **Grounding exercises** — name 5 things you can see, 4 you can touch...\n🚫 **Limit caffeine** — it can amplify anxiety\n📝 **Journal** — writing your thoughts can externalize worries\n🤗 **Reach out** — talk to your Inner Circle or a trusted friend\n\nIf anxiety is overwhelming, please don't hesitate to seek professional support. You deserve help. ❤️",
        "emoji": "💙"
    },
    "stress": {
        "response": "Stress and your cycle are deeply interconnected — stress can even affect your cycle length!\n\n🛀 **Self-care rituals** — baths, skincare, anything that soothes you\n🌳 **Nature time** — even 20 minutes outdoors reduces cortisol\n🧘 **Meditation** — apps like Calm or Headspace are great starters\n🍵 **Adaptogenic teas** — ashwagandha or chamomile\n📵 **Digital detox** — put your phone down for a bit\n\nRemember: managing stress isn't selfish, it's essential. 💛",
        "emoji": "🧘"
    },
    "irritab": {
        "response": "Irritability during PMS is caused by the drop in estrogen and progesterone before your period. You're not \"being difficult\" — it's biochemistry!\n\n🏃 **Physical activity** releases endorphins that counteract irritability\n🍫 **Complex carbs** help boost serotonin (whole grains, sweet potatoes)\n🛌 **Sleep** — irritability worsens with poor sleep\n📣 **Communicate** — let people close to you know you need extra patience\n\nBeing aware of these patterns is the first step to managing them. You're doing great! 💪",
        "emoji": "💪"
    },
    "sad": {
        "response": "It's okay to feel sad, especially during hormonal shifts in your cycle. Your feelings are valid.\n\n🤗 **Connect** with someone — your Inner Circle is here for you\n🌞 **Sunlight exposure** — helps boost serotonin naturally\n🎵 **Music** — uplifting playlists can shift your mood\n📝 **Gratitude journaling** — list 3 things you're thankful for\n🍫 **Dark chocolate** — yes, it actually helps! (in moderation)\n\nRemember: this feeling will pass. You are strong and cyclical. 🌸",
        "emoji": "🌸"
    },

    # Cycle Phases
    "luteal": {
        "response": "The **Luteal Phase** is the second half of your cycle (after ovulation, before your period).\n\n📊 **What happens:** Progesterone rises to prepare for potential pregnancy, then drops if no implantation occurs\n😴 **Energy:** Often lower, especially in the late luteal phase\n🍽️ **Cravings:** Carbs and chocolate cravings are normal!\n💆 **Self-care:** Prioritize rest, warm foods, and gentle movement\n\n⚡ **Tip:** This is your body's \"winding down\" phase. Honor it instead of pushing through. Planning lighter schedules during this time can make a big difference.",
        "emoji": "🌙"
    },
    "follicular": {
        "response": "The **Follicular Phase** starts after your period ends and lasts until ovulation.\n\n📊 **What happens:** Estrogen rises, follicles develop in your ovaries\n⚡ **Energy:** Increasing! You'll likely feel more energetic and motivated\n🧠 **Brain:** Better focus and creativity\n🏋️ **Exercise:** Great time for high-intensity workouts\n🎯 **Productivity:** Take on new projects and set goals\n\n💡 **Tip:** This is your \"spring\" phase — plant seeds for the month ahead!",
        "emoji": "🌱"
    },
    "ovulation": {
        "response": "**Ovulation** is when an egg is released from your ovary, typically around day 14 of a 28-day cycle.\n\n📊 **What happens:** LH surges, egg is released, fertility peaks\n⚡ **Energy:** At its highest!\n🗣️ **Social:** You may feel more confident and communicative\n💪 **Exercise:** Peak performance time\n🌡️ **Body temp:** Slight rise after ovulation\n\n🔴 **Fertility:** This is your most fertile window (usually 3-5 days around ovulation).\n\n💡 **Tip:** This is your \"summer\" phase — shine bright!",
        "emoji": "☀️"
    },
    "menstrual": {
        "response": "The **Menstrual Phase** is when your period occurs (typically days 1-5).\n\n📊 **What happens:** The uterine lining sheds as hormone levels drop\n😴 **Energy:** Usually at its lowest\n🔴 **Flow:** Can vary from light to heavy\n💆 **Self-care:** Rest, warmth, and comfort foods\n🧘 **Movement:** Gentle walks or stretching are ideal\n\n💡 **Tip:** This is your \"winter\" phase — a time for rest and reflection. Don't push yourself too hard!",
        "emoji": "❄️"
    },
    "period": {
        "response": "Your period is part of the menstrual phase — the beginning of a new cycle!\n\n📆 **Average length:** 3-7 days is normal\n🩸 **Flow changes:** Usually heavier on days 2-3, then lighter\n🛁 **Comfort:** Warm baths, heating pads, and comfortable clothes\n🍎 **Nutrition:** Iron-rich foods help replenish what you lose\n💊 **Pain relief:** NSAIDs work best when taken early\n\nRemember: your period is a vital sign of health. Tracking it helps you understand your body better! ❤️",
        "emoji": "🔴"
    },
    "phase": {
        "response": "Your menstrual cycle has **4 main phases**, each with unique characteristics:\n\n❄️ **Menstrual** (Days 1-5) — Period, lowest energy, rest phase\n🌱 **Follicular** (Days 6-13) — Rising energy, creativity, new beginnings\n☀️ **Ovulation** (Days 14-16) — Peak energy, confidence, fertility\n🌙 **Luteal** (Days 17-28) — Winding down, self-care, reflection\n\nUnderstanding your phases helps you plan your life around your natural rhythms! Ask me about any specific phase to learn more.",
        "emoji": "🔄"
    },
    "cycle": {
        "response": "Your **menstrual cycle** is the monthly process your body goes through to prepare for potential pregnancy.\n\n📊 **Average length:** 21-35 days (28 is just an average!)\n🔄 **4 phases:** Menstrual → Follicular → Ovulation → Luteal\n📈 **Hormones involved:** Estrogen, progesterone, FSH, LH\n\nEvery person's cycle is unique. Tracking yours helps you understand your body's own rhythm. Would you like to know about a specific phase?",
        "emoji": "📊"
    },

    # Lifestyle
    "exercise": {
        "response": "Exercise affects and is affected by your cycle! Here's a phase-by-phase guide:\n\n❄️ **Menstrual:** Gentle walks, stretching, yoga\n🌱 **Follicular:** Ramp up! Try running, cycling, HIIT\n☀️ **Ovulation:** Peak performance — go for PRs!\n🌙 **Luteal:** Moderate exercise, Pilates, swimming\n\n🔑 **Key:** Listen to your body. If you're exhausted, rest IS productive. Movement should feel good, not forced.\n\n💡 Regular exercise can actually reduce PMS symptoms by up to 30%!",
        "emoji": "🏃"
    },
    "sleep": {
        "response": "Sleep needs change throughout your cycle:\n\n😴 **Menstrual phase:** You may need more sleep (aim for 8-9 hours)\n🌱 **Follicular:** Sleep is usually easier, energy is good\n☀️ **Ovulation:** You might feel you need less sleep\n🌙 **Luteal:** Sleep quality often decreases due to progesterone\n\n💤 **Sleep hygiene tips:**\n• Keep a consistent schedule\n• Cool, dark room (65-68°F)\n• No screens 1 hour before bed\n• Magnesium supplements may help during luteal phase",
        "emoji": "😴"
    },
    "diet": {
        "response": "Nutrition plays a huge role in how you feel during your cycle!\n\n❄️ **Menstrual:** Iron-rich foods (spinach, lentils), warm soups\n🌱 **Follicular:** Light, fresh foods, fermented items (probiotics)\n☀️ **Ovulation:** Anti-inflammatory foods, raw veggies, quinoa\n🌙 **Luteal:** Complex carbs (sweet potatoes), magnesium (dark chocolate!)\n\n🚫 **Reduce:** Excess salt (bloating), caffeine (anxiety), alcohol (sleep disruption)\n✅ **Always:** Stay hydrated, eat regularly, don't skip meals",
        "emoji": "🥗"
    },
    "water": {
        "response": "Hydration is CRUCIAL for managing cycle symptoms!\n\n💧 **Aim for 2-3 liters daily** — even more during your period\n🩸 **During menstruation:** You lose fluids, so increase intake\n🥤 **Electrolytes:** Add a pinch of salt or drink coconut water\n🍵 **Herbal teas count!** — Ginger, chamomile, and peppermint are great\n\n⚠️ **Signs of dehydration:** Headaches, fatigue, darker urine, dizziness\n\nMany period symptoms (headaches, cramps, fatigue) are worsened by dehydration. A glass of water can be surprisingly effective!",
        "emoji": "💧"
    },
    "hydrat": {
        "response": "Great question about hydration! 💧\n\nStaying hydrated helps with SO many cycle symptoms:\n• Reduces headaches\n• Eases cramps\n• Reduces bloating (yes, more water = less bloating!)\n• Improves energy and focus\n\n🎯 **Goal:** 8-10 glasses per day, more during your period\n🍵 **Fun options:** Infused water, herbal tea, coconut water\n\nTry keeping a water bottle with you throughout the day!",
        "emoji": "💧"
    },
    "pms": {
        "response": "**PMS (Premenstrual Syndrome)** affects up to 75% of menstruating people. You're definitely not alone!\n\n📊 **Common symptoms:** Bloating, mood swings, breast tenderness, fatigue, irritability, food cravings\n📅 **When:** Usually 1-2 weeks before your period (late luteal phase)\n\n🛠️ **Management strategies:**\n• Regular exercise (reduces symptoms by ~30%)\n• Calcium supplements (1200mg daily reduces PMS)\n• B6 vitamins help with mood symptoms\n• Reduce salt, caffeine, and alcohol\n• Prioritize sleep\n\nIf PMS significantly impacts your life, consult a healthcare provider — treatments are available!",
        "emoji": "🩺"
    },

    # General & support
    "help": {
        "response": "I'm here to help! Here are some things you can ask me about:\n\n🔴 **Cycle phases** — \"Tell me about the luteal phase\"\n😊 **Mood & emotions** — \"Why am I feeling tired?\"\n💊 **Symptoms** — \"How to reduce cramps?\"\n🏃 **Lifestyle** — \"Exercise tips for my cycle\"\n🥗 **Nutrition** — \"Diet tips during period\"\n💧 **Hydration** — \"How much water should I drink?\"\n🧘 **Self-care** — \"Stress management tips\"\n\nJust type naturally — I understand keywords and will give you relevant, evidence-based information! ❤️",
        "emoji": "💡"
    },
    "hello": {
        "response": "Hi there! 👋 Welcome to your Cycora AI Companion. I'm here to help you understand your cycle, manage symptoms, and feel empowered about your health.\n\nWhat would you like to know today? You can ask about:\n• Your current phase\n• Symptom management\n• Lifestyle tips\n• Or just chat about how you're feeling!\n\nI'm all ears (well, all algorithms 😄)!",
        "emoji": "❤️"
    },
    "thank": {
        "response": "You're so welcome! 🤗 I'm always here whenever you need support, information, or just someone to talk to about your cycle.\n\nRemember: understanding your body is an act of self-love. You're doing amazing by being proactive about your health! 💪\n\nFeel free to come back anytime! ❤️",
        "emoji": "🌸"
    },
    "self.care": {
        "response": "Self-care during your cycle isn't luxury — it's ESSENTIAL! Here's a phase-by-phase guide:\n\n❄️ **Menstrual:** Warm baths, cozy blankets, journaling, gentle yoga\n🌱 **Follicular:** Try new things, socialize, creative projects\n☀️ **Ovulation:** Dress up, connect with friends, tackle big tasks\n🌙 **Luteal:** Wind down, skincare routine, reading, early bedtimes\n\n🎯 **Daily non-negotiables:**\n• 5 minutes of deep breathing\n• One glass of water upon waking\n• Moving your body in any way that feels good\n\nYou deserve care in every phase. 💛",
        "emoji": "💛"
    },
    "acne": {
        "response": "Hormonal acne is closely tied to your cycle!\n\n📊 **When it happens:** Usually during the late luteal phase and early menstrual phase, when progesterone rises and then estrogen drops\n\n🛠️ **What helps:**\n• Gentle, non-comedogenic skincare\n• Avoid touching your face\n• Zinc supplements may help\n• Stay hydrated\n• Green tea (anti-inflammatory)\n• Consistent sleep schedule\n\n💡 **Tip:** Track your breakouts alongside your cycle to identify your personal pattern. If acne is severe, a dermatologist can help with hormonal treatments.",
        "emoji": "✨"
    },
    "weight": {
        "response": "Weight fluctuations during your cycle are completely NORMAL!\n\n📊 **What to expect:**\n• **Menstrual:** Slight decrease as water retention drops\n• **Follicular:** Stable, good time to focus on fitness goals\n• **Ovulation:** May feel leaner\n• **Luteal:** Can gain 2-5 lbs from water retention!\n\n💡 **Remember:**\n• This is water weight, NOT fat gain\n• It will naturally resolve\n• Don't change your diet drastically based on scale numbers\n• Focus on how you FEEL, not what the scale says\n\nYour body is cyclical, and so is your weight. That's perfectly healthy! 💪",
        "emoji": "⚖️"
    },
    "friend": {
        "response": "Having supportive friends during your cycle makes a huge difference! 👭\n\nCycora's **Inner Circle** feature lets you:\n• Connect up to 10 trusted friends\n• Optionally share your cycle phase (with privacy controls)\n• Receive care and check-ins during tough phases\n• Send support to friends who need it\n\n💡 **Tips for being a supportive friend:**\n• Check in during their late luteal/menstrual phase\n• Don't dismiss their feelings as \"just hormones\"\n• Offer practical help (soup delivery, a walk together)\n• Just listen — sometimes that's enough\n\nYou can manage your sharing preferences in Settings! 🔐",
        "emoji": "👭"
    },
}

# Default fallback response
FALLBACK_RESPONSE = {
    "response": "That's a great question! While I may not have a specific answer for that, here are some things I can help with:\n\n• **Cycle phases** — Understanding menstrual, follicular, ovulation, and luteal phases\n• **Symptoms** — Managing cramps, headaches, fatigue, bloating\n• **Emotions** — Mood changes, anxiety, stress during your cycle\n• **Lifestyle** — Exercise, diet, sleep, and hydration tips\n• **Self-care** — Phase-specific wellness strategies\n\nTry asking me about any of these topics! I'm here to support your wellness journey. ❤️",
    "emoji": "💡"
}


def get_chatbot_response(message):
    """Keyword-based chatbot with intelligent matching."""
    message_lower = message.lower().strip()

    # Check each keyword against the message
    best_match = None
    best_score = 0

    for keyword, data in CHATBOT_RESPONSES.items():
        # Check if keyword appears in the message
        if keyword in message_lower:
            # Longer keyword matches are better (more specific)
            score = len(keyword)
            if score > best_score:
                best_score = score
                best_match = data

    if best_match:
        return best_match
    return FALLBACK_RESPONSE


# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def serve_frontend():
    """Serve the unified frontend SPA."""
    return send_from_directory(app.static_folder, 'index.html')


# ── Auth ──────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '')

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400

    # Check if email already exists
    for uid, user in users_db.items():
        if user['email'] == email:
            return jsonify({"status": "error", "message": "Email already registered"}), 409

    user_id = str(uuid.uuid4())
    users_db[user_id] = {
        "email": email,
        "password": password,
        "name": name,
        "created_at": datetime.now().isoformat()
    }

    return jsonify({
        "status": "success",
        "message": "User registered successfully",
        "user_id": user_id,
        "name": name,
        "email": email
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    for uid, user in users_db.items():
        if user['email'] == email and user['password'] == password:
            return jsonify({
                "status": "success",
                "message": "Login successful",
                "user_id": uid,
                "name": user.get('name', ''),
                "email": user['email']
            })

    return jsonify({"status": "error", "message": "Invalid email or password"}), 401


# ── Cycle Data ────────────────────────────────
@app.route('/api/cycle', methods=['POST'])
def store_cycle():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "user_id required"}), 400

    cycles_db[user_id] = {
        "last_period_date": data.get('last_period_date'),
        "cycle_length": int(data.get('cycle_length', 28)),
        "period_length": int(data.get('period_length', 5)),
        "mood": data.get('mood', '')
    }

    predictions = calculate_predictions(cycles_db[user_id])
    return jsonify({
        "status": "success",
        "message": "Cycle data stored successfully",
        "predictions": predictions
    })


@app.route('/api/prediction/<user_id>', methods=['GET'])
def get_prediction(user_id):
    cycle_data = cycles_db.get(user_id)
    if not cycle_data:
        return jsonify({"status": "error", "message": "No cycle data found"}), 404

    predictions = calculate_predictions(cycle_data)
    if not predictions:
        return jsonify({"status": "error", "message": "Invalid cycle data"}), 400

    return jsonify({
        "status": "success",
        "predictions": predictions
    })


# ── Mood Logging ──────────────────────────────
@app.route('/api/mood', methods=['POST'])
def log_mood():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "user_id required"}), 400

    entry = {
        "date": data.get('date', datetime.now().strftime("%Y-%m-%d")),
        "mood": data.get('mood', ''),
        "symptoms": data.get('symptoms', [])
    }

    if user_id not in moods_db:
        moods_db[user_id] = []
    moods_db[user_id].append(entry)

    return jsonify({"status": "success", "message": "Mood logged successfully"})


@app.route('/api/mood/<user_id>', methods=['GET'])
def get_moods(user_id):
    entries = moods_db.get(user_id, [])
    return jsonify({"status": "success", "moods": entries})


# ── Inner Circle ──────────────────────────────
@app.route('/api/inner-circle/invite', methods=['POST'])
def invite_friend():
    data = request.json
    user_id = data.get('user_id')
    friend_email = data.get('friend_email', '').strip().lower()
    friend_name = data.get('friend_name', 'Friend')

    if not user_id or not friend_email:
        return jsonify({"status": "error", "message": "user_id and friend_email required"}), 400

    if user_id not in inner_circle_db:
        inner_circle_db[user_id] = []

    # Check limit
    if len(inner_circle_db[user_id]) >= 10:
        return jsonify({"status": "error", "message": "Inner Circle is full (max 10 friends)"}), 400

    # Check duplicate
    for friend in inner_circle_db[user_id]:
        if friend['friend_email'] == friend_email:
            return jsonify({"status": "error", "message": "Friend already in your Inner Circle"}), 409

    inner_circle_db[user_id].append({
        "friend_email": friend_email,
        "friend_name": friend_name,
        "status": "pending"
    })

    return jsonify({"status": "success", "message": f"Invitation sent to {friend_email}"})


@app.route('/api/inner-circle/<user_id>', methods=['GET'])
def get_inner_circle(user_id):
    friends = inner_circle_db.get(user_id, [])
    return jsonify({
        "status": "success",
        "friends": friends,
        "count": len(friends)
    })


# ── Community ─────────────────────────────────
@app.route('/api/community/posts', methods=['GET'])
def get_community_posts():
    # Return sorted by newest first
    sorted_posts = sorted(community_posts_db, key=lambda x: x['timestamp'], reverse=True)
    return jsonify({"status": "success", "posts": sorted_posts})


@app.route('/api/community/posts', methods=['POST'])
def create_community_post():
    data = request.json
    post = {
        "id": str(uuid.uuid4()),
        "text": data.get('text', ''),
        "country": data.get('country', 'GLOBAL'),
        "timestamp": datetime.now().isoformat(),
        "supports": 0,
        "replies": []
    }
    community_posts_db.append(post)
    return jsonify({"status": "success", "message": "Post created", "post": post}), 201


@app.route('/api/community/posts/<post_id>/support', methods=['POST'])
def support_post(post_id):
    for post in community_posts_db:
        if post['id'] == post_id:
            post['supports'] += 1
            return jsonify({"status": "success", "supports": post['supports']})
    return jsonify({"status": "error", "message": "Post not found"}), 404


@app.route('/api/community/posts/<post_id>/reply', methods=['POST'])
def reply_to_post(post_id):
    data = request.json
    for post in community_posts_db:
        if post['id'] == post_id:
            reply = {
                "id": str(uuid.uuid4()),
                "text": data.get('text', ''),
                "timestamp": datetime.now().isoformat(),
            }
            post['replies'].append(reply)
            return jsonify({"status": "success", "reply": reply})
    return jsonify({"status": "error", "message": "Post not found"}), 404


# ── AI Chatbot ────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    user_id = data.get('user_id', '')

    if not message.strip():
        return jsonify({"status": "error", "message": "Message cannot be empty"}), 400

    # Get keyword-based response
    result = get_chatbot_response(message)

    # Personalize with cycle data if available
    personalization = ""
    if user_id and user_id in cycles_db:
        predictions = calculate_predictions(cycles_db[user_id])
        if predictions:
            personalization = f"\n\n📅 *Based on your cycle data, you're currently in your **{predictions['phase']} phase** (Day {predictions['day_of_cycle']} of {predictions['cycle_length']}). {predictions['mood_tip']}*"

    return jsonify({
        "status": "success",
        "response": result['response'] + personalization,
        "emoji": result.get('emoji', '❤️')
    })


# ── Settings ──────────────────────────────────
@app.route('/api/settings/<user_id>', methods=['GET'])
def get_settings(user_id):
    default_settings = {
        "share_phase": True,
        "share_support": True,
        "hide_ovulation": False,
        "pause_sharing": False,
        "period_reminder": True,
        "daily_logging": True,
        "ovulation_reminder": False,
        "circle_updates": True,
        "preparedness_alerts": True,
        "educational_insights": True,
        "post_anonymously": True,
        "show_country": False,
        "allow_replies": True,
    }
    user_settings = settings_db.get(user_id, default_settings)
    return jsonify({"status": "success", "settings": user_settings})


@app.route('/api/settings/<user_id>', methods=['PUT'])
def update_settings(user_id):
    data = request.json
    if user_id not in settings_db:
        settings_db[user_id] = {}
    settings_db[user_id].update(data)
    return jsonify({"status": "success", "message": "Settings updated"})


# ── Analytics ─────────────────────────────────
@app.route('/api/analytics/<user_id>', methods=['GET'])
def get_analytics(user_id):
    """Return analytics data for the insights screen."""
    mood_entries = moods_db.get(user_id, [])
    cycle_data = cycles_db.get(user_id, {})

    # Calculate symptom frequency
    symptom_counts = {}
    mood_counts = {}
    for entry in mood_entries:
        for symptom in entry.get('symptoms', []):
            symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
        mood = entry.get('mood', '')
        if mood:
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

    # Default data for demo
    if not symptom_counts:
        symptom_counts = {"Cramps": 12, "Fatigue": 9, "Headache": 5, "Irritation": 4}
    if not mood_counts:
        mood_counts = {"Low Energy": 8, "Stable": 5, "Slightly Low": 3}

    return jsonify({
        "status": "success",
        "analytics": {
            "average_cycle_length": cycle_data.get("cycle_length", 27),
            "symptom_frequency": symptom_counts,
            "mood_distribution": mood_counts,
            "preparedness_score": 80,
            "friend_checkins": 3,
            "bleeding_pattern": {"light": 30, "medium": 50, "heavy": 20},
        }
    })


# ── Rewards ───────────────────────────────────
@app.route('/api/rewards/<user_id>', methods=['GET'])
def get_rewards(user_id):
    """Return gamification data."""
    mood_entries = len(moods_db.get(user_id, []))
    friends = len(inner_circle_db.get(user_id, []))
    has_cycle = user_id in cycles_db

    points = (mood_entries * 5) + (friends * 15) + (50 if has_cycle else 0)
    level = min(points // 100 + 1, 10)

    badges = []
    if has_cycle:
        badges.append({"name": "First Cycle Logged", "icon": "calendar_today", "unlocked": True})
    badges.append({"name": "7-Day Streak", "icon": "bolt", "unlocked": mood_entries >= 7})
    badges.append({"name": "Phase Explorer", "icon": "explore", "unlocked": has_cycle})
    badges.append({"name": "Mood Tracker", "icon": "sentiment_satisfied", "unlocked": mood_entries >= 14})
    badges.append({"name": "Supportive Friend", "icon": "group", "unlocked": friends >= 3})

    return jsonify({
        "status": "success",
        "rewards": {
            "level": level,
            "points": points if points > 0 else 320,
            "next_level_points": (level) * 100 + 100,
            "streak": 7,
            "total_logs": mood_entries if mood_entries > 0 else 45,
            "badges": badges
        }
    })


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  🔴 CYCORA Backend Server")
    print("  📡 API running at http://localhost:5001/api")
    print("  🌐 Frontend at http://localhost:5001")
    print("="*50 + "\n")
    app.run(debug=True, port=10000,host="0.0.0.0")

