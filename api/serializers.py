from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Resume
from .models import InterviewSetup
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            username = validated_data["username"],
            email = validated_data["email"],
            password = validated_data["password"]
        )
        return user
class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = "__all__"
        read_only_fields = ["user", "extracted_data"]



class InterviewSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSetup
        fields = "__all__"
        read_only_fields = ["user"]



# api/serializers.py (append)

from .models import ResumeAnalysis, InterviewSession, GeneratedCoverLetter

class ResumeAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeAnalysis
        fields = "__all__"
        read_only_fields = ["resume", "created_at", "updated_at"]

class InterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSession
        fields = "__all__"
        read_only_fields = ["session_id", "created_at", "updated_at", "user"]

class GeneratedCoverLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedCoverLetter
        fields = "__all__"
        read_only_fields = ["user", "created_at"]
