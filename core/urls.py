from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/chat/message/', views.chat_message, name='chat_message'),
    path('api/reports/<int:report_id>/preview/', views.report_preview, name='report_preview'),
    path('api/reports/<int:report_id>/data/', views.report_data, name='report_data'),
]
