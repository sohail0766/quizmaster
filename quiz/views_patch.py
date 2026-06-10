NEW_FUNCTION = '''
@login_required
@teacher_required
def ai_generate_questions(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    if request.method == 'POST':
        topic = request.POST.get('topic')
        num_questions = int(request.POST.get('num_questions', 5))

        if not topic:
            return JsonResponse({'error': 'Topic is required'}, status=400)

        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            return JsonResponse({'error': 'Groq API key not configured in settings.'}, status=500)

        try:
            client = Groq(api_key=api_key)

            prompt = f"""Generate exactly {num_questions} multiple-choice questions about '{topic}'.
Output MUST be a valid JSON array of objects. No preamble, no markdown, no extra text.
Each object format:
{{"text": "question", "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...", "correct_answer": "A/B/C/D"}}"""

            response = client.chat.completions.create(
                model='llama3-8b-8192',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            try:
                questions_data = json.loads(content)
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'AI Error: Response was not valid JSON. Please try again.'
                }, status=500)

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
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower() or "quota" in err_str.lower():
                return JsonResponse({'error': 'AI Error: Groq rate limit reached. Please wait a moment and try again.'}, status=429)
            elif "401" in err_str or "invalid api key" in err_str.lower() or "authentication" in err_str.lower():
                return JsonResponse({'error': 'AI Error: Invalid Groq API key. Please check your GROQ_API_KEY setting.'}, status=403)
            return JsonResponse({'error': f'AI Error: {err_str}'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)
'''
