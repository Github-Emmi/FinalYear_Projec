# schoolapp/views_token.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from agora_token_builder import RtcTokenBuilder
from datetime import datetime, timedelta

from schoolapp.models import Room, Students, Staffs

TOKEN_EXPIRATION_SECONDS = 3600 * 24

def build_agora_token(channel_name, uid):
    role = 1  # publisher
    expiration_ts = int((datetime.now(datetime.timezone.utc) + timedelta(seconds=TOKEN_EXPIRATION_SECONDS)).timestamp())
    return RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        role,
        expiration_ts
    )

@login_required
def generate_agora_token(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    user = request.user
    uid = user.id

    if user.user_type == '3':  # Student
        try:
            student = Students.objects.get(admin=user)
            if room.classroom_id != student.class_id_id:
                return JsonResponse({'error': 'Access denied to this classroom room.'}, status=403)
        except Students.DoesNotExist:
            return JsonResponse({'error': 'Student profile not found'}, status=403)

    elif user.user_type == '2':  # Staff
        try:
            staff = Staffs.objects.get(admin=user)
        except Staffs.DoesNotExist:
            return JsonResponse({'error': 'Staff profile not found'}, status=403)
        if room.classroom_id is not None:
            return JsonResponse({'error': 'Access denied to classroom rooms.'}, status=403)

    elif user.user_type == '1':  # Admin
        pass

    else:
        return JsonResponse({'error': 'Invalid user type'}, status=403)

    token = build_agora_token(room.channel_name, uid)

    return JsonResponse({
        'token': token,
        'channel_name': room.channel_name,
        'uid': uid,
        'app_id': settings.AGORA_APP_ID,
    })
