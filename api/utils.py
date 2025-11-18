import re
import json
import os
import fitz                      # PyMuPDF for PDF text extraction
from openai import OpenAI        # OpenAI official SDK

# Initialize OpenAI client using .env API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ----------------------------------------------------
# EXTRACT TEXT FROM PDF (CLEAN + KEEP LINE BREAKS)
# ----------------------------------------------------
def extract_text_from_pdf_fileobj(file_obj):
    file_obj.seek(0)
    pdf_bytes = file_obj.read()

    # Load PDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""

    for page in doc:
        raw = page.get_text("text")

        # Clean lines but maintain readable spacing
        cleaned = "\n".join(
            re.sub(r"\s+", " ", line).strip()
            for line in raw.split("\n")
        )
        text += cleaned + "\n"

    return text


# ----------------------------------------------------
# AI RESUME PARSER (STRICT JSON OUTPUT)
# ----------------------------------------------------
def parse_resume_text_from_fileobj(file_obj):
    text = extract_text_from_pdf_fileobj(file_obj)

    prompt = f"""
    You are an expert resume parser.

    Extract the following fields STRICTLY in valid JSON only:

    {{
        "contact": {{
            "name": "",
            "phone": "",
            "email": "",
            "linkedin": "",
            "github": ""
        }},
        "summary": "",
        "education": [
            {{
                "institution": "",
                "duration": "",
                "degree": "",
                "location": "",
                "scores": []
            }}
        ],
        "projects": [
            {{
                "title": "",
                "year": "",
                "description": ""
            }}
        ],
        "experience": [
            {{
                "role": "",
                "company": "",
                "duration": "",
                "description": ""
            }}
        ],
        "skills": {{
            "programming": [],
            "frameworks_tools": [],
            "soft_skills": []
        }},
        "certifications": [],
        "achievements": []
    }}

    RULES:
    - Return ONLY pure JSON.
    - No markdown.
    - No backticks.
    - No explanations.
    
    Resume:
    {text}
    """

    # Ask OpenAI
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You only output pure valid JSON. No markdown."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1200,
        temperature=0.0
    )

    raw = response.choices[0].message.content.strip()

    # Remove ```json ... ``` if present
    if raw.startswith("```"):
        raw = re.sub(r"```(json)?", "", raw)
        raw = raw.replace("```", "").strip()

    # Try parse JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try repairing with one more model call
        repair_prompt = f"Fix this into valid JSON only:\n{raw}"

        repair = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Fix invalid JSON and output only JSON."},
                {"role": "user", "content": repair_prompt}
            ]
        )

        fixed = repair.choices[0].message.content.strip()

        # Remove any code fences again
        if fixed.startswith("```"):
            fixed = re.sub(r"```(json)?", "", fixed)
            fixed = fixed.replace("```", "").strip()

        try:
            return json.loads(fixed)
        except:
            return {
                "error": "OpenAI returned invalid JSON twice.",
                "raw": raw,
                "fixed": fixed
            }


# ----------------------------------------------------
# AI QUESTION GENERATOR
# ----------------------------------------------------
def generate_questions_from_resume(resume_data, job_role, difficulty, interview_type, page=1, page_size=10):
    start = (page - 1) * page_size + 1
    end = start + page_size - 1

    prompt = f"""
    You are an AI technical interviewer.

    Generate interview questions based on:

    Resume Data:
    {json.dumps(resume_data)[:4000]}

    Job Role: {job_role}
    Difficulty: {difficulty}
    Interview Type: {interview_type}

    Number questions from {start} to {end}.

    RULES:
    - Output ONLY the questions (with numbering).
    - No explanations.
    - Format:
      {start}. question
      {start+1}. question
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.7,
    )

    raw_output = response.choices[0].message.content.strip()

    # Extract questions like: 1. What is...?
    questions = []
    for line in raw_output.split("\n"):
        match = re.match(r"^\d+\.\s+(.*)$", line)
        if match:
            questions.append(match.group(1).strip())

    return questions
# ----------------------------------------------------
# PREMIUM FEATURES
# ----------------------------------------------------

def generate_resume_score(resume_text):
    prompt = f"""
    Score this resume and return STRICT JSON with:

    {{
      "score": 0,
      "ats_score": 0,
      "strengths": [],
      "weaknesses": [],
      "skills": []
    }}

    Resume:
    {resume_text}

    Rules:
    - Output only pure JSON
    - No markdown
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    # cleaning: remove ```json
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}



def generate_ats_report(resume_text):
    prompt = f"""
    You are an ATS analyzer.

    Return STRICT JSON:
    {{
      "ats_score": 0,
      "missing_keywords": [],
      "format_issues": [],
      "suggestions": []
    }}

    Resume:
    {resume_text}

    Rules:
    - Only JSON
    - No markdown
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}



def generate_jd_based_questions(resume_text, jd):
    prompt = f"""
    Generate interview questions based on this resume and JD.

    Return STRICT JSON ONLY:
    {{
      "questions": [
        {{
          "question": "",
          "skill": "",
          "ideal_answer": ""
        }}
      ]
    }}

    Resume:
    {resume_text}

    Job Description:
    {jd}

    Rules:
    - Exactly 10 questions
    - Only JSON
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}



def generate_cover_letter(resume_text, jd):
    prompt = f"""
    Write a professional cover letter based on the resume and JD.

    Return STRICT JSON:
    {{
      "cover_letter": ""
    }}

    Cover letter must be:
    - 3–4 short paragraphs
    - Tailored to JD
    - Clean and formal
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}



def generate_interview_bot_response(history, resume_text, user_message):
    prompt = f"""
    You are an AI technical interview coach.

    The candidate's latest answer is:
    "{user_message}"

    Your tasks:
    1. Evaluate the answer in 1–2 sentences (clarity, correctness, relevance).
    2. Give a numeric score from 0 to 10 for the answer.
    3. Ask the next interview question.
    4. Use resume data + history context.

    Return STRICT JSON ONLY in this EXACT structure:

    {{
        "evaluation": "",
        "score": 0,
        "next_question": ""
    }}

    --- RESUME DATA ---
    {resume_text}

    --- HISTORY ---
    {json.dumps(history)}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {
            "error": "invalid JSON",
            "raw": raw
        }
