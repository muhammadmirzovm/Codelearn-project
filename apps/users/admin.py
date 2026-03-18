"""Register all models with Django admin for easy management."""
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User, Group as StudentGroup
from apps.tasks.models import Task, TestCase
from apps.sessions_app.models import Session
from apps.submissions.models import Submission


from .models import Notification
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.urls import path

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



User = get_user_model()


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    change_list_template = 'admin/users/notification/change_list.html'
    list_display    = ('title', 'recipient', 'notif_type', 'is_read', 'created_at')
    list_filter     = ('notif_type', 'is_read')
    search_fields   = ('title', 'recipient__username')
    readonly_fields = ('created_at',)
    list_per_page   = 25
    date_hierarchy  = 'created_at'

    def get_urls(self):
        return [
            path(
                'send-to-all/',
                self.admin_site.admin_view(self.send_to_all_view),
                name='send_notif_all',
            ),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(request, {
            **(extra_context or {}),
            'send_to_all_url': 'send-to-all/',
        })

    def send_to_all_view(self, request):
        if request.method == 'POST':
            title      = request.POST.get('title', '').strip()
            message    = request.POST.get('message', '').strip()
            notif_type = request.POST.get('notif_type', 'info')
            target     = request.POST.get('target', 'all')

            if not title:
                messages.error(request, '❌ Title is required!')
                return redirect('.')

            qs = User.objects.filter(is_active=True)
            if target == 'teachers':
                qs = qs.filter(role='teacher')
            elif target == 'students':
                qs = qs.filter(role='student')

            # Only fetch IDs — avoid loading full User objects into memory
            user_ids = list(qs.values_list('id', flat=True))

            Notification.objects.bulk_create([
                Notification(
                    recipient_id=uid,
                    title=title,
                    message=message,
                    notif_type=notif_type,
                )
                for uid in user_ids
            ])

            messages.success(request, f'✅ Notification sent to {len(user_ids)} users!')
            return redirect('/admin/users/notification/')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Send Notification to All Users',
            'type_choices': Notification.TYPE_CHOICES,
        }
        return render(request, 'admin/send_notification.html', context)