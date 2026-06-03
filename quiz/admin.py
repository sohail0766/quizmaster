from django.contrib import admin
from .models import Profile, Category, Quiz, Question, Result, StudentAnswer

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'teacher', 'is_published', 'created_at']
    list_filter = ['is_published', 'category']
    search_fields = ['title', 'teacher__username']
    inlines = [QuestionInline]
    list_editable = ['is_published']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'quiz', 'correct_answer', 'marks']
    list_filter = ['quiz', 'correct_answer']

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'score', 'total_marks', 'percentage', 'attempted_at']
    list_filter = ['quiz']
    search_fields = ['student__username']

@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ['result', 'question', 'selected_answer', 'is_correct']

admin.site.site_header = "QuizMaster Admin"
admin.site.site_title = "QuizMaster"
admin.site.index_title = "Online Quiz System Administration"
