from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .models import Profile, Quiz, Question, Result, StudentAnswer, Category
from .forms import RegisterForm, QuizForm, QuestionForm, CategoryForm, PasswordChangeFormCustom
from .decorators import teacher_required, student_required
import json
import google.generativeai as genai

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    total_quizzes = Quiz.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    total_questions = Question.objects.count()
    total_attempts = Result.objects.count()
    categories = Category.objects.all()
    return render(request, 'home.html', {
        'total_quizzes': total_quizzes,
        'total_users': total_users,
        'total_questions': total_questions,
        'total_attempts': total_attempts,
        'categories': categories
    })

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.first_name}! Account created successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def change_password(request):
    form = PasswordChangeFormCustom()
    if request.method == 'POST':
        form = PasswordChangeFormCustom(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['old_password']):
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('profile')
            else:
                messages.error(request, 'Old password is incorrect.')
    return render(request, 'auth/change_password.html', {'form': form})

@login_required
def dashboard(request):
    profile = get_object_or_404(Profile, user=request.user)
    if profile.is_teacher():
        quizzes = Quiz.objects.filter(teacher=request.user)
        total_students = Result.objects.filter(quiz__teacher=request.user).values('student').distinct().count()
        total_results = Result.objects.filter(quiz__teacher=request.user).count()
        avg_score = Result.objects.filter(quiz__teacher=request.user).aggregate(Avg('percentage'))['percentage__avg'] or 0
        return render(request, 'dashboard/teacher_dashboard.html', {
            'quizzes': quizzes,
            'total_students': total_students,
            'total_results': total_results,
            'avg_score': round(avg_score, 1),
            'profile': profile,
        })
    else:
        results = Result.objects.filter(student=request.user).select_related('quiz')
        available_quizzes = Quiz.objects.filter(is_published=True).exclude(results__student=request.user)
        avg_score = results.aggregate(Avg('percentage'))['percentage__avg'] or 0
        return render(request, 'dashboard/student_dashboard.html', {
            'results': results,
            'available_quizzes': available_quizzes,
            'avg_score': round(avg_score, 1),
            'profile': profile,
        })

@login_required
def profile_view(request):
    profile = get_object_or_404(Profile, user=request.user)
    return render(request, 'profile.html', {'profile': profile})

@login_required
def quiz_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    quizzes = Quiz.objects.filter(is_published=True)
    if query:
        quizzes = quizzes.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category:
        quizzes = quizzes.filter(category__id=category)
    paginator = Paginator(quizzes, 6)
    page = request.GET.get('page')
    quizzes = paginator.get_page(page)
    categories = Category.objects.all()
    return render(request, 'quiz/quiz_list.html', {
        'quizzes': quizzes,
        'categories': categories,
        'query': query,
        'selected_category': category,
    })

@login_required
@teacher_required
def quiz_create(request):
    form = QuizForm()
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.teacher = request.user
            quiz.save()
            messages.success(request, 'Quiz created! Now add questions.')
            return redirect('quiz_add_question', pk=quiz.pk)
    return render(request, 'quiz/quiz_form.html', {'form': form, 'title': 'Create Quiz'})

@login_required
@teacher_required
def quiz_edit(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    form = QuizForm(instance=quiz)
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, 'Quiz updated successfully!')
            return redirect('quiz_detail_teacher', pk=quiz.pk)
    return render(request, 'quiz/quiz_form.html', {'form': form, 'title': 'Edit Quiz', 'quiz': quiz})

@login_required
@teacher_required
def quiz_delete(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, 'Quiz deleted!')
        return redirect('dashboard')
    return render(request, 'quiz/quiz_confirm_delete.html', {'quiz': quiz})

@login_required
@teacher_required
def quiz_detail_teacher(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    questions = quiz.questions.all()
    results = Result.objects.filter(quiz=quiz).select_related('student')
    return render(request, 'quiz/quiz_detail_teacher.html', {
        'quiz': quiz,
        'questions': questions,
        'results': results,
    })

@login_required
@teacher_required
def quiz_add_question(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    form = QuestionForm()
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            messages.success(request, 'Question added!')
            if 'add_another' in request.POST:
                return redirect('quiz_add_question', pk=quiz.pk)
            return redirect('quiz_detail_teacher', pk=quiz.pk)
    questions = quiz.questions.all()
    return render(request, 'quiz/add_question.html', {'form': form, 'quiz': quiz, 'questions': questions})

@login_required
@teacher_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk, quiz__teacher=request.user)
    form = QuestionForm(instance=question)
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question updated!')
            return redirect('quiz_detail_teacher', pk=question.quiz.pk)
    return render(request, 'quiz/question_form.html', {'form': form, 'question': question})

@login_required
@teacher_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk, quiz__teacher=request.user)
    quiz_pk = question.quiz.pk
    question.delete()
    messages.success(request, 'Question deleted!')
    return redirect('quiz_detail_teacher', pk=quiz_pk)

@login_required
@teacher_required
def ai_generate_questions(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    if request.method == 'POST':
        topic = request.POST.get('topic')
        num_questions = int(request.POST.get('num_questions', 5))

        if not topic:
            return JsonResponse({'error': 'Topic is required'}, status=400)

        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            return JsonResponse({'error': 'Gemini API key not configured in settings.py'}, status=500)

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""
            Generate exactly {num_questions} multiple-choice questions about '{topic}'.
            Output MUST be a valid JSON array of objects. No preamble, no markdown.
            Each object format:
            {{"text": "question", "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...", "correct_answer": "A/B/C/D"}}
            """

            response = model.generate_content(prompt)
            content = response.text.strip()

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            questions_data = json.loads(content)

            created_count = 0
            for q_data in questions_data:
                Question.objects.create(
                    quiz=quiz,
                    text=q_data['text'],
                    option_a=q_data['option_a'],
                    option_b=q_data['option_b'],
                    option_c=q_data['option_c'],
                    option_d=q_data['option_d'],
                    correct_answer=q_data['correct_answer'].upper(),
                    marks=1
                )
                created_count += 1

            return JsonResponse({
                'success': True,
                'message': f'Successfully generated {created_count} questions!',
                'count': created_count
            })

        except Exception as e:
            return JsonResponse({'error': f"AI Error: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@student_required
def quiz_attempt(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    profile = get_object_or_404(Profile, user=request.user)
    already_attempted = Result.objects.filter(student=request.user, quiz=quiz).exists()
    if already_attempted:
        messages.warning(request, 'You have already attempted this quiz!')
        return redirect('quiz_result', pk=Result.objects.get(student=request.user, quiz=quiz).pk)
    questions = quiz.questions.all()
    if not questions:
        messages.error(request, 'This quiz has no questions yet!')
        return redirect('quiz_list')
    if request.method == 'POST':
        score = 0
        total = 0
        result = Result.objects.create(
            student=request.user,
            quiz=quiz,
            score=0,
            total_marks=0,
            percentage=0
        )
        for question in questions:
            selected = request.POST.get(f'question_{question.pk}', '')
            is_correct = selected == question.correct_answer
            if is_correct:
                score += question.marks
            total += question.marks
            StudentAnswer.objects.create(
                result=result,
                question=question,
                selected_answer=selected,
                is_correct=is_correct
            )
        percentage = (score / total * 100) if total > 0 else 0
        result.score = score
        result.total_marks = total
        result.percentage = round(percentage, 2)
        result.save()
        messages.success(request, f'Quiz submitted! You scored {score}/{total}')
        return redirect('quiz_result', pk=result.pk)
    return render(request, 'quiz/quiz_attempt.html', {
        'quiz': quiz,
        'questions': questions,
    })

@login_required
def quiz_result(request, pk):
    result = get_object_or_404(Result, pk=pk)
    if result.student != request.user and not hasattr(request.user, 'profile') or \
       (result.student != request.user and not Profile.objects.filter(user=request.user, role='teacher').exists()):
        if result.student != request.user:
            messages.error(request, 'Access denied!')
            return redirect('dashboard')
    answers = result.answers.select_related('question').all()
    return render(request, 'quiz/quiz_result.html', {
        'result': result,
        'answers': answers,
    })

@login_required
def download_pdf_result(request, pk):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io

    result = get_object_or_404(Result, pk=pk)
    is_teacher = Profile.objects.filter(user=request.user, role='teacher').exists()
    if result.student != request.user and not is_teacher:
        messages.error(request, 'Access denied!')
        return redirect('dashboard')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    story = []

    header_style = ParagraphStyle('HeaderStyle', fontSize=32, fontName='Helvetica-Bold', alignment=TA_LEFT, leading=36)
    sub_header_style = ParagraphStyle('SubHeaderStyle', fontSize=10, fontName='Helvetica', alignment=TA_LEFT, letterSpacing=1, textColor=colors.black)
    label_style = ParagraphStyle('LabelStyle', fontSize=10, fontName='Helvetica-Bold')
    value_style = ParagraphStyle('ValueStyle', fontSize=10, fontName='Helvetica')
    table_text_style = ParagraphStyle('TableText', fontSize=9, fontName='Helvetica', leading=12)

    header_data = [[Paragraph("QUIZMASTER", header_style)]]
    header_table = Table(header_data, colWidths=[A4[0]-100])
    header_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 2, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("OFFICIAL PERFORMANCE TRANSCRIPT", sub_header_style))
    story.append(Spacer(1, 0.4*inch))

    status_text = "PASSED" if result.percentage >= 50 else "FAILED"
    info_data = [
        [Paragraph("STUDENT", label_style), Paragraph(result.student.get_full_name().upper() or result.student.username.upper(), value_style),
         Paragraph("DATE", label_style), Paragraph(result.attempted_at.strftime('%d %b %Y').upper(), value_style)],
        [Paragraph("QUIZ", label_style), Paragraph(result.quiz.title.upper(), value_style),
         Paragraph("TIME", label_style), Paragraph(result.attempted_at.strftime('%I:%M %p'), value_style)],
        [Paragraph("CATEGORY", label_style), Paragraph(result.quiz.category.name.upper(), value_style),
         Paragraph("STATUS", label_style), Paragraph(status_text, label_style)],
    ]
    info_table = Table(info_data, colWidths=[1.1*inch, 2.4*inch, 1.1*inch, 2.4*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*inch))

    grade = "A" if result.percentage >= 80 else "B" if result.percentage >= 60 else "C" if result.percentage >= 50 else "F"
    score_data = [
        ["TOTAL SCORE", "PERCENTAGE", "GRADE"],
        [f"{result.score} / {result.total_marks}", f"{result.percentage}%", grade]
    ]
    score_table = Table(score_data, colWidths=[2.33*inch, 2.33*inch, 2.34*inch])
    score_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.black),
        ('LINEBELOW', (0, 1), (-1, 1), 1.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, 1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5*inch))

    story.append(Paragraph("PERFORMANCE SUMMARY", ParagraphStyle('SectionHeader', fontSize=12, fontName='Helvetica-Bold', spaceAfter=10)))

    ans_data = [['NO.', 'QUESTION', 'CORRECT', 'SELECTED', 'RESULT']]
    answers = result.answers.select_related('question').all()
    for i, ans in enumerate(answers, 1):
        q_p = Paragraph(ans.question.text, table_text_style)
        correct_p = Paragraph(ans.question.correct_answer, table_text_style)
        selected_p = Paragraph(ans.selected_answer or "-", table_text_style)
        res_text = "PASS" if ans.is_correct else "FAIL"
        ans_data.append([str(i), q_p, correct_p, selected_p, res_text])

    ans_table = Table(ans_data, colWidths=[0.4*inch, 3.4*inch, 1.1*inch, 1.1*inch, 1.0*inch], repeatRows=1)
    ans_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(ans_table)

    story.append(Spacer(1, 0.8*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
    footer_style = ParagraphStyle('Footer', fontSize=8, textColor=colors.black, alignment=TA_CENTER, spaceBefore=5)
    story.append(Paragraph(f"Official transcript generated by QuizMaster Portal. Verification Code: QMR-{result.pk}-{result.student.id}", footer_style))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Transcript_{result.student.username}_{result.pk}.pdf"'
    return response

@login_required
def chart_data(request):
    if Profile.objects.filter(user=request.user, role='teacher').exists():
        quizzes = Quiz.objects.filter(teacher=request.user)
        data = []
        for quiz in quizzes:
            avg = Result.objects.filter(quiz=quiz).aggregate(Avg('percentage'))['percentage__avg'] or 0
            data.append({'name': quiz.title[:20], 'avg': round(avg, 1), 'attempts': quiz.results.count()})
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        results = Result.objects.filter(student=request.user)
        data = [{'name': r.quiz.title[:20], 'score': r.percentage} for r in results]
        return HttpResponse(json.dumps(data), content_type='application/json')

@login_required
@teacher_required
def category_list(request):
    categories = Category.objects.annotate(quiz_count=Count('quizzes'))
    return render(request, 'quiz/category_list.html', {'categories': categories})

@login_required
@teacher_required
def category_create(request):
    form = CategoryForm()
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created!')
            return redirect('category_list')
    return render(request, 'quiz/category_form.html', {'form': form})