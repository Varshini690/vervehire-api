from django.contrib import admin
from django.contrib.auth.models import User
from .models import Resume, InterviewSetup


# -------------------------------------
# Custom User Admin
# -------------------------------------
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "date_joined", "is_active")
    search_fields = ("username", "email")
    list_filter = ("is_active", "date_joined")


# -------------------------------------
# Resume Admin (shows uploaded files + parsed JSON)
# -------------------------------------
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "file", "uploaded_at")
    search_fields = ("user__username", "user__email")
    list_filter = ("uploaded_at",)
    readonly_fields = ("uploaded_at",)

    # For easier viewing of extracted JSON in admin
    def extracted_json_pretty(self, obj):
        import json
        return json.dumps(obj.extracted_data, indent=2, ensure_ascii=False)

    extracted_json_pretty.short_description = "Extracted Resume Data"


# -------------------------------------
# Interview Setup Admin
# -------------------------------------
class InterviewSetupAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "job_role", "difficulty", "interview_type", "rounds", "created_at")
    search_fields = ("user__username", "job_role", "company")
    list_filter = ("difficulty", "interview_type", "created_at")
    readonly_fields = ("created_at",)


# -------------------------------------
# Register everything
# -------------------------------------
admin.site.unregister(User)          # Unregister default User admin
admin.site.register(User, UserAdmin)
admin.site.register(Resume, ResumeAdmin)
admin.site.register(InterviewSetup, InterviewSetupAdmin)
