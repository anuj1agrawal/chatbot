# TalentScout Hiring Assistant Chatbot

## Project Overview
The TalentScout Hiring Assistant is an AI-powered chatbot designed to streamline the initial screening process for technology placements. Built for the fictional recruitment agency "TalentScout," the chatbot, named Maya, engages candidates in a friendly and professional manner to collect essential information, assess technical proficiency through tailored questions, and ensure a seamless user experience. The project leverages Streamlit for the user interface, Groq's `llama3-8b-8192` model for natural language processing, and custom prompt engineering to maintain coherent and context-aware interactions.

Key features include:
- **Greeting and Introduction**: Warmly welcomes candidates and explains the process.
- **Information Gathering**: Collects candidate details (name, email, phone, experience, position, location, tech stack) with robust validation.
- **Technical Question Generation**: Dynamically generates 3-5 technical questions based on the candidate’s declared tech stack and experience level.
- **Context Handling**: Maintains conversation flow and handles unexpected inputs gracefully.
- **Data Privacy**: Masks sensitive information (email, phone) in the UI to align with GDPR best practices.
- **Progress Tracking**: Displays real-time progress and collected information in a sidebar.

## Installation Instructions
To set up and run the TalentScout Hiring Assistant locally, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/AnujAgrawal/talentscout-hiring-assistant.git
   cd talentscout-hiring-assistant
   ```

2. **Set Up a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   Ensure Python 3.8+ is installed, then install the required libraries:
   ```bash
   pip install streamlit groq python-dotenv
   ```

4. **Configure Environment Variables**:
   - Create a `.env` file in the project root.
   - Add your Groq API key:
     ```plaintext
     GROQ_API_KEY=your_groq_api_key_here
     ```
   - Obtain a Groq API key from [GroqCloud](https://console.groq.com) if you don’t have one.

5. **Run the Application**:
   ```bash
   streamlit run app.py
   ```
   The app will open in your default browser at `http://localhost:8501`.

## Usage Guide
1. **Start the Chatbot**:
   - Open the application in your browser.
   - Maya, the AI assistant, greets you and begins the interview process.

2. **Provide Information**:
   - Respond to prompts for your full name, email, phone number, years of experience, desired position, location, and tech stack.
   - The chatbot validates inputs to ensure accuracy (e.g., valid email format, plausible tech stack).

3. **Confirm Details**:
   - Review the collected information and confirm or request changes.

4. **Answer Technical Questions**:
   - Based on your tech stack (e.g., Python, Django), Maya generates 3-5 tailored technical questions.
   - Provide answers, and receive friendly feedback with explanations for each question.

5. **Complete the Interview**:
   - After answering all questions, Maya concludes the session, informing you of next steps.
   - Use keywords like "bye" or "exit" to end the conversation early.

6. **Start a New Session**:
   - Click the "Start New Interview Session" button to reset and begin anew.

## Technical Details
- **Programming Language**: Python 3.8+
- **Libraries**:
  - `streamlit`: For the interactive web interface.
  - `groq`: For accessing the `llama3-8b-8192` model via Groq’s API.
  - `python-dotenv`: For secure API key management.
  - `re` and `json`: For input validation and response parsing.
- **Model**: Groq’s `llama3-8b-8192` for natural language understanding, question generation, and answer evaluation.
- **Architecture**:
  - **Session State Management**: Uses Streamlit’s `session_state` to track conversation phases, candidate data, and technical questions.
  - **Conversation Flow**: Structured into phases (greeting, data collection, data confirmation, technical questions, conclusion) defined in `CONVERSATION_PHASES`.
  - **Validation**: Combines regex-based checks (e.g., email, phone) with AI-driven validation for fields like tech stack and location.
  - **UI Components**: A main chat interface and a sidebar displaying progress, collected data, and technical question status.
- **Data Privacy**:
  - Sensitive information (email, phone) is partially masked in the sidebar display (e.g., `jo**@example.com`, `123****456`).
  - No persistent data storage is implemented, ensuring compliance with GDPR principles for this prototype.

## Prompt Design
Prompts were crafted to achieve precise and context-aware interactions with the LLM:

1. **Greeting Prompt**:
   - Instructs Maya to be warm, empathetic, and professional, introducing the process clearly.
   - Example: "You are Maya, a friendly hiring assistant for TalentScout. Greet the candidate warmly, introduce yourself, explain the process..."

2. **Information Gathering**:
   - Prompts are embedded in `DATA_STEPS`, each tailored to collect specific fields with clear instructions.
   - Validation prompts use the LLM to check plausibility (e.g., "Is this a plausible 'Job Position'?").

3. **Technical Question Generation**:
   - Generates 5 questions based on tech stack and experience level (entry-level, mid-level, senior-level).
   - Example: "Generate exactly 5 technical questions for a mid-level candidate with expertise in: Python, Django..."
   - Focuses on conceptual understanding and avoids code-heavy questions to suit chat-based responses.

4. **Answer Evaluation**:
   - Uses a structured JSON prompt to evaluate answers, provide encouraging feedback, and explain correct answers.
   - Example: "Analyze {candidate_name}'s answer... Return a JSON object with feedback and explanation."

5. **Fallback Mechanism**:
   - Handles unexpected inputs by prompting the LLM to respond politely and redirect to the current phase.
   - Example: "I need a bit more clarity, {candidate_name}. Could you please try again?"

## Challenges & Solutions
1. **Challenge**: Ensuring context retention across conversation phases.
   - **Solution**: Used Streamlit’s `session_state` to persist candidate data, phase, and question index, ensuring seamless transitions.

2. **Challenge**: Generating relevant technical questions for diverse tech stacks.
   - **Solution**: Crafted a prompt that specifies experience level and tech stack, with a fallback to generic questions if the LLM fails.

3. **Challenge**: Validating user inputs without over-relying on regex.
   - **Solution**: Combined regex for structured fields (email, phone) with AI-driven validation for subjective fields (tech stack, position).

4. **Challenge**: Handling sensitive data securely in a prototype.
   - **Solution**: Avoided persistent storage and masked sensitive fields in the UI to simulate GDPR compliance.

5. **Challenge**: Ensuring a responsive and user-friendly interface.
   - **Solution**: Leveraged Streamlit’s built-in components (chat input, sidebar, progress bar) and added custom styling for a polished look.

## Deployment (Optional)
For bonus points, the application can be deployed on Hugging Face Spaces:
1. Create a Hugging Face Space and push the repository.
2. Set the `GROQ_API_KEY` as a secret in the Space settings.
3. Ensure `requirements.txt` includes all dependencies:
   ```plaintext
   streamlit
   groq
   python-dotenv
   ```
4. Access the live demo at `https://AnujAgrawal-talentscout-hiring-assistant.hf.space` (replace with your Space URL).

## Demo
A video walkthrough demonstrating the chatbot’s features is available via https://drive.google.com/drive/folders/1JgwYzsQWr8EYwzwy_MKBhGEmcoaCppqU?usp=sharing . The demo covers:
- Greeting and information collection.
- Technical question interaction with feedback.
- Progress tracking and UI features.
- Conversation conclusion and reset functionality.