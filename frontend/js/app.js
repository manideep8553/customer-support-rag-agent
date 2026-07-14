(function() {
  'use strict';

  const API_BASE = '/api/v1';
  let currentSessionId = null;

  const elements = {
    sidebar: document.getElementById('sidebar'),
    sidebarToggle: document.getElementById('sidebar-toggle'),
    newChatBtn: document.getElementById('new-chat-btn'),
    sessionsList: document.getElementById('sessions-list'),
    messagesContainer: document.getElementById('messages-container'),
    welcomeMessage: document.getElementById('welcome-message'),
    messageInput: document.getElementById('message-input'),
    sendBtn: document.getElementById('send-btn'),
    typingIndicator: document.getElementById('typing-indicator'),
    sessionBadge: document.getElementById('session-badge'),
    sourceModal: document.getElementById('source-modal'),
    sourceModalBody: document.getElementById('source-modal-body'),
    sourceModalClose: document.getElementById('source-modal-close'),
  };

  function apiUrl(path) {
    return `${API_BASE}${path}`;
  }

  async function apiPost(path, body) {
    const res = await fetch(apiUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  async function apiGet(path) {
    const res = await fetch(apiUrl(path));
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  async function apiDelete(path) {
    const res = await fetch(apiUrl(path), { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function markdownToHtml(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';
    html = html.replace(/<p><\/p>/g, '');
    return html;
  }

  async function createSession() {
    const data = await apiPost('/sessions', {});
    return data.session_id;
  }

  async function ensureSession() {
    if (!currentSessionId) {
      currentSessionId = await createSession();
      updateSessionBadge();
      loadSessions();
    }
    return currentSessionId;
  }

  function updateSessionBadge() {
    if (currentSessionId) {
      const shortId = currentSessionId.slice(-8);
      elements.sessionBadge.textContent = `Session: ${shortId}`;
    } else {
      elements.sessionBadge.textContent = '';
    }
  }

  async function loadSessions() {
    try {
      const sessions = await apiGet('/sessions');
      renderSessions(sessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }

  function renderSessions(sessions) {
    const list = elements.sessionsList;
    if (!sessions || sessions.length === 0) {
      list.innerHTML = '<div class="sessions-empty">No conversations yet</div>';
      return;
    }

    list.innerHTML = sessions.map(s => {
      const isActive = s.session_id === currentSessionId;
      const preview = s.message_count > 0 ? `${s.message_count} messages` : 'Empty';
      return `
        <div class="session-item${isActive ? ' active' : ''}" data-session-id="${s.session_id}">
          <span class="session-item-icon">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
            </svg>
          </span>
          <span class="session-item-text">${preview}</span>
          <span class="session-item-actions">
            <button class="btn-delete-session" data-session-id="${s.session_id}" title="Delete conversation">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 3h8M4 3V2a1 1 0 011-1h2a1 1 0 011 1v1M5 5.5v3M7 5.5v3M3 3l.5 7a1 1 0 001 1h3a1 1 0 001-1L9 3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </span>
        </div>
      `;
    }).join('');

    list.querySelectorAll('.session-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.btn-delete-session')) return;
        switchSession(item.dataset.sessionId);
      });
    });

    list.querySelectorAll('.btn-delete-session').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const sid = btn.dataset.sessionId;
        await deleteSession(sid);
      });
    });
  }

  async function switchSession(sessionId) {
    currentSessionId = sessionId;
    updateSessionBadge();
    loadSessions();
    await loadHistory(sessionId);
  }

  async function deleteSession(sessionId) {
    try {
      await apiDelete(`/sessions/${sessionId}`);
      if (currentSessionId === sessionId) {
        currentSessionId = null;
        elements.welcomeMessage.classList.remove('hidden');
        elements.messagesContainer.querySelectorAll('.message').forEach(m => m.remove());
        updateSessionBadge();
      }
      loadSessions();
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  }

  async function loadHistory(sessionId) {
    try {
      const data = await apiPost(`/sessions/${sessionId}/history`, { session_id: sessionId, limit: 50 });
      renderHistory(data.messages);
    } catch (err) {
      if (err.message.includes('404')) {
        currentSessionId = null;
        updateSessionBadge();
      }
    }
  }

  function renderHistory(messages) {
    elements.messagesContainer.querySelectorAll('.message').forEach(m => m.remove());
    elements.welcomeMessage.classList.add('hidden');

    if (!messages || messages.length === 0) {
      elements.welcomeMessage.classList.remove('hidden');
      return;
    }

    messages.forEach(msg => {
      if (msg.role === 'system') return;
      if (msg.role === 'assistant' && msg.content.startsWith('You are GigaBot')) return;
      const isUser = msg.role === 'user';
      addMessageToUI(isUser ? 'user' : 'bot', msg.content, null, msg.timestamp);
    });

    scrollToBottom();
  }

  function getSourceMeta(s) {
    const meta = s.metadata || {};
    return {
      doc: meta.source || s.source || 'Document',
      heading: meta.heading || '',
      chunk: meta.chunk_index !== undefined ? `#${meta.chunk_index + 1}` : '',
    };
  }

  function formatSourceLabel(s, i) {
    const meta = getSourceMeta(s);
    let label = `[${i + 1}]`;
    if (meta.heading) label += ` ${meta.heading}`;
    return label;
  }

  function addMessageToUI(role, text, sources, timestamp) {
    elements.welcomeMessage.classList.add('hidden');

    const container = elements.messagesContainer;
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatar = role === 'user' ? 'U' : 'G';
    const time = timestamp ? formatTime(new Date(timestamp)) : formatTime(new Date());

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
      const sourcesJson = escapeHtml(JSON.stringify(sources));
      sourcesHtml = `
        <div class="message-sources">
          <div class="sources-label">Sources</div>
          ${sources.map((s, i) => {
            const meta = getSourceMeta(s);
            return `
            <button class="source-badge" data-sources='${sourcesJson}' data-index="${i}">
              <span class="source-badge-num">${i + 1}</span>
              <span class="source-badge-info">
                <span class="source-badge-heading">${escapeHtml(meta.heading || 'Untitled Section')}</span>
                <span class="source-badge-doc">${escapeHtml(meta.doc)} ${meta.chunk}</span>
              </span>
              <span class="source-badge-score">${(s.score * 100).toFixed(0)}%</span>
            </button>
          `}).join('')}
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div class="message-avatar">${avatar}</div>
      <div class="message-content">
        <div class="message-text">${markdownToHtml(text)}</div>
        ${sourcesHtml}
        <div class="message-time">${time}</div>
      </div>
    `;

    container.appendChild(msgDiv);

    msgDiv.querySelectorAll('.source-badge').forEach(btn => {
      btn.addEventListener('click', () => {
        const sources = JSON.parse(btn.dataset.sources);
        showSourceModal(sources);
      });
    });

    scrollToBottom();
  }

  function scrollToBottom() {
    setTimeout(() => {
      elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
    }, 50);
  }

  function showTyping() {
    elements.typingIndicator.classList.remove('hidden');
  }

  function hideTyping() {
    elements.typingIndicator.classList.add('hidden');
  }

  function showSourceModal(sources) {
    const body = elements.sourceModalBody;
    body.innerHTML = sources.map((s, i) => {
      const meta = getSourceMeta(s);
      return `
      <div class="source-item">
        <div class="source-item-header">
          <span class="source-item-title">${escapeHtml(meta.heading || 'Untitled Section')}</span>
          <span class="source-item-score">${(s.score * 100).toFixed(0)}% match</span>
        </div>
        <div class="source-item-meta">
          <span>${escapeHtml(meta.doc)}</span>
          ${meta.chunk ? `<span>Chunk ${meta.chunk}</span>` : ''}
        </div>
        <div class="source-item-content">${escapeHtml(s.content)}</div>
      </div>
    `}).join('');
    elements.sourceModal.classList.remove('hidden');
  }

  async function sendMessage() {
    const text = elements.messageInput.value.trim();
    if (!text) return;

    elements.messageInput.value = '';
    elements.sendBtn.disabled = true;
    autoResizeInput();

    addMessageToUI('user', text, null);

    try {
      await ensureSession();
      showTyping();

      const data = await apiPost('/chat', {
        session_id: currentSessionId,
        message: text,
      });

      hideTyping();
      addMessageToUI('bot', data.answer, data.sources, data.timestamp);
      loadSessions();
    } catch (err) {
      hideTyping();
      addMessageToUI('bot', `I apologize, but I encountered an error: ${err.message}. Please try again or contact our support team.`, null);
    }
  }

  function autoResizeInput() {
    elements.messageInput.style.height = 'auto';
    elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 150) + 'px';
  }

  function handleInput() {
    const hasText = elements.messageInput.value.trim().length > 0;
    elements.sendBtn.disabled = !hasText;
    autoResizeInput();
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function handleNewChat() {
    currentSessionId = null;
    updateSessionBadge();
    elements.messagesContainer.querySelectorAll('.message').forEach(m => m.remove());
    elements.welcomeMessage.classList.remove('hidden');
    elements.messageInput.focus();

    await ensureSession();
    loadSessions();
  }

  function initEventListeners() {
    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('input', handleInput);
    elements.messageInput.addEventListener('keydown', handleKeydown);
    elements.newChatBtn.addEventListener('click', handleNewChat);

    elements.sidebarToggle.addEventListener('click', () => {
      elements.sidebar.classList.toggle('collapsed');
    });

    elements.sourceModalClose.addEventListener('click', () => {
      elements.sourceModal.classList.add('hidden');
    });

    elements.sourceModal.querySelector('.source-modal-backdrop').addEventListener('click', () => {
      elements.sourceModal.classList.add('hidden');
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        elements.sourceModal.classList.add('hidden');
      }
    });

    elements.messageInput.addEventListener('focus', () => {
      if (window.innerWidth <= 768) {
        setTimeout(scrollToBottom, 300);
      }
    });

    document.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        elements.messageInput.value = chip.dataset.query;
        handleInput();
        sendMessage();
      });
    });
  }

  async function init() {
    initEventListeners();
    await ensureSession();
    loadSessions();
    elements.messageInput.focus();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
