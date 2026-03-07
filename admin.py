"""Register all models with Django admin for easy management."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User, Group as StudentGroup
from apps.tasks.models import Task, TestCase
from apps.sessions_app.models import Session
from apps.submissions.models import Submission


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('CodeLearn', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('CodeLearn', {'fields': ('role',)}),
    )


@admin.register(StudentGroup)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'student_count', 'created_at')
    filter_horizontal = ('students',)

    def student_count(self, obj):
        return obj.students.count()


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'time_limit', 'memory_limit', 'created_at')
    inlines = [TestCaseInline]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active', 'start_time', 'created_at')
    list_filter = ('is_active',)
    actions = ['activate_sessions', 'deactivate_sessions']

    def activate_sessions(self, request, queryset):
        queryset.update(is_active=True)
    activate_sessions.short_description = 'Activate selected sessions'

    def deactivate_sessions(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_sessions.short_description = 'Deactivate selected sessions'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'student', 'task', 'status', 'is_correct', 'created_at')
    list_filter = ('status', 'is_correct')
    readonly_fields = ('results',)
