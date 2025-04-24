from django.shortcuts import render

# Create your views here.
from django.shortcuts import render , redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import google.generativeai as genai
import os
from dotenv import load_dotenv
from django.contrib.auth import logout as auth_logout ,authenticate, login as auth_login
from django.contrib.auth.models import User
from .models import Chat
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('models/gemma-3-4b-it')  # Selected model
else:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    model = None


def generate_ai_response(user_message):
   
    if user_message and model:
        try:
            response = model.generate_content(user_message)
            ai_response = response.text
            return ai_response
        except Exception as e:
            return f"Error generating AI response: {str(e)}"
    else:
        return "AI model not initialized or empty message."

# Create your views here.
@login_required()
@csrf_exempt
def chatbot(request):
    chats = Chat.objects.filter(user=request.user).order_by('created_at')
    
    if request.method == 'POST':
        try:
            message = request.POST.get('message')
            response = generate_ai_response(message)
            chat = Chat(
                user=request.user, 
                message=message,
                response=response, 
                created_at=timezone.now()
            )
            chat.save()
            return JsonResponse({
                'message': message,
                'response': response
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
        return render(request, {'chats':chats})
    
    # For GET requests, render the template normally
    return render(request, 'chatbot.html', {'chats': chats})
def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('chatbot'))
    
    if request.method == 'POST':
        if request.user.is_authenticated:
            return redirect('chatbot')
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return JsonResponse({'redirect': reverse('chatbot')})
        else:
            return JsonResponse({'error_message': 'Invalid username or password'}, status=400)
    else:
        return render(request, 'login.html')


def register(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('chatbot'))
    if request.method == 'POST':
        errors = {}
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Validation checks
        if password1 != password2:
            errors['password2'] = ['Passwords do not match']
        
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = ['Enter a valid email address']

        if User.objects.filter(username=username).exists():
            errors['username'] = ['Username already exists']
        
        if User.objects.filter(email=email).exists():
            errors['email'] = ['Email already registered']

        if errors:
            return JsonResponse({'errors': errors}, status=400)

        try:
            user = User.objects.create_user(username, email, password1)
            auth_login(request, user)
            return JsonResponse({'redirect': reverse('chatbot')})
        except Exception as e:
            return JsonResponse({'error_message': str(e)}, status=400)
    
    return render(request, 'register.html')

def logout(request):
    auth_logout(request)
    return redirect('login')