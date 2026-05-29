from django.contrib import admin
from .models import UploadedFile, MarineWasteRecord, AgentAnalysis, Report, ChatSession, ChatMessage

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'status', 'records_count', 'uploaded_at')
    list_filter = ('status', 'uploaded_at')

@admin.register(MarineWasteRecord)
class MarineWasteRecordAdmin(admin.ModelAdmin):
    list_display = ('id_registro', 'data_coleta', 'sensor_origem', 'regiao', 'categoria_residuo')
    list_filter = ('regiao', 'categoria_residuo', 'impacto_imediato', 'sensor_origem')
    search_fields = ('id_registro', 'descricao_visual')

@admin.register(AgentAnalysis)
class AgentAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_file', 'record', 'risco_estimado', 'confianca', 'created_at')
    list_filter = ('risco_estimado', 'created_at')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'created_at', 'updated_at')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'created_at')
    list_filter = ('role', 'created_at')
