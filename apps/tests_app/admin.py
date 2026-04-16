from django.contrib import admin
from .models import TestPack, Question, Choice, GlobalTestAttempt, GlobalTestAnswer


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(TestPack)
class TestPackAdmin(admin.ModelAdmin):
    list_display = ['title', 'mode', 'question_count', 'coin_reward', 'created_by', 'created_at']
    list_filter  = ['mode']
    inlines      = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'test_pack', 'order']
    inlines      = [ChoiceInline]


@admin.register(GlobalTestAttempt)
class GlobalTestAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'test_pack', 'score', 'total', 'status', 'coins_awarded', 'started_at']


@admin.register(GlobalTestAnswer)
class GlobalTestAnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'choice', 'is_correct']
