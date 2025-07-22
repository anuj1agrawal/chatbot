import streamlit as st
import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Initialize Groq client
try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    st.error("Failed to initialize AI client. Please check your API key.")
    st.stop()

# --- AI Validation Function ---
def validate_text_input_with_ai(user_input, field_name):
    """Use AI to validate if the user input is a plausible value for a given field."""
    try:
        system_prompt = f"""You are a strict data validation assistant. A user has provided the following input for a '{field_name}' field: "{user_input}".
Is this a plausible, real-world '{field_name}'? The input should not be gibberish or nonsensical like 'asdfg' or 'gskgjk'.
Respond with only a single word: 'yes' or 'no'."""

        response = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}],
            model="llama3-8b-8192", max_tokens=5, temperature=0.0
        )
        decision = response.choices[0].message.content.strip().lower()
        return "yes" in decision
    except Exception:
        return len(user_input) > 2 # Fallback to simple check on error

# Constants & Data Steps
CONVERSATION_PHASES = {"GREETING": "greeting", "DATA_COLLECTION": "data_collection", "DATA_CONFIRMATION": "data_confirmation", "TECHNICAL_QUESTIONS": "technical_questions", "CONCLUSION": "conclusion", "ENDED": "ended"}
EXIT_KEYWORDS = ["bye", "goodbye", "exit", "quit", "end", "stop", "finish", "done", "thanks", "thank you"]
DATA_STEPS = {
    1: {"field": "name", "prompt": "What's your full name?", "validation": lambda x: len(x.strip().split()) >= 2 and all(part.replace('-', '').replace("'", "").isalpha() for part in x.strip().split()), "error_msg": "Please provide your complete full name (first and last name)."},
    2: {"field": "email", "prompt": "Could you please share your email address?", "validation": lambda x: re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', x.strip()), "error_msg": "Please provide a valid email address."},
    3: {"field": "phone", "prompt": "What's your phone number?", "validation": lambda x: len(re.sub(r'[^0-9]', '', x)) >= 10, "error_msg": "Please provide a valid phone number with at least 10 digits."},
    4: {"field": "experience", "prompt": "How many years of professional experience do you have?", "validation": lambda x: re.match(r'^\d+(\.\d+)?$', x.strip()) and 0 <= float(x.strip()) <= 50, "error_msg": "Please provide your experience in years (e.g., 2, 3.5, 0 for fresher)."},
    5: {"field": "position", "prompt": "What position are you interested in applying for?", "validation": lambda x: validate_text_input_with_ai(x, "Job Position"), "error_msg": "Please provide a valid and clear job position."},
    6: {"field": "location", "prompt": "What's your preferred work location? (or are you open to remote work?)", "validation": lambda x: validate_text_input_with_ai(x, "Work Location"), "error_msg": "Please provide a valid location or specify 'remote'."},
    7: {"field": "tech_stack", "prompt": "What programming languages, frameworks, and technologies are you proficient in?", "validation": lambda x: validate_text_input_with_ai(x, "Technology Stack"), "error_msg": "Please list the technical skills you are proficient in."}
}

# --- AI Answer Evaluation Function ---
def evaluate_technical_answer(question, answer, candidate_name, candidate_experience_level, tech_stack):
    """Uses AI to evaluate a user's answer, provide feedback, and return the correct explanation."""
    try:
        system_prompt = f"""You are an expert technical interviewer. Your goal is to be encouraging, conversational, and educational. You will receive a technical question and a user's answer from {candidate_name}, who is a {candidate_experience_level} candidate in {tech_stack}.
**Question:** "{question}"
**{candidate_name}'s Answer:** "{answer}"
Your task is to perform the following steps and return a single, valid JSON object:
1.  Analyze {candidate_name}'s answer. Determine if it's correct, partially correct, incorrect, or if they indicated they don't know (e.g., "skip", "idk", "I don't know", "next").
2.  Write a short, friendly, and encouraging sentence of feedback for {candidate_name}. This should feel like a real person talking directly to them, using their name.
    - If {candidate_name} knew the answer, acknowledge their knowledge (e.g., "That's a great explanation, {candidate_name}!").
    - If {candidate_name} was partially correct, praise their effort (e.g., "You're on the right track, {candidate_name}!").
    - If {candidate_name} was incorrect (but attempted an answer), be encouraging about the learning opportunity (e.g., "Thanks for trying, {candidate_name}!").
    - If {candidate_name} said "skip" or "don't know", acknowledge their choice politely and encouragingly, varying the phrasing (e.g., "No worries at all, {candidate_name}.", "That's okay, {candidate_name}!", "{candidate_name}! No problem if you'd like to skip this one.").
3.  Write a clear, concise, and comprehensive explanation for the **correct answer** to the original question. Start this explanation with a heading like "Here's a breakdown:".
**Return a valid JSON object with the following structure, and nothing else:**
{{
  "feedback": "Your friendly feedback sentence here, using the candidate's name.",
  "explanation": "Your comprehensive correct answer here."
}}"""
        response = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}], model="llama3-8b-8192",
            max_tokens=500, temperature=0.7, response_format={"type": "json_object"}, 
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception:
        return {"feedback": f"Great, thank you for your response, {candidate_name or 'Anuj'}!", "explanation": "Let's move on to the next question."}

# --- Helper Functions (Session State, Prompts, etc.) ---
def initialize_session_state():
    if "candidate_data" not in st.session_state: st.session_state.candidate_data = {"name": "", "email": "", "phone": "", "experience": "", "position": "", "location": "", "tech_stack": ""}
    if "current_step" not in st.session_state: st.session_state.current_step = 1
    if "conversation_phase" not in st.session_state: st.session_state.conversation_phase = CONVERSATION_PHASES["GREETING"]
    if "technical_questions" not in st.session_state: st.session_state.technical_questions = []
    if "technical_answers" not in st.session_state: st.session_state.technical_answers = []
    if "current_question_index" not in st.session_state: st.session_state.current_question_index = 0
    if "retry_count" not in st.session_state: st.session_state.retry_count = 0
    if "messages" not in st.session_state: st.session_state.messages = []

def get_system_prompt(phase):
    base_prompt = "You are Maya, a friendly, warm, and professional hiring assistant for TalentScout. You are encouraging, empathetic, and make candidates feel comfortable and valued. Always address the candidate by their name if you know it."
    if phase == CONVERSATION_PHASES["GREETING"]:
        return base_prompt + " Greet the candidate warmly, introduce yourself, explain the process (info gathering, technical questions, next steps), and ask for their full name to begin in a very friendly manner."
    elif phase == CONVERSATION_PHASES["CONCLUSION"]:
        return base_prompt + " Thank the candidate warmly for their time. Let them know they did great, their info is recorded, the team will review it, and they'll hear back in 2-3 business days. End on an encouraging and positive note, wishing them luck."
    return base_prompt

def get_ai_response(messages, system_prompt):
    try:
        response = client.chat.completions.create(messages=[{"role": "system", "content": system_prompt}, *messages], model="llama3-8b-8192", max_tokens=400, temperature=0.8)
        return response.choices[0].message.content
    except Exception:
        return "I'm experiencing some technical difficulties right now. Could we try that again? 😊"

def generate_technical_questions(tech_stack, experience):
    fallback_questions = ["Tell me about a challenging project you've worked on.", "How do you approach debugging?", "What coding best practices do you follow?", "How do you stay updated with new technologies?", "Describe your experience with version control."]
    try:
        experience_level = "entry-level" if float(experience) < 2 else "mid-level" if float(experience) < 5 else "senior-level"
        system_prompt = f"Generate exactly 5 technical questions for a {experience_level} candidate with expertise in: {tech_stack}. Focus on conceptual understanding, design patterns, best practices, and problem-solving. Avoid questions that would require generating multi-line code snippets as an answer. Format as a numbered list."
        response = client.chat.completions.create(messages=[{"role": "system", "content": system_prompt}], model="llama3-8b-8192", max_tokens=600, temperature=0.7)
        questions = [line.split('.', 1)[1].strip() for line in response.choices[0].message.content.split('\n') if line and re.match(r'^\d\.', line.strip())]
        return questions[:5] if len(questions) == 5 else fallback_questions
    except Exception:
        return fallback_questions

# --- Streamlit App UI and Main Logic ---
initialize_session_state()

st.set_page_config(page_title="TalentScout - Maya AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Maya - Your TalentScout Assistant")
st.markdown("*Making your tech career journey smooth and friendly* ✨")

# --- SIDEBAR CODE BLOCK (RESTORED) ---
with st.sidebar:
    st.header("📊 Your Progress")
    
    # Progress bar logic
    total_steps = len(DATA_STEPS)
    progress = 0
    phase = st.session_state.conversation_phase
    if phase == CONVERSATION_PHASES["DATA_COLLECTION"]:
        progress = (st.session_state.current_step - 1) / total_steps * 0.7
    elif phase == CONVERSATION_PHASES["DATA_CONFIRMATION"]:
        progress = 0.75
    elif phase == CONVERSATION_PHASES["TECHNICAL_QUESTIONS"]:
        q_count = len(st.session_state.technical_questions)
        progress = 0.8 + (st.session_state.current_question_index / q_count * 0.15) if q_count > 0 else 0.8
    elif phase in [CONVERSATION_PHASES["CONCLUSION"], CONVERSATION_PHASES["ENDED"]]:
        progress = 1.0
    st.progress(progress)
    
    phase_display = phase.replace('_', ' ').title()
    st.write(f"**Current Phase:** {phase_display}")
    
    # Display collected information
    st.subheader("📝 Your Information")
    info_collected = any(st.session_state.candidate_data.values())
    if info_collected:
        for key, value in st.session_state.candidate_data.items():
            if value:
                display_value = value
                # Partially hide sensitive information
                if key in ["email", "phone"] and len(value) > 5:
                    if key == "email":
                        if '@' in value:
                            name_part, domain_part = value.split('@')
                            display_value = name_part[:2] + "*" * (len(name_part)-2) + "@" + domain_part
                    else:
                        clean_phone = re.sub(r'[^0-9]', '', value)
                        if len(clean_phone) > 6:
                            display_value = clean_phone[:3] + "*" * (len(clean_phone)-6) + clean_phone[-3:]
                st.write(f"**{key.replace('_', ' ').title()}:** {display_value}")
    else:
        st.write("*Information will appear here as we chat* 📝")
    
    # Technical questions progress
    if st.session_state.technical_questions and phase == CONVERSATION_PHASES["TECHNICAL_QUESTIONS"]:
        st.subheader("🧠 Technical Assessment")
        st.write(f"**Progress:** {st.session_state.current_question_index}/{len(st.session_state.technical_questions)} questions")
        for i in range(len(st.session_state.technical_questions)):
            if i < st.session_state.current_question_index:
                st.write(f"**Question {i+1}:** ✅ Completed")
            elif i == st.session_state.current_question_index:
                st.write(f"**Question {i+1}:** 🔄 Current")
            else:
                st.write(f"**Question {i+1}:** ⏳ Pending")

# Main chat interface
st.subheader("💬 Chat with Maya")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Main chat input and logic
if st.session_state.conversation_phase != CONVERSATION_PHASES["ENDED"]:
    if prompt := st.chat_input("Type your message here... 💭"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        phase = st.session_state.conversation_phase
        bot_response = ""
        candidate_name = st.session_state.candidate_data.get("name", "there") 
        candidate_first_name = candidate_name.split(' ')[0] if candidate_name else "there"


        if any(keyword in prompt.lower() for keyword in EXIT_KEYWORDS):
            bot_response = "Thank you for your time! Best of luck, " + candidate_first_name + "! 👋"
            st.session_state.conversation_phase = CONVERSATION_PHASES["ENDED"]
        
        elif phase == CONVERSATION_PHASES["GREETING"]:
            system_prompt = get_system_prompt(phase)
            bot_response = get_ai_response(st.session_state.messages, system_prompt)
            st.session_state.conversation_phase = CONVERSATION_PHASES["DATA_COLLECTION"]

        elif phase == CONVERSATION_PHASES["DATA_COLLECTION"]:
            is_valid = DATA_STEPS[st.session_state.current_step]["validation"](prompt)
            if is_valid:
                st.session_state.candidate_data[DATA_STEPS[st.session_state.current_step]["field"]] = prompt
                
                # Custom personalized responses for data collection steps
                if st.session_state.current_step == 1: # After name
                    bot_response = f"Hi {candidate_first_name}! Thanks for sharing your full name. Next, {DATA_STEPS[2]['prompt']}"
                elif st.session_state.current_step == 2: # After email
                    bot_response = f"Got it, {candidate_first_name}! Your email address is {st.session_state.candidate_data['email']}. Next, {DATA_STEPS[3]['prompt']}"
                elif st.session_state.current_step == 3: # After phone
                    bot_response = f"{candidate_first_name}! Your phone number is {st.session_state.candidate_data['phone']}. Next, {DATA_STEPS[4]['prompt']}"
                elif st.session_state.current_step == 4: # After experience
                    experience_val = float(st.session_state.candidate_data['experience'])
                    experience_msg = ""
                    if experience_val == 0:
                        experience_msg = f"With {int(experience_val)} years of experience, you're just starting out! "
                    elif experience_val < 2:
                        experience_msg = f"With {experience_val} years of experience, that's a great start! "
                    elif experience_val < 5:
                        experience_msg = f"With {experience_val} years of experience, you're building a solid foundation! "
                    else:
                        experience_msg = f"With {experience_val} years of experience, you have significant expertise! "
                    bot_response = f"{candidate_first_name}! {experience_msg}Next, {DATA_STEPS[5]['prompt']}"
                elif st.session_state.current_step == 5: # After position
                    bot_response = f"{candidate_first_name}! You're interested in a {st.session_state.candidate_data['position']} position. That's great! Next, {DATA_STEPS[6]['prompt']}"
                elif st.session_state.current_step == 6: # After location
                    bot_response = f"{candidate_first_name}! You're looking for a {st.session_state.candidate_data['position']} opportunity in {st.session_state.candidate_data['location']}. Got it! Next, {DATA_STEPS[7]['prompt']}"
                
                st.session_state.current_step += 1 

                if st.session_state.current_step > len(DATA_STEPS):
                    st.session_state.conversation_phase = CONVERSATION_PHASES["DATA_CONFIRMATION"]
                    data_summary = "\n".join([f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in st.session_state.candidate_data.items() if v])
                    bot_response = f"Alright, {candidate_first_name}! We've gathered all your information. Does this look correct?\n\n{data_summary}\n\nPlease type 'yes' to confirm or tell me what to change."
            else:
                bot_response = f"I need a bit more clarity, {candidate_first_name}. {DATA_STEPS[st.session_state.current_step]['error_msg']} Could you please try again? 😊"
        
        elif phase == CONVERSATION_PHASES["DATA_CONFIRMATION"]:
            if any(word in prompt.lower() for word in ["yes", "correct", "confirm", "proceed"]):
                st.session_state.technical_questions = generate_technical_questions(st.session_state.candidate_data["tech_stack"], st.session_state.candidate_data["experience"])
                st.session_state.technical_answers = [""] * len(st.session_state.technical_questions)
                st.session_state.conversation_phase = CONVERSATION_PHASES["TECHNICAL_QUESTIONS"]
                
                tech_stack_display = st.session_state.candidate_data['tech_stack']
                position_display = st.session_state.candidate_data['position']

                bot_response = (
                    f"{candidate_first_name}! You're familiar with {tech_stack_display}, which is a great combination for {position_display}. "
                    "Next, I'll ask you some technical questions to assess your skills. Please answer them one by one. "
                    f"Here's your first question:\n\n**Question 1:** {st.session_state.technical_questions[0]}"
                )
            else:
                bot_response = f"No problem, {candidate_first_name}! What information would you like to change?"

        elif phase == CONVERSATION_PHASES["TECHNICAL_QUESTIONS"]:
            current_question = st.session_state.technical_questions[st.session_state.current_question_index]
            experience_level_for_eval = "entry-level" if float(st.session_state.candidate_data["experience"]) < 2 else "mid-level" if float(st.session_state.candidate_data["experience"]) < 5 else "senior-level"
            
            evaluation = evaluate_technical_answer(
                current_question,
                prompt,
                candidate_first_name, # Pass the candidate's first name
                experience_level_for_eval,
                st.session_state.candidate_data["tech_stack"]
            )
            feedback = evaluation.get("feedback", f"Thanks for your answer, {candidate_first_name}!")
            explanation = evaluation.get("explanation", "Let's proceed.")
            
            bot_response = f"{feedback}\n\n{explanation}"
            st.session_state.technical_answers[st.session_state.current_question_index] = prompt
            st.session_state.current_question_index += 1
            
            if st.session_state.current_question_index < len(st.session_state.technical_questions):
                next_question = st.session_state.technical_questions[st.session_state.current_question_index]
                bot_response += f"\n\n---\n\nReady for the next one, {candidate_first_name}?\n\n**Question {st.session_state.current_question_index + 1}:** {next_question}"
            else:
                st.session_state.conversation_phase = CONVERSATION_PHASES["CONCLUSION"]
                bot_response += "\n\n---\n\n🎉 **Fantastic, " + candidate_first_name + "!** You've completed all the technical questions! You did really well, and I appreciate you talking through them with me. Let me give you information about the next steps. 📋"

        elif phase == CONVERSATION_PHASES["CONCLUSION"]:
            system_prompt = get_system_prompt(phase)
            bot_response = get_ai_response(st.session_state.messages, system_prompt)
            st.session_state.conversation_phase = CONVERSATION_PHASES["ENDED"]

        if bot_response:
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            st.rerun()

else:
    st.success("🎉 **Interview Completed Successfully!** Thank you for using TalentScout!")
    st.balloons()
    if st.button("🔄 Start New Interview Session", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- FOOTER CODE BLOCK (RESTORED) ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <strong>TalentScout Hiring Assistant</strong> | Powered by AI | Built with ❤️ using Streamlit<br>
    <small>Your friendly AI assistant Maya is here to make hiring smooth and personal ✨</small>
</div>
""", unsafe_allow_html=True)