import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Report, ChatSession, ChatMessage
from core.services.ingestion import process_uploaded_json
from core.services.agents import analyze_uploaded_file, chat_agent
from core.services.report_generator import generate_html_report

def dashboard(request):
    """Renderiza a interface principal com o chat e preview."""
    # Para o MVP, não estamos usando sessões de usuário autenticadas.
    # Criaremos uma ChatSession anônima temporária ou a carregaremos da sessão do Django.
    
    session_id = request.session.get('chat_session_id')
    if session_id:
        chat_session = ChatSession.objects.filter(session_id=session_id).first()
    else:
        chat_session = None
        
    if not chat_session:
        chat_session = ChatSession.objects.create()
        request.session['chat_session_id'] = str(chat_session.session_id)
        
    return render(request, 'dashboard.html', {'chat_session': chat_session})

def chat_message(request):
    """
    Endpoint para receber mensagens do chat e arquivos anexados.
    Processa via agentes Agno e retorna a resposta e o ID do relatório (se gerado).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido.'}, status=405)
        
    session_id = request.session.get('chat_session_id')
    chat_session = ChatSession.objects.filter(session_id=session_id).first()
    
    if not chat_session:
        return JsonResponse({'error': 'Sessão inválida.'}, status=400)
        
    message_text = request.POST.get('message', '').strip()
    uploaded_file = request.FILES.get('file')
    
    response_data = {'response': '', 'report_id': None}
    
    # 1. Salvar mensagem do usuário
    user_content = message_text
    db_file = None
    if uploaded_file:
        user_content += f"\n[Arquivo Anexado: {uploaded_file.name}]"
        
    if user_content:
        ChatMessage.objects.create(session=chat_session, role='user', content=user_content)
        
    # 2. Processar arquivo (se houver) -> gera relatório
    if uploaded_file:
        try:
            # Ingestão e validação
            db_file = process_uploaded_json(uploaded_file)
            
            # Atualiza mensagem com a foreign key do arquivo
            last_msg = chat_session.messages.last()
            last_msg.attachment = db_file
            last_msg.save()
            
            # Análise com Agno
            analysis, chart_config = analyze_uploaded_file(db_file)
            
            # Gerar relatório HTML
            report = generate_html_report(analysis, chart_config)
            
            response_data['report_id'] = report.id
            response_data['response'] = f"✅ Arquivo `{uploaded_file.name}` processado com sucesso. Relatório ambiental gerado e disponível no painel ao lado."
            
        except Exception as e:
            response_data['response'] = f"❌ Erro ao processar o arquivo: {str(e)}"
            
    # 3. Processar mensagem de texto livre via chat_agent (se houver e não foi só upload)
    elif message_text:
        try:
            # Obtém histórico da sessão para o agente (opcional, simplificado aqui)
            chat_response = chat_agent.run(message_text)
            response_data['response'] = chat_response.content if hasattr(chat_response, 'content') else chat_response
        except Exception as e:
            response_data['response'] = f"❌ Erro ao comunicar com o assistente: {str(e)}"
            
    # 4. Salvar resposta do assistente
    if response_data['response']:
        ChatMessage.objects.create(session=chat_session, role='assistant', content=response_data['response'])
        
    return JsonResponse(response_data)

from django.views.decorators.clickjacking import xframe_options_sameorigin

@xframe_options_sameorigin
def report_preview(request, report_id):
    """Retorna o HTML cru do relatório para ser renderizado no iframe."""
    report = get_object_or_404(Report, id=report_id)
    return HttpResponse(report.html_content)

def report_data(request, report_id):
    """Retorna os dados do relatório em JSON (opcional)."""
    report = get_object_or_404(Report, id=report_id)
    return JsonResponse({
        'title': report.title,
        'chart_data': report.chart_data,
        'created_at': report.created_at
    })
