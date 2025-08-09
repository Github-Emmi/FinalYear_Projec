from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.contrib.auth import login,logout
from django.urls import reverse
from .models import RememberToken
import secrets
from django.shortcuts import render, get_object_or_404, redirect
from notifications.models import Notification
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Event

from schoolapp.EmailBackEnd import EmailBackEnd

# Create your views here.

def index(request):
     return render(request, 'jobs/index.html', {})

def about(request):
     return render(request, 'jobs/about.html', {}) 

def classes(request):
     return render(request, 'jobs/classes.html', {})    

def academics(request):
     return render(request, 'jobs/academics.html', {})  

def gallery(request):
     
     return render(request, 'jobs/gallery.html', {})

def contact(request):
     return render(request, 'jobs/contact.html', {})   

def user_login(request):
    return render(request, 'jobs/login.html', {})


def DoLogin(request):
    if request.method != "POST":
        return HttpResponse('<h2>Method Not Allowed</h2>')
    else:
        email = request.POST.get("email")
        password = request.POST.get("password")
        remember = request.POST.get("remember_me") == "true"

        user = EmailBackEnd.authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)

            if remember:
                token = secrets.token_hex(32)
                RememberToken.objects.update_or_create(user=user, defaults={'token': token})
                response = HttpResponseRedirect(reverse_user_home(user))
                response.set_cookie('remember_token', token, max_age=60*60*24*7, httponly=True, secure=True)
                return response

            return HttpResponseRedirect(reverse_user_home(user))
        else:
            messages.error(request, "Invalid Login Details (Email or Password)")
            return HttpResponseRedirect("/login")

def reverse_user_home(user):
    if user.user_type == "1":
        return "/admin-home"
    elif user.user_type == "2":
        return reverse("staff_home")
    else:
        return reverse("student_home")
        
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')      

@login_required
def notifications_list(request):
    query = request.GET.get('q', '')
    page = request.GET.get('page', 1)

    notes = request.user.notifications.all()
    if query:
        notes = notes.filter(verb__icontains=query)

    paginator = Paginator(notes.order_by('-timestamp'), 10)
    try:
        page_obj = paginator.get_page(page)
    except:
        page_obj = paginator.get_page(1)

    context = {
        'page_obj': page_obj,
        'query': query,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'notifications/_notification_rows.html', context)
    return render(request, 'notifications/notifications_list.html', context)

@login_required
def staff_notifications_list(request):
    query = request.GET.get('q', '')
    page = request.GET.get('page', 1)

    notes = request.user.notifications.all()
    if query:
        notes = notes.filter(verb__icontains=query)

    paginator = Paginator(notes.order_by('-timestamp'), 10)
    try:
        page_obj = paginator.get_page(page)
    except:
        page_obj = paginator.get_page(1)

    context = {
        'page_obj': page_obj,
        'query': query,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'notifications/_staff_notification_rows.html', context)
    return render(request, 'notifications/staff_notifications_list.html', context)


@login_required
def delete_selected_notifications(request):
    if request.method == 'POST':
        ids = request.POST.getlist('selected_ids[]')
        if ids:
            request.user.notifications.filter(id__in=ids).delete()
            return JsonResponse({'status': 'success'})
    return HttpResponseBadRequest()


@login_required
def mark_all_read(request):
    """Mark all notifications as read for the current user."""
    Notification.objects.filter(recipient=request.user, unread=True).update(unread=False)
    return redirect('notifications_list')


@login_required
def notification_read(request, pk):
    """Mark a single notification as read and redirect to its target (if any)."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.unread = False
    notification.save()
    return redirect(notification.target.get_absolute_url() if notification.target else 'notifications_list')

@login_required
def calendar_events_json(request):
    user = request.user
    user_type = user.user_type

    if user_type == "2":  # Staff
        audience_filter = ['ALL', 'STAFFS']
    elif user_type == "3":  # Student
        audience_filter = ['ALL', 'STUDENTS']
    else:
        audience_filter = ['ALL']

    events = Event.objects.filter(
        target_audience__in=audience_filter
    ).order_by("event_datetime")

    data = []
    for event in events:
        data.append({
            "title": event.title,
            "start": event.event_datetime.isoformat(),
            "description": event.description,
            "color": event.get_event_color(),
        })

    return JsonResponse(data, safe=False)

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, "notifications/event_detail.html", {"event": event})
