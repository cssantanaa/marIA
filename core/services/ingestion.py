import json
from datetime import datetime
from pydantic import ValidationError
from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile
from core.models import UploadedFile, MarineWasteRecord
from core.schemas import MarineWasteInput

def process_uploaded_json(django_file: DjangoUploadedFile) -> UploadedFile:
    """
    Recebe um arquivo JSON via request.FILES, valida tamanho e extensão,
    parseia o conteúdo e persiste no SQLite.
    Suporta um objeto único ou uma lista de objetos.
    """
    
    # 1. Criar o registro do arquivo
    uploaded_file = UploadedFile.objects.create(
        original_name=django_file.name,
        file=django_file,
        status='pendente'
    )
    
    try:
        # Voltar o ponteiro do arquivo para o início, pois ao criar o model o Django pode tê-lo lido
        django_file.seek(0)
        content = django_file.read().decode('utf-8')
        data = json.loads(content)
        
        # Pode ser um dict único ou uma lista de dicts
        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, list):
            records = data
        else:
            raise ValueError("O JSON deve ser um objeto ou um array de objetos.")
            
        count = 0
        for item in records:
            # 2. Validar via Pydantic schema
            try:
                validated_data = MarineWasteInput(**item)
            except ValidationError as e:
                # Log e continua ou falha tudo? Vamos lançar erro por enquanto
                raise ValueError(f"Erro de validação no registro: {e}")
                
            # 3. Normalização
            sensor = validated_data.sensor_origem.strip()
            
            # Parse coordenadas ("-9.6658, -35.7050")
            coords = validated_data.localizacao.coordenadas_aproximadas.split(',')
            if len(coords) == 2:
                lat = float(coords[0].strip())
                lon = float(coords[1].strip())
            else:
                lat = 0.0
                lon = 0.0
                
            categoria = validated_data.dados_avistamento.categoria_residuo.strip().upper()
            
            # 4. Persistir o registro
            MarineWasteRecord.objects.update_or_create(
                id_registro=validated_data.id_registro,
                defaults={
                    'uploaded_file': uploaded_file,
                    'data_coleta': validated_data.data_coleta,
                    'sensor_origem': sensor,
                    'regiao': validated_data.localizacao.regiao,
                    'latitude': lat,
                    'longitude': lon,
                    'categoria_residuo': categoria,
                    'tipo_item': validated_data.dados_avistamento.tipo_item,
                    'estado_conservacao': validated_data.dados_avistamento.estado_conservacao,
                    'descricao_visual': validated_data.dados_avistamento.descricao_visual,
                    'impacto_imediato': validated_data.impacto_imediato,
                    'raw_json': item
                }
            )
            count += 1
            
        uploaded_file.status = 'processado'
        uploaded_file.records_count = count
        uploaded_file.save()
        
        return uploaded_file
        
    except Exception as e:
        uploaded_file.status = 'erro'
        uploaded_file.error_message = str(e)
        uploaded_file.save()
        raise e
