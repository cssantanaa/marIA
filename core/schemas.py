from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional

class LocationInput(BaseModel):
    regiao: str
    coordenadas_aproximadas: str

class SightingDataInput(BaseModel):
    categoria_residuo: str
    tipo_item: str
    estado_conservacao: str
    descricao_visual: str

class MarineWasteInput(BaseModel):
    id_registro: str
    data_coleta: datetime
    sensor_origem: str
    localizacao: LocationInput
    dados_avistamento: SightingDataInput
    impacto_imediato: str

class AnalysisOutput(BaseModel):
    titulo: str = Field(description="Título curto do relatório")
    resumo_ambiental: str = Field(description="Resumo do impacto ambiental avaliado")
    risco_estimado: str = Field(description="Nível de risco: baixo, moderado, alto, crítico")
    confianca: float = Field(description="Grau de confiança da análise entre 0 e 1")
    indicadores: Dict[str, Any] = Field(description="Dicionário com KPIs extraídos (ex: total_itens, categorias_encontradas)")
    graficos: List[Dict[str, Any]] = Field(description="Lista de configurações para Chart.js")
    recomendacoes: List[str] = Field(description="Ações sugeridas")

class DataQualityOutput(BaseModel):
    valido: bool = Field(description="Verdadeiro se o registro tem qualidade aceitável")
    problemas: List[str] = Field(description="Lista de inconsistências encontradas")
    dados_corrigidos: Dict[str, Any] = Field(description="Tentativa de corrigir os dados")
    confianca_dados: float = Field(description="Grau de confiança nos dados originais entre 0 e 1")
