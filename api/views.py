import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser

from django.contrib.auth.models import User
from .serializers import (
    RegisterSerializer,
    ResumeSerializer,
    InterviewSetupSerializer,
    ResumeAnalysisSerializer
)
from .models import Resume, InterviewSetup, ResumeAnalysis, InterviewSession, GeneratedCoverLetter

from .utils import (
    parse_resume_text_from_fileobj,
    generate_questions_from_resume,
    generate_resume_score,
    generate_ats_report,
    generate_jd_based_questions,
    generate_cover_letter,
    generate_interview_bot_response
)

# =====================================================
# USER REGISTER (Public)
# =====================================================
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=201)
        print("REGISTER ERROR:", serializer.errors)
        return Response(serializer.errors, status=400)


# =====================================================
# RESUME UPLOAD + AI PARSING
# =====================================================
class ResumeUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("resume")

        if not file:
            return Response({"error": "No resume uploaded. Send 'resume' file."}, status=400)

        resume = Resume.objects.create(user=request.user, file=file)

        # Parse AI resume data
        with resume.file.open("rb") as f:
            parsed = parse_resume_text_from_fileobj(f)

        resume.extracted_data = parsed
        resume.save()

        return Response({
            "message": "Resume uploaded and parsed successfully",
            "data": parsed
        }, status=200)


# =====================================================
# INTERVIEW SETUP + REGULAR QUESTIONS
# =====================================================
class InterviewSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = InterviewSetupSerializer(data=request.data)
        
        if serializer.is_valid():
            setup = serializer.save(user=request.user)

            resume = Resume.objects.filter(user=request.user).last()
            if not resume:
                return Response({"error": "Upload resume first"}, status=400)

            questions = generate_questions_from_resume(
                resume.extracted_data,
                setup.job_role,
                setup.difficulty,
                setup.interview_type,
            )

            return Response({
                "message": "Interview setup complete",
                "questions": questions
            }, status=200)

        return Response(serializer.errors, status=400)


# =====================================================
# PREMIUM FEATURE 1 — RESUME SCORING
# =====================================================
class ResumeScoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Automatically use last uploaded resume
        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return Response({"error": "Upload a resume first"}, status=400)

        resume_text = json.dumps(resume.extracted_data)

        score_json = generate_resume_score(resume_text)

        analysis, _ = ResumeAnalysis.objects.get_or_create(resume=resume)
        analysis.score = score_json.get("score")
        analysis.ats_score = score_json.get("ats_score")
        analysis.strengths = score_json.get("strengths", [])
        analysis.weaknesses = score_json.get("weaknesses", [])
        analysis.skills = score_json.get("skills", [])
        analysis.save()

        return Response({
            "message": "Resume scored",
            "analysis": ResumeAnalysisSerializer(analysis).data
        }, status=200)


# =====================================================
# PREMIUM FEATURE 2 — ATS CHECKER
# =====================================================
class ATSCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return Response({"error": "Upload a resume first"}, status=400)

        resume_text = json.dumps(resume.extracted_data)

        ats_json = generate_ats_report(resume_text)

        return Response({
            "message": "ATS report generated",
            "ats": ats_json
        }, status=200)


# =====================================================
# PREMIUM FEATURE 3 — JD-BASED QUESTIONS
# =====================================================
class JDQuestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        jd = request.data.get("jd")

        if not jd:
            return Response({"error": "Job description (jd) required"}, status=400)

        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return Response({"error": "Upload resume first"}, status=400)

        resume_text = json.dumps(resume.extracted_data)

        q_json = generate_jd_based_questions(resume_text, jd)

        return Response({
            "message": "JD-based questions generated",
            "questions": q_json
        }, status=200)


# =====================================================
# PREMIUM FEATURE 4 — COVER LETTER GENERATOR
# =====================================================
class CoverLetterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        jd = request.data.get("jd")
        if not jd:
            return Response({"error": "Job description required"}, status=400)

        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return Response({"error": "Upload resume first"}, status=400)

        resume_text = json.dumps(resume.extracted_data)

        result = generate_cover_letter(resume_text, jd)

        letter = GeneratedCoverLetter.objects.create(
            user=request.user,
            resume=resume,
            job_description=jd,
            content=result.get("cover_letter", "")
        )

        return Response({
            "message": "Cover letter generated",
            "cover_letter": result.get("cover_letter", ""),
            "cover_id": letter.id
        }, status=200)


# =====================================================
# PREMIUM FEATURE 5 — INTERVIEW BOT
# =====================================================
class InterviewBotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        user_message = request.data.get("message")

        if not user_message:
            return Response({"error": "message is required"}, status=400)

        resume = Resume.objects.filter(user=request.user).last()
        if not resume:
            return Response({"error": "Upload resume first"}, status=400)

        resume_text = json.dumps(resume.extracted_data)

        # Load or create session
        if session_id:
            try:
                session = InterviewSession.objects.get(session_id=session_id)
            except:
                return Response({"error": "Session not found"}, status=404)
        else:
            session = InterviewSession.objects.create(
                user=request.user,
                resume=resume,
                history=[]
            )

        # AI bot reply
        bot_json = generate_interview_bot_response(
            history=session.history,
            resume_text=resume_text,
            user_message=user_message
        )

        # Update chat history
        session.history.append({"role": "user", "content": user_message})
        session.history.append({"role": "ai", "content": bot_json})
        session.save()

        return Response({
            "session_id": session.session_id,
            "response": bot_json,
            "history": session.history
        }, status=200)
