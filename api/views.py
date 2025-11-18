# api/views.py
import json
import logging
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.models import User

from .serializers import (
    RegisterSerializer,
    ResumeSerializer,
    InterviewSetupSerializer,
    ResumeAnalysisSerializer,
)
from .models import (
    Resume,
    InterviewSetup,
    ResumeAnalysis,
    InterviewSession,
    GeneratedCoverLetter,
)

from .utils import (
    parse_resume_text_from_fileobj,
    generate_questions_from_resume,
    generate_resume_score,
    generate_ats_report,
    generate_jd_based_questions,
    generate_cover_letter,
    
)

logger = logging.getLogger(__name__)


# -------------------------
# Helper: safe JSON response
# -------------------------
def _error(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": msg}, status=code)


# =====================================================
# USER REGISTER (Public)
# =====================================================
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
            except Exception as e:
                logger.exception("Register: Exception while saving user")
                return _error("Failed to create user", status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)

        logger.warning("REGISTER ERROR: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# RESUME UPLOAD + AI PARSING
# =====================================================
class ResumeUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    # Limit file sizes (bytes). Adjust if needed (5 MB default)
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024

    def post(self, request):
        file = request.FILES.get("resume")
        if not file:
            return _error("No resume uploaded. Send form field 'resume'.", status.HTTP_400_BAD_REQUEST)

        # Basic validations
        content_type = file.content_type or ""
        if "pdf" not in content_type and content_type not in ("application/octet-stream",):
            # allow fallback for some clients that send octet-stream but file name .pdf
            return _error("Only PDF resumes are supported. Please upload a PDF file.", status.HTTP_400_BAD_REQUEST)

        if file.size > self.MAX_UPLOAD_SIZE:
            return _error(f"File too large. Max allowed {self.MAX_UPLOAD_SIZE // (1024*1024)} MB.", status.HTTP_400_BAD_REQUEST)

        # Save + parse inside a transaction to avoid partial failures
        try:
            with transaction.atomic():
                resume = Resume.objects.create(user=request.user, file=file)
        except Exception as e:
            logger.exception("ResumeUpload: Failed to save file to model")
            return _error("Failed to save uploaded resume.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Parse the resume using utils.parse_resume_text_from_fileobj
        try:
            with resume.file.open("rb") as f:
                parsed = parse_resume_text_from_fileobj(f)
        except Exception as e:
            logger.exception("ResumeUpload: Exception during parsing")
            # keep the saved resume but return a clear error message
            resume.extracted_data = {"error": "Parsing failed on server"}
            resume.save(update_fields=["extracted_data"])
            return _error("Failed to parse resume. See server logs for details.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save parsed data and return
        try:
            resume.extracted_data = parsed
            resume.save(update_fields=["extracted_data"])
        except Exception as e:
            logger.exception("ResumeUpload: Failed to save extracted_data")
            return _error("Parsed resume but failed to persist data.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Resume uploaded and parsed successfully", "data": parsed}, status=status.HTTP_200_OK)


# =====================================================
# INTERVIEW SETUP + REGULAR QUESTIONS
# =====================================================
class InterviewSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = InterviewSetupSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("InterviewSetup validation failed: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            setup = serializer.save(user=request.user)
        except Exception as e:
            logger.exception("InterviewSetup: Failed to save setup")
            return _error("Failed to save interview setup.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return _error("Upload resume first", status.HTTP_400_BAD_REQUEST)

        try:
            questions = generate_questions_from_resume(
                resume.extracted_data,
                setup.job_role,
                setup.difficulty,
                setup.interview_type,
            )
        except Exception as e:
            logger.exception("InterviewSetup: generate_questions_from_resume failed")
            return _error("Failed to generate questions.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Interview setup complete", "questions": questions}, status=status.HTTP_200_OK)


# =====================================================
# PREMIUM FEATURE 1 — RESUME SCORING
# =====================================================
class ResumeScoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return _error("Upload a resume first", status.HTTP_400_BAD_REQUEST)

        resume_text = json.dumps(resume.extracted_data)
        try:
            score_json = generate_resume_score(resume_text)
        except Exception as e:
            logger.exception("ResumeScore: generate_resume_score failed")
            return _error("Failed to score resume.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            analysis, _ = ResumeAnalysis.objects.get_or_create(resume=resume)
            analysis.score = score_json.get("score")
            analysis.ats_score = score_json.get("ats_score")
            analysis.strengths = score_json.get("strengths", [])
            analysis.weaknesses = score_json.get("weaknesses", [])
            analysis.skills = score_json.get("skills", [])
            analysis.save()
        except Exception as e:
            logger.exception("ResumeScore: Failed to save analysis")
            return _error("Scored resume but failed to persist analysis.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Resume scored", "analysis": ResumeAnalysisSerializer(analysis).data}, status=status.HTTP_200_OK)


# =====================================================
# PREMIUM FEATURE 2 — ATS CHECKER
# =====================================================
class ATSCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return _error("Upload a resume first", status.HTTP_400_BAD_REQUEST)

        resume_text = json.dumps(resume.extracted_data)
        try:
            ats_json = generate_ats_report(resume_text)
        except Exception as e:
            logger.exception("ATSCheck: generate_ats_report failed")
            return _error("Failed to generate ATS report.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "ATS report generated", "ats": ats_json}, status=status.HTTP_200_OK)


# =====================================================
# PREMIUM FEATURE 3 — JD-BASED QUESTIONS
# =====================================================
class JDQuestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        jd = request.data.get("jd")
        if not jd:
            return _error("Job description (jd) required", status.HTTP_400_BAD_REQUEST)

        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return _error("Upload resume first", status.HTTP_400_BAD_REQUEST)

        resume_text = json.dumps(resume.extracted_data)
        try:
            q_json = generate_jd_based_questions(resume_text, jd)
        except Exception as e:
            logger.exception("JDQuestionView: generate_jd_based_questions failed")
            return _error("Failed to generate JD-based questions.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "JD-based questions generated", "questions": q_json}, status=status.HTTP_200_OK)


# =====================================================
# PREMIUM FEATURE 4 — COVER LETTER GENERATOR
# =====================================================
class CoverLetterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        jd = request.data.get("jd")
        if not jd:
            return _error("Job description required", status.HTTP_400_BAD_REQUEST)

        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return _error("Upload resume first", status.HTTP_400_BAD_REQUEST)

        resume_text = json.dumps(resume.extracted_data)
        try:
            result = generate_cover_letter(resume_text, jd)
        except Exception as e:
            logger.exception("CoverLetterView: generate_cover_letter failed")
            return _error("Failed to generate cover letter.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            letter = GeneratedCoverLetter.objects.create(
                user=request.user,
                resume=resume,
                job_description=jd,
                content=result.get("cover_letter", ""),
            )
        except Exception as e:
            logger.exception("CoverLetterView: Failed to save cover letter")
            return _error("Generated cover letter but failed to persist.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Cover letter generated", "cover_letter": result.get("cover_letter", ""), "cover_id": letter.id}, status=status.HTTP_200_OK)


# =====================================================
# PREMIUM FEATURE 5 — INTERVIEW BOT
# =====================================================
