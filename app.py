import json
import random
import time
import os
from typing import List, Dict, Any, Tuple, Optional
import httpx

import gradio as gr
from openai import OpenAI

# ==========================================
# CONFIGURATION
# ==========================================

# LocalAI Configuration
LOCALAI_BASE_URL = "http://localhost:8080/v1"
LOCALAI_DUMMY_KEY = "sk-localai-dummy-key"

# Model settings
MODEL_NAME = "gpt-3.5-turbo"
TEMPERATURE = 0.7

# Game Settings
CATEGORIES = [
    "🎃 General Halloween",
    "🎬 Horror Movies",
    "🧛 Monsters & Myths",
    "👻 Haunted History",
    "🧙‍♀️ Witches & Spells",
    "🍬 Candy & Traditions",
    "📖 Urban Legends"
]

AUDIENCE_MODES = ["Kids (Spooky Fun)", "Adults (True Horror)"]
DIFFICULTIES = ["Easy", "Medium", "Hard", "Nightmare"]

# ==========================================
# AI & DATA LOGIC
# ==========================================

def get_openai_client() -> OpenAI:
    # Added strict timeout to prevent "Processing..." hang
    return OpenAI(
        base_url=LOCALAI_BASE_URL,
        api_key=LOCALAI_DUMMY_KEY,
        timeout=3.0, 
        max_retries=0
    )

def generate_system_prompt(audience: str, difficulty: str) -> str:
    tone = "lighthearted, funny, and spooky but NOT scary" if "Kids" in audience else "dark, eerie, suspenseful, and strictly for mature audiences"
    complexity = "simple, direct, and educational" if "Kids" in audience else "challenging, obscure, and detailed"
    
    return f"""You are a Halloween Game Master. 
    Target Audience: {audience}
    Tone: {tone}
    Difficulty Level: {difficulty} ({complexity})

    Return ONLY JSON matching this structure:
    {{
      "topic": "Creative Title for the Quiz",
      "questions": [
        {{
          "question": "The question text",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_index": 0,
          "explanation": "Fun or spooky fact explaining the answer.",
          "visual_cue": "A short 3-word description of a scene for this question (e.g. 'foggy graveyard', 'cute pumpkin')"
        }}
      ]
    }}

    Rules:
    1. Generate exactly N questions.
    2. Options must be exactly 4.
    3. correct_index is 0-3.
    4. For 'Kids': Focus on candy, costumes, cartoons (Casper, Scooby Doo), and fun monsters. NO gore.
    5. For 'Adults': Focus on classic slashers, psychological horror, obscure lore, and true crime history.
    """

def generate_questions(category: str, count: int, audience: str, difficulty: str) -> Dict[str, Any]:
    client = get_openai_client()
    sys_prompt = generate_system_prompt(audience, difficulty)
    user_prompt = f"Create a {count}-question quiz about '{category}' for {audience} at {difficulty} difficulty."

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = resp.choices[0].message.content.strip()
        
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        data = json.loads(content.strip())
        return _validate_payload(data, count, audience)
    except Exception as e:
        print(f"⚠️ AI Connection Failed ({e}). Switching to Offline Backup.")
        return _get_fallback_data(category, count, audience)

def _validate_payload(data: Dict[str, Any], n: int, audience: str) -> Dict[str, Any]:
    if not isinstance(data, dict) or "questions" not in data:
        return _get_fallback_data("Error", n, audience)
    
    valid_questions = []
    for q in data["questions"]:
        if "question" in q and "options" in q and len(q["options"]) >= 2:
            opts = q["options"][:4]
            while len(opts) < 4: opts.append("N/A")
            
            valid_questions.append({
                "question": str(q.get("question")),
                "options": [str(o) for o in opts],
                "correct_index": int(q.get("correct_index", 0)),
                "explanation": str(q.get("explanation", "No explanation provided.")),
                "visual_cue": str(q.get("visual_cue", "spooky halloween"))
            })
            
    if len(valid_questions) < n:
        fallback = _get_fallback_data("Padding", n - len(valid_questions), audience)["questions"]
        valid_questions.extend(fallback)
        
    return {"topic": data.get("topic", "Halloween Quiz"), "questions": valid_questions[:n]}

def _get_fallback_data(topic: str, n: int, audience: str) -> Dict[str, Any]:
    is_kids = "Kids" in audience
    if is_kids:
        pool = [
            {"question": "What vegetable was originally carved instead of pumpkins?", "options": ["Turnips", "Potatoes", "Carrots", "Watermelons"], "correct_index": 0, "explanation": "People in Ireland carved scary faces into turnips!", "visual_cue": "carved turnip lantern"},
            {"question": "Who is Casper?", "options": ["The Friendly Ghost", "A Mean Vampire", "A Green Witch", "A Skeleton"], "correct_index": 0, "explanation": "Casper is known for being friendly!", "visual_cue": "cute white ghost"},
            {"question": "What phrase do you say to get candy?", "options": ["Trick or Treat!", "Smell my feet!", "Happy Birthday!", "Please and Thank You"], "correct_index": 0, "explanation": "Trick or Treat is the magic phrase.", "visual_cue": "candy bucket"},
            {"question": "Which monster wraps himself in bandages?", "options": ["The Mummy", "Dracula", "Frankenstein", "The Wolfman"], "correct_index": 0, "explanation": "Mummies are wrapped in cloth bandages.", "visual_cue": "egyptian mummy"},
            {"question": "What animal is a witch's best friend?", "options": ["Black Cat", "Golden Retriever", "Parrot", "Hamster"], "correct_index": 0, "explanation": "Black cats are famous witch companions.", "visual_cue": "black cat moon"},
        ]
    else:
        pool = [
            {"question": "In 'Halloween' (1978), what is Michael Myers' weapon of choice?", "options": ["Kitchen Knife", "Chainsaw", "Machete", "Axe"], "correct_index": 0, "explanation": "He famously uses a chef's knife.", "visual_cue": "sharp knife shadow"},
            {"question": "Which hotel acts as the setting for 'The Shining'?", "options": ["The Overlook", "The Bates Motel", "The Continental", "The Plaza"], "correct_index": 0, "explanation": "The Overlook Hotel is the haunted site.", "visual_cue": "haunted hotel hallway"},
            {"question": "What is the name of the possessed girl in 'The Exorcist'?", "options": ["Regan MacNeil", "Carrie White", "Annabelle", "Samara"], "correct_index": 0, "explanation": "Regan was the girl possessed by Pazuzu.", "visual_cue": "scary bedroom"},
            {"question": "Which ancient festival is thought to be the origin of Halloween?", "options": ["Samhain", "Yule", "Beltane", "Lupercalia"], "correct_index": 0, "explanation": "Samhain was a Celtic harvest festival.", "visual_cue": "celtic bonfire"},
            {"question": "Who wrote the novel 'Frankenstein'?", "options": ["Mary Shelley", "Bram Stoker", "H.P. Lovecraft", "Edgar Allan Poe"], "correct_index": 0, "explanation": "Mary Shelley wrote it at age 18.", "visual_cue": "frankenstein laboratory"},
        ]
    results = []
    while len(results) < n:
        results.append(random.choice(pool))
    return {"topic": f"{topic} (Offline Mode)", "questions": results}

# ==========================================
# GAME STATE & LOGIC
# ==========================================

MAX_LIFELINES = {"50-50": 1, "Flip": 1, "Hint": 1}

def init_game_state(payload: Dict, audience: str):
    qs = payload["questions"]
    q_indices = list(range(len(qs)))
    random.shuffle(q_indices)
    return {
        "topic": payload["topic"],
        "questions": qs,
        "queue": q_indices,
        "current_idx": None,
        "score": 0,
        "asked": 0,
        "total": len(qs),
        "lifelines": {"50-50": 0, "Flip": 0, "Hint": 0},
        "eliminated": [],
        "game_over": False,
        "audience": audience,
        "streak": 0
    }

def get_current_question(state):
    if state["current_idx"] is None: return None
    return state["questions"][state["current_idx"]]

def next_turn(state):
    state["eliminated"] = []
    if not state["queue"]:
        state["game_over"] = True
        state["current_idx"] = None
        return state
    state["current_idx"] = state["queue"].pop(0)
    return state

# ==========================================
# UI CALLBACKS
# ==========================================

def start_game_ui(category, count, audience, difficulty):
    if not category or not audience:
        return (None, "⚠️ Please select settings first!", "", 
                gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
                "", gr.update(), gr.update(), gr.update())
        
    payload = generate_questions(category, count, audience, difficulty)
    state = init_game_state(payload, audience)
    state = next_turn(state)
    return update_ui(state, initial=True)

def submit_answer_ui(state, selected_idx):
    if state is None or state["game_over"]: return state, *get_empty_ui()
    
    q = get_current_question(state)
    real_options = q["options"]
    
    is_correct = (selected_idx == q["correct_index"])
    
    feedback = ""
    if is_correct:
        state["score"] += 1
        state["streak"] += 1
        msg = random.choice(["Brilliant!", "Spooktacular!", "You survived!", "Killer Move!", "Wicked!"])
        feedback = f"<div class='feedback correct-anim'>🎃 {msg}</div>"
    else:
        state["streak"] = 0
        corr_text = real_options[q["correct_index"]]
        feedback = f"<div class='feedback wrong-anim'>💀 FATAL ERROR! Answer: <b>{corr_text}</b></div>"
        
    if q.get("explanation"):
        feedback += f"<div class='explanation'>📝 {q['explanation']}</div>"

    state["asked"] += 1
    state = next_turn(state)
    
    if state["game_over"]:
        return render_game_over(state, feedback)
        
    return update_ui(state, feedback=feedback)

def use_lifeline_ui(state, lifeline):
    if state is None or state["game_over"]: return state, *get_empty_ui()
    
    q = get_current_question(state)
    msg = ""
    
    if state["lifelines"][lifeline] >= MAX_LIFELINES.get(lifeline, 1):
        msg = f"⚠️ {lifeline} Depleted!"
        return update_ui(state, feedback=f"<div class='feedback neutral'>{msg}</div>")

    state["lifelines"][lifeline] += 1
    
    if lifeline == "50-50":
        correct = q["correct_index"]
        wrong_indices = [i for i in range(4) if i != correct]
        to_remove = random.sample(wrong_indices, 2)
        state["eliminated"] = to_remove
        msg = "✂️ The spirits have silenced two lies..."
        
    elif lifeline == "Flip":
        if len(state["queue"]) == 0:
             msg = "⚠️ No destiny left to flip to!"
        else:
            state["queue"].append(state["current_idx"])
            state = next_turn(state)
            msg = "🔄 Fate has been twisted. New question!"

    elif lifeline == "Hint":
        cue = q.get("visual_cue", "Think spooky...")
        msg = f"💡 The spirits whisper: '{cue}'"
        return update_ui(state, feedback=f"<div class='feedback neutral'>{msg}</div>")

    return update_ui(state, feedback=f"<div class='feedback neutral'>{msg}</div>")

# ==========================================
# UI RENDERING HELPERS
# ==========================================

def update_ui(state, feedback="", initial=False):
    q = get_current_question(state)
    
    is_kids = "Kids" in state["audience"]
    theme_cls = "theme-kids" if is_kids else "theme-adults"
    
    pct = int((state["asked"] / state["total"]) * 100)
    
    if q:
        q_html = f"""
        <div class='q-container {theme_cls}'>
            <div class='scanline'></div>
            <div class='q-meta'>
                <span class='q-num'>Q {state['asked'] + 1}/{state['total']}</span>
                <span class='q-streak'>🔥 {state['streak']}</span>
            </div>
            <div class='q-text'>{q['question']}</div>
        </div>
        """
        
        updates = []
        for i in range(4):
            if i < len(q["options"]):
                text = q["options"][i]
                if i in state["eliminated"]:
                    updates.append(gr.update(value=f"❌ {text}", visible=True, interactive=False, variant="secondary"))
                else:
                    updates.append(gr.update(value=text, visible=True, interactive=True, variant="primary"))
            else:
                updates.append(gr.update(visible=False))
                
    else:
        q_html = "<div class='q-container'>Loading Nightmares...</div>"
        updates = [gr.update(visible=False)] * 4

    score_html = f"""
    <div class='stats-bar {theme_cls}'>
        <div class='stat-item'>🍬 Score: {state['score']}</div>
        <div class='progress-track'><div class='progress-fill' style='width:{pct}%'></div></div>
    </div>
    """

    return (
        state, 
        q_html,
        score_html,
        updates[0], updates[1], updates[2], updates[3],
        feedback,
        gr.update(interactive=state["lifelines"]["50-50"] < 1),
        gr.update(interactive=state["lifelines"]["Flip"] < 1),
        gr.update(interactive=state["lifelines"]["Hint"] < 1)
    )

def render_game_over(state, last_feedback):
    is_kids = "Kids" in state["audience"]
    final_score = state["score"]
    total = state["total"]
    
    if is_kids:
        grade = "Monster Master!" if final_score > total/2 else "Baby Bat!"
        color = "#00ff9d"
    else:
        grade = "Sole Survivor" if final_score > total/2 else "Fresh Meat"
        color = "#ff0000"
        
    html = f"""
    <div class='game-over-screen' style='border-color:{color}'>
        <div class='scanline'></div>
        {last_feedback}
        <h1 class='glitch-text'>GAME OVER</h1>
        <div class='final-score'>Score: {final_score} / {total}</div>
        <div class='final-rank'>Rank: {grade}</div>
    </div>
    """
    
    hidden = gr.update(visible=False)
    
    return (
        state,
        html,
        "",
        hidden, hidden, hidden, hidden,
        "",
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False)
    )

def get_empty_ui(msg=""):
    h = gr.update(visible=False)
    return "", "", h, h, h, h, msg, gr.update(), gr.update(), gr.update()

# ==========================================
# ULTRA PRO MAX CSS (CRT Edition)
# ==========================================

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Creepster&family=Nosifer&family=Rubik+Beastly&family=Montserrat:wght@400;700&family=Share+Tech+Mono&display=swap');

:root {
    --neon-green: #00ff9d;
    --neon-purple: #bd00ff;
    --blood-red: #ff0000;
    --ui-font: 'Montserrat', sans-serif;
    --mono-font: 'Share Tech Mono', monospace;
}

body { 
    background-image: url('/file=spooky.gif');
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    background-color: #000;
    color: #eee;
    margin: 0;
    font-family: var(--ui-font);
    overflow-x: hidden;
}

/* CRT OVERLAY EFFECT */
body::before {
    content: " ";
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background-image: url('/file=spooky.gif');
    z-index: 2;
    background-size: 100% 2px, 3px 100%;
    pointer-events: none;
}

/* Glassmorphic Container */
.gradio-container {
    max-width: 950px !important;
    margin: 30px auto !important;
    background: rgba(5, 5, 5, 0.85) !important;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    box-shadow: 0 0 80px rgba(0,0,0,1);
    padding: 0 !important;
    overflow: hidden;
    position: relative;
    z-index: 3;
}

/* Header */
.header-area {
    background: rgba(0,0,0,0.8);
    padding: 25px;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    position: relative;
}
.header-area h1 {
    font-family: 'Creepster', cursive;
    font-size: 4.5rem;
    color: #ff7a00;
    text-shadow: 4px 4px 0px #000, 0 0 20px #ff4d00;
    margin: 0;
    letter-spacing: 4px;
    animation: flicker 3s infinite;
}
.header-area p {
    color: #888;
    font-family: var(--mono-font);
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-top: 5px;
}

/* Panel Inputs */
.gradio-dropdown, .gradio-slider {
    background: transparent !important;
}

/* Question Container */
.q-container {
    padding: 40px;
    border-radius: 16px;
    margin-bottom: 30px;
    text-align: center;
    position: relative;
    min-height: 220px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    overflow: hidden;
}

.theme-adults.q-container {
    border: 1px solid #333;
    background: radial-gradient(circle, rgba(40,0,0,0.6) 0%, rgba(0,0,0,0.9) 100%);
    box-shadow: 0 0 30px rgba(255,0,0,0.1);
}

.theme-kids.q-container {
    border: 2px solid var(--neon-purple);
    background: radial-gradient(circle, rgba(20,0,50,0.8) 0%, rgba(10,0,20,0.9) 100%);
    box-shadow: 0 0 30px rgba(189, 0, 255, 0.3);
}

.q-text {
    font-size: 2.4rem;
    line-height: 1.2;
    margin-top: 10px;
    position: relative;
    z-index: 10;
}
.theme-adults .q-text { font-family: var(--adults-font); color: #e0e0e0; text-shadow: 0 0 10px red; }
.theme-kids .q-text { font-family: var(--kids-font); color: var(--neon-green); text-shadow: 0 0 10px var(--neon-green); }

/* Option Cards */
.opt-btn {
    height: 90px !important;
    font-size: 1.3rem !important;
    font-family: var(--mono-font) !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #ccc !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-align: left !important;
    padding-left: 24px !important;
    position: relative;
    overflow: hidden;
}
.opt-btn:hover {
    transform: scale(1.02);
    background: rgba(255,255,255,0.1) !important;
    border-color: var(--neon-green) !important;
    color: #fff !important;
    box-shadow: 0 0 15px var(--neon-green);
}

/* Start Button */
.primary-btn { 
    background: linear-gradient(90deg, #ff7a00, #ff0000) !important; 
    color: #000 !important; 
    border: none !important;
    font-weight: 900 !important;
    font-family: var(--mono-font) !important;
    text-transform: uppercase;
    font-size: 1.5rem !important;
    letter-spacing: 2px;
    transition: transform 0.2s;
}
.primary-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 0 30px #ff4d00;
}

/* Animations */
@keyframes flicker {
  0%, 18%, 22%, 25%, 53%, 57%, 100% { text-shadow: 4px 4px 0px #000, 0 0 20px #ff4d00; opacity: 1; }
  20%, 24%, 55% { text-shadow: none; opacity: 0.4; }
}

/* CRT Scanline Animation */
.scanline {
    width: 100%;
    height: 100px;
    z-index: 10;
    background: linear-gradient(0deg, rgba(0,0,0,0) 0%, rgba(255, 255, 255, 0.04) 50%, rgba(0,0,0,0) 100%);
    opacity: 0.1;
    position: absolute;
    bottom: 100%;
    animation: scanline 10s linear infinite;
    pointer-events: none;
}
@keyframes scanline {
    0% { bottom: 100%; }
    80% { bottom: 100%; }
    100% { bottom: -100%; }
}

.feedback {
    font-size: 1.6rem;
    text-align: center;
    padding: 20px;
    border-radius: 12px;
    margin: 20px 0;
    font-family: var(--mono-font);
    font-weight: bold;
    text-transform: uppercase;
}
.correct-anim { background: rgba(0, 255, 0, 0.1); border: 1px solid #0f0; color: #0f0; box-shadow: 0 0 20px #0f0; }
.wrong-anim { background: rgba(255, 0, 0, 0.1); border: 1px solid #f00; color: #f00; box-shadow: 0 0 20px #f00; }
"""

# ==========================================
# APP LAYOUT
# ==========================================

with gr.Blocks() as demo: 
    gr.HTML(f"<style>{CSS}</style>")
    
    game_state = gr.State()
    
    # HEADER
    with gr.Row(elem_classes="header-area"):
        gr.HTML("<h1>🎃 HALLOWEEN QUIZ 🎃</h1><p>Dare you enter the realm of shadows?</p>")
    
    # CONTROL PANEL
    with gr.Row(variant="panel", elem_classes="control-panel"):
        with gr.Column(scale=1):
            audience_sel = gr.Dropdown(AUDIENCE_MODES, value="Adults (True Horror)", label="Victim Profile")
            difficulty_sel = gr.Dropdown(DIFFICULTIES, value="Medium", label="Torment Level")
        with gr.Column(scale=1):
            category_sel = gr.Dropdown(CATEGORIES, value="🎬 Horror Movies", label="Forbidden Topic")
            count_slide = gr.Slider(5, 15, value=10, step=1, label="Questions to Survive")
        with gr.Column(scale=1, min_width=150):
            start_btn = gr.Button("🔮 SUMMON QUIZ", elem_classes="primary-btn", size="lg")

    # MAIN GAME STAGE
    with gr.Group(visible=True) as game_stage:
        stats_display = gr.HTML()
        question_display = gr.HTML()
        feedback_display = gr.HTML()
        
        with gr.Row():
            with gr.Column(scale=1):
                opt_btn_0 = gr.Button("Option A", visible=False, elem_classes="opt-btn")
                opt_btn_1 = gr.Button("Option B", visible=False, elem_classes="opt-btn")
            with gr.Column(scale=1):
                opt_btn_2 = gr.Button("Option C", visible=False, elem_classes="opt-btn")
                opt_btn_3 = gr.Button("Option D", visible=False, elem_classes="opt-btn")

        with gr.Row(elem_classes="lifeline-row"):
            btn_5050 = gr.Button("✂️ Sever 50/50", elem_classes="sec-btn")
            btn_flip = gr.Button("🔄 Alter Fate", elem_classes="sec-btn")
            btn_hint = gr.Button("🕯️ Consult Spirits", elem_classes="sec-btn")
            
    reset_btn = gr.Button("💀 RESURRECT (RESET)", elem_classes="sec-btn")

    # WIRING
    common_outputs = [game_state, question_display, stats_display, opt_btn_0, opt_btn_1, opt_btn_2, opt_btn_3, feedback_display, btn_5050, btn_flip, btn_hint]

    start_btn.click(
        fn=start_game_ui,
        inputs=[category_sel, count_slide, audience_sel, difficulty_sel],
        outputs=common_outputs
    )
    
    opt_btn_0.click(fn=submit_answer_ui, inputs=[game_state, gr.Number(0, visible=False)], outputs=common_outputs)
    opt_btn_1.click(fn=submit_answer_ui, inputs=[game_state, gr.Number(1, visible=False)], outputs=common_outputs)
    opt_btn_2.click(fn=submit_answer_ui, inputs=[game_state, gr.Number(2, visible=False)], outputs=common_outputs)
    opt_btn_3.click(fn=submit_answer_ui, inputs=[game_state, gr.Number(3, visible=False)], outputs=common_outputs)
    
    btn_5050.click(use_lifeline_ui, inputs=[game_state, gr.State("50-50")], outputs=common_outputs)
    btn_flip.click(use_lifeline_ui, inputs=[game_state, gr.State("Flip")], outputs=common_outputs)
    btn_hint.click(use_lifeline_ui, inputs=[game_state, gr.State("Hint")], outputs=common_outputs)
    
    reset_btn.click(
        lambda: (None, "", "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "", gr.update(), gr.update(), gr.update()),
        outputs=common_outputs
    )

if __name__ == "__main__":
    demo.launch(allowed_paths=["."])