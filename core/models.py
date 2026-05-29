import uuid
from django.db import models

class UploadedFile(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('processado', 'Processado'),
        ('erro', 'Erro'),
    ]

    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    error_message = models.TextField(null=True, blank=True)
    records_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.original_name} ({self.status})"

class MarineWasteRecord(models.Model):
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='records')
    id_registro = models.CharField(max_length=100, unique=True)
    data_coleta = models.DateTimeField()
    sensor_origem = models.CharField(max_length=100)
    regiao = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    categoria_residuo = models.CharField(max_length=100)
    tipo_item = models.CharField(max_length=100)
    estado_conservacao = models.CharField(max_length=100)
    descricao_visual = models.TextField()
    impacto_imediato = models.CharField(max_length=50)
    raw_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id_registro} - {self.categoria_residuo}"

class AgentAnalysis(models.Model):
    # Pode ser associada a um arquivo (lote) ou registro específico (caso precisemos, null=True permite flexibilidade)
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='analyses', null=True, blank=True)
    record = models.ForeignKey(MarineWasteRecord, on_delete=models.CASCADE, related_name='analyses', null=True, blank=True)
    risco_estimado = models.CharField(max_length=50)
    confianca = models.FloatField()
    resumo_ambiental = models.TextField()
    recomendacoes = models.JSONField()
    indicadores = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Análise do arquivo {self.uploaded_file_id} - Risco: {self.risco_estimado}"

class Report(models.Model):
    analysis = models.ForeignKey(AgentAnalysis, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=255)
    html_content = models.TextField()
    chart_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ChatSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.session_id)

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    attachment = models.ForeignKey(UploadedFile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} at {self.created_at}"
