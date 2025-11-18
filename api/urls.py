from django.urls import path
from .views import (
    RegisterView,
    ResumeUploadView,
    InterviewSetupView,
    ResumeScoreView,
    ATSCheckView,
    JDQuestionView,
    CoverLetterView,

)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Authentication
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Resume upload + parsing
    path("resume/upload/", ResumeUploadView.as_view(), name="resume-upload"),

    # Interview setup + question generation
    path("interview/setup/", InterviewSetupView.as_view(), name="interview-setup"),

    # Premium features
    path("resume/score/", ResumeScoreView.as_view(), name="resume-score"),
    path("resume/ats-check/", ATSCheckView.as_view(), name="ats-check"),
    path("resume/jd-questions/", JDQuestionView.as_view(), name="jd-questions"),
    path("resume/cover-letter/", CoverLetterView.as_view(), name="cover-letter"),
   
]
