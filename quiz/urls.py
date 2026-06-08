from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password, name='change_password'),

    # Dashboard & Profile
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),

    # Quiz
    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/create/', views.quiz_create, name='quiz_create'),
    path('quiz/<int:pk>/edit/', views.quiz_edit, name='quiz_edit'),
    path('quiz/<int:pk>/delete/', views.quiz_delete, name='quiz_delete'),
    path('quiz/<int:pk>/detail/', views.quiz_detail_teacher, name='quiz_detail_teacher'),
    path('quiz/<int:pk>/add-question/', views.quiz_add_question, name='quiz_add_question'),
    path('quiz/<int:pk>/attempt/', views.quiz_attempt, name='quiz_attempt'),
    path('quiz/result/<int:pk>/', views.quiz_result, name='quiz_result'),

    # AI Generation
    path('quiz/<int:pk>/ai-generate/', views.ai_generate_questions, name='ai_generate_questions'),

    # Questions
    path('question/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('question/<int:pk>/delete/', views.question_delete, name='question_delete'),

    # PDF & Charts
    path('result/<int:pk>/pdf/', views.download_pdf_result, name='download_pdf'),
    path('chart-data/', views.chart_data, name='chart_data'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),

    # SEO
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),

    # Google Search Console Verification
    path('googled243ab1274c211cc.html', views.google_verify, name='google_verify'),
]
