import json
import os
import base64
import re
from openai import OpenAI
from PyPDF2 import PdfReader

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ----------------------------------------------------------------------
# SAFE PDF TEXT EXTRACTION (Render-friendly)
# ----------------------------------------------------------------------
def extract_pdf_text(file_obj):
    """
    Extract text from PDF using PyPDF2.
    Never crashes — returns empty string if unreadable.
    """
    try:
        file_obj.seek(0)
        reader = PdfReader(file_obj)
        text = ""

        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except:
                continue

        return text or ""
    except:
        return ""


# ----------------------------------------------------------------------
# If PDF has no extractable text → fallback by sending PDF to OpenAI
# ----------------------------------------------------------------------
def openai_extract_from_pdf_bytes(file_obj):
    """
    Sends raw PDF bytes to OpenAI for extraction.
    Works for scanned or complex PDFs.
    """
    file_obj.seek(0)
    pdf_bytes = file_obj.read()
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    prompt = """
    You are an AI resume parser. Extract the full readable text from this PDF.
    Return ONLY plain text. No JSON. No explanations.
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_file",
                        "mime_type": "application/pdf",
                        "data": pdf_b64,
                    },
                ],
            }
        ],
        max_tokens=2000,
    )

    return response.choices[0].message.content.strip()


# ----------------------------------------------------------------------
# MAIN RESUME PARSER (ALWAYS RETURNS JSON)
# ----------------------------------------------------------------------
def parse_resume_text_from_fileobj(file_obj):
    # Try safe PyPDF2 extraction
    text = extract_pdf_text(file_obj)

    # If nothing extracted → fallback to OpenAI PDF parsing
    if len(text.strip()) < 40:
        text = openai_extract_from_pdf_bytes(file_obj)

    # Now send extracted text to OpenAI to structure JSON
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
        "education": [],
        "projects": [],
        "experience": [],
        "skills": {{
            "programming": [],
            "frameworks_tools": [],
            "soft_skills": []
        }},
        "certifications": [],
        "achievements": []
    }}

    RULES:
    - Return ONLY pure JSON
    - No markdown
    - No comments
    - No backticks

    Resume:
    {text}
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.0,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": "You always return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # clean ```json fences if any
    raw = raw.replace("```json", "").replace("```", "").strip()

    # Try parsing JSON
    try:
        return json.loads(raw)
    except:
        # Final attempt → ask model to fix
        fix_prompt = f"Fix this into valid JSON only:\n{raw}"
        fix = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": fix_prompt}],
        )
        fixed = fix.choices[0].message.content.strip()
        fixed = fixed.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(fixed)
        except:
            return {
                "error": "Invalid JSON returned",
                "raw": raw,
                "fixed": fixed,
            }


# ----------------------------------------------------------------------
# QUESTION GENERATOR
# ----------------------------------------------------------------------
def generate_questions_from_resume(resume_data, job_role, difficulty, interview_type):
    prompt = f"""
    Generate interview questions only.

    Resume:
    {json.dumps(resume_data)[:3500]}

    Job Role: {job_role}
    Difficulty: {difficulty}
    Type: {interview_type}

    Return numbered questions ONLY.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )

    text = response.choices[0].message.content.strip()

    questions = []
    for line in text.split("\n"):
        m = re.match(r"^\d+\.\s+(.*)$", line)
        if m:
            questions.append(m.group(1).strip())

    return questions


# ----------------------------------------------------------------------
# PREMIUM FEATURES — Resume Score
# ----------------------------------------------------------------------
def generate_resume_score(resume_text):
    prompt = f"""
    Score this resume. Return STRICT JSON:

    {{
      "score": 0,
      "ats_score": 0,
      "strengths": [],
      "weaknesses": [],
      "skills": []
    }}

    Resume text:
    {resume_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}


# ----------------------------------------------------------------------
# ATS CHECK
# ----------------------------------------------------------------------
def generate_ats_report(resume_text):
    prompt = f"""
    Generate ATS report. STRICT JSON:

    {{
      "ats_score": 0,
      "missing_keywords": [],
      "format_issues": [],
      "suggestions": []
    }}

    Resume:
    {resume_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}


# ----------------------------------------------------------------------
# JD Based Questions
# ----------------------------------------------------------------------
def generate_jd_based_questions(resume_text, jd):
    prompt = f"""
    Generate 10 JD-based questions.

    STRICT JSON:
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

    JD:
    {jd}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}


# ----------------------------------------------------------------------
# Cover Letter Generator
# ----------------------------------------------------------------------
def generate_cover_letter(resume_text, jd):
    prompt = f"""
    Generate a professional cover letter.

    STRICT JSON:
    {{
        "cover_letter": ""
    }}

    Resume:
    {resume_text}

    Job Description:
    {jd}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return {"error": "invalid JSON", "raw": raw}


# ----------------------------------------------------------------------
# Interview Chat Bot
# ----------------------------------------------------------------------
