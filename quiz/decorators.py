from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import Profile

def teacher_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role == 'teacher':
                return func(request, *args, **kwargs)
            else:
                messages.error(request, 'Access denied! Teachers only.')
                return redirect('dashboard')
        except Profile.DoesNotExist:
            messages.error(request, 'Profile not found.')
            return redirect('dashboard')
    return wrapper

def student_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role == 'student':
                return func(request, *args, **kwargs)
            else:
                messages.error(request, 'Access denied! Students only.')
                return redirect('dashboard')
        except Profile.DoesNotExist:
            messages.error(request, 'Profile not found.')
            return redirect('dashboard')
    return wrapper
