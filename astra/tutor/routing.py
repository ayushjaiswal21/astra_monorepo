from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/course/(?P<course_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/lesson/(?P<lesson_id>\w+)/$', consumers.LessonConsumer.as_asgi()),
    re_path(r'ws/tutor/chat/$', consumers.TutorChatConsumer.as_asgi()),
]
