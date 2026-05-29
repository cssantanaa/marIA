import json
from django.template.loader import render_to_string
from core.models import Report, AgentAnalysis

def generate_html_report(analysis: AgentAnalysis, chart_config: list) -> Report:
    """
    Renderiza o relatório HTML usando o template report.html e salva no banco.
    """
    
    # Prepara os dados para o template
    context = {
        'titulo': f"Relatório de Monitoramento: {analysis.uploaded_file.original_name}",
        'data_analise': analysis.created_at.strftime("%d/%m/%Y %H:%M"),
        'risco_estimado': analysis.risco_estimado,
        'resumo_ambiental': analysis.resumo_ambiental,
        'recomendacoes': analysis.recomendacoes,
        'indicadores': analysis.indicadores,
        # O Chart.js precisa de JSON parseável no template
        'chart_data_json': json.dumps(chart_config)
    }
    
    # Renderiza o HTML
    html_content = render_to_string('report.html', context)
    
    # Salva no banco
    report = Report.objects.create(
        analysis=analysis,
        title=context['titulo'],
        html_content=html_content,
        chart_data=chart_config
    )
    
    return report
