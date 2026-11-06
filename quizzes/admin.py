"""Admin configuration for quizzes and questions."""
from django.contrib import admin

from .models import Question, Quiz


class QuestionInline(admin.StackedInline):
    """Edit the questions directly inside a quiz."""

    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin for quizzes with inline questions."""

    list_display = ['title', 'user', 'created_at']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]

    def save_model(self, request, obj, form, change):
        """Assign the creating admin as owner of new quizzes."""
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin for single questions."""

    list_display = ['question_title', 'quiz']
    search_fields = ['question_title']
