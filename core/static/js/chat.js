document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const fileUpload = document.getElementById('file-upload');
    const filePreview = document.getElementById('file-preview');
    const fileNameDisplay = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');
    const chatMessages = document.getElementById('chat-messages');
    const iframe = document.getElementById('report-iframe');
    const emptyState = document.getElementById('empty-state');
    const loadingState = document.getElementById('loading-state');
    const btnRefresh = document.getElementById('btn-refresh-report');
    
    let currentFile = null;
    let currentReportId = null;

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') {
            this.style.height = 'auto';
        }
    });

    // Handle Enter key (Shift+Enter for new line)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim() !== '' || currentFile) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    // File Selection
    fileUpload.addEventListener('change', function(e) {
        if (this.files && this.files.length > 0) {
            currentFile = this.files[0];
            fileNameDisplay.textContent = currentFile.name;
            filePreview.style.display = 'flex';
        }
    });

    // Remove File
    removeFileBtn.addEventListener('click', function(e) {
        e.preventDefault();
        currentFile = null;
        fileUpload.value = '';
        filePreview.style.display = 'none';
    });

    // Append Message to Chat
    function appendMessage(role, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Simples formatação de markdown básico para negrito e quebras de linha
        let formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
            
        contentDiv.innerHTML = formattedContent;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const now = new Date();
        timeDiv.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        
        msgDiv.appendChild(contentDiv);
        msgDiv.appendChild(timeDiv);
        
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    // Scroll chat to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Show typing indicator
    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<i class="fa-solid fa-ellipsis fa-fade"></i> Processando...';
        
        typingDiv.appendChild(contentDiv);
        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }

    // Remove typing indicator
    function hideTyping() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // Load Report in Iframe
    function loadReport(reportId) {
        currentReportId = reportId;
        emptyState.style.display = 'none';
        loadingState.style.display = 'none';
        iframe.style.display = 'block';
        iframe.src = `/api/reports/${reportId}/preview/`;
    }

    // Refresh report button
    btnRefresh.addEventListener('click', () => {
        if (currentReportId) {
            const currentSrc = iframe.src;
            iframe.src = 'about:blank';
            setTimeout(() => { iframe.src = currentSrc; }, 50);
        }
    });

    // Handle Form Submit
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const text = chatInput.value.trim();
        
        if (!text && !currentFile) return;
        
        // UI Updates for user message
        let userContent = text;
        if (currentFile) {
            userContent += userContent ? '<br><br>' : '';
            userContent += `📎 <i>Anexou: ${currentFile.name}</i>`;
        }
        
        if(userContent) {
            appendMessage('user', userContent);
        }
        
        // Prepare FormData
        const formData = new FormData();
        formData.append('message', text);
        if (currentFile) {
            formData.append('file', currentFile);
            
            // Show loading on the left side if there's a file
            emptyState.style.display = 'none';
            iframe.style.display = 'none';
            loadingState.style.display = 'flex';
        }
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Reset input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        removeFileBtn.click();
        
        showTyping();
        
        try {
            const response = await fetch('/api/chat/message/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });
            
            const data = await response.json();
            
            hideTyping();
            
            if (response.ok) {
                if (data.response) {
                    appendMessage('assistant', data.response);
                }
                
                if (data.report_id) {
                    loadReport(data.report_id);
                } else if (!currentReportId) {
                    // Restore empty state if no report generated and none active
                    loadingState.style.display = 'none';
                    emptyState.style.display = 'flex';
                }
            } else {
                appendMessage('assistant', `❌ Ocorreu um erro: ${data.error || 'Falha ao processar requisição.'}`);
                loadingState.style.display = 'none';
                if (!currentReportId) emptyState.style.display = 'flex';
            }
        } catch (error) {
            hideTyping();
            appendMessage('assistant', '❌ Erro de conexão com o servidor.');
            loadingState.style.display = 'none';
            if (!currentReportId) emptyState.style.display = 'flex';
            console.error(error);
        }
    });
});
