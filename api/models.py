from django.db import models
from django.contrib.auth.models import User


class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Resume {self.pk} - {self.user.username}"
    

class InterviewSetup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_role = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=20)
    interview_type = models.CharField(max_length=100)
    rounds = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.job_role}"
# api/models.py (append these)

import uuid
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class ResumeAnalysis(models.Model):
    resume = models.OneToOneField("Resume", on_delete=models.CASCADE, related_name="analysis")
    score = models.IntegerField(null=True, blank=True)
    ats_score = models.IntegerField(null=True, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    weaknesses = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis for Resume {self.resume.pk}"


class InterviewSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interview_sessions")
    resume = models.ForeignKey("Resume", on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    history = models.JSONField(default=list, blank=True)  # list of {"role": "user/ai", "content": "..."}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"InterviewSession {self.session_id} - {self.user}"

class GeneratedCoverLetter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="generated_cover_letters")
    resume = models.ForeignKey("Resume", on_delete=models.SET_NULL, null=True, blank=True)
    job_description = models.TextField(blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CoverLetter {self.pk} - {self.user}"
