# journals/admin.py
from django.contrib import admin
from .models import Journal, Lesson, Record


class RecordInline(admin.TabularInline):
    model = Record
    extra = 0


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    show_change_link = True


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['group', 'created_at']
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'journal', 'date']
    inlines = [RecordInline]