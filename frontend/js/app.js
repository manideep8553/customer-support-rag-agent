(function() {
  'use strict';

  const API_BASE = '/api/v1';
  let currentSessionId = null;
  let isStreaming = false;
  let abortStream = null;

  const el = {
    sidebar: document.getElementById('sidebar'),
    sidebarToggle: document.getElementById('sidebar-toggle'),
    newChatBtn: document.getElementById('new-chat-btn'),
    sessionsList: document.getElementById('sessions-list'),
    msgContainer: document.getElementById('messages-container'),
    welcome: document.getElementById('welcome-message'),
    input: document.getElementById('message-input'),
    sendBtn: document.getElementById('send-btn'),
    typing: document.getElementById('typing-indicator'),
    sessionBadge: document.getElementById('session-badge'),
    sourceModal: document.getElementById('source-modal'),
    sourceBody: document.getElementById('source-modal-body'),
    sourceClose: document.getElementById('source-modal-close'),
  };

  /* ─── API ─── */
  const api = {
    async post(path, body) {
      const r = await fetch(API_BASE + path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({detail: r.statusText}));
        throw new Error(e.detail || 'Request failed');
      }
      return r.json();
    },
    async get(path) {
      const r = await fetch(API_BASE + path);
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      return r.json();
    },
    async del(path) {
      const r = await fetch(API_BASE + path, {method: 'DELETE'});
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      return r.json();
    },
  };

  /* ─── Utils ─── */
  function fmtTime(date) {
    return date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  /* ─── Markdown ─── */
  function renderMarkdown(text) {
    let html = esc(text);

    // Code blocks (fenced with ```) - must happen before inline code
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      const langLabel = lang ? esc(lang) : 'code';
      return `<div class="code-block-wrapper">
        <div class="code-block-header">
          <span>${langLabel}</span>
          <button class="code-block-copy" data-code="${esc(code.replace(/&/g,'&amp;').replace(/"/g,'&quot;'))}">Copy</button>
        </div>
        <pre><code>${esc(code)}</code></pre>
      </div>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold / italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

    // Unordered lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => m.includes('<ul>') ? m : '<ol>' + m + '</ol>');

    // Tables
    html = html.replace(/<p>\|(.+)\|<\/p>/g, '<table><thead><tr>$1</tr></thead></table>');
    html = html.replace(/\|(.+)\|/g, '<tr><td>$1</td></tr>');
    html = html.replace(/<tr><td>[-| ]+<\/td><\/tr>/g, ''); // skip separator rows

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Paragraphs
    const parts = html.split('\n\n');
    if (parts.length > 1) {
      html = parts.map(p => {
        const trimmed = p.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<ol') ||
            trimmed.startsWith('<blockquote') || trimmed.startsWith('<div') || trimmed.startsWith('<table')) {
          return trimmed;
        }
        return `<p>${trimmed}</p>`;
      }).join('\n');
    } else if (!html.startsWith('<')) {
      html = `<p>${html}</p>`;
    }

    // Clean empty paragraphs
    html = html.replace(/<p><\/p>/g, '');

    return html;
  }

  function attachCodeCopy(container) {
    container.querySelectorAll('.code-block-copy').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.code);
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(() => {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 2000);
        } catch {
          // fallback for older browsers
          const ta = document.createElement('textarea');
          ta.value = btn.dataset.code;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          btn.textContent = 'Copied!';
          setTimeout(() => btn.textContent = 'Copy', 2000);
        }
      });
    });
  }

  /* ─── Sessions ─── */
  function getDateLabel(date) {
    const now = new Date();
    const d = new Date(date);
    const diff = now - d;
    if (diff < 864e5) return 'Today';
    if (diff < 1728e5) return 'Yesterday';
    if (diff < 6048e5) return 'This Week';
    if (d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()) return 'This Month';
    return d.toLocaleDateString([], {month: 'long', year: 'numeric'});
  }

  async function createSession() {
    const data = await api.post('/sessions', {});
    return data.session_id;
  }

  async function ensureSession() {
    if (!currentSessionId) {
      currentSessionId = await createSession();
      updateBadge();
      loadSessions();
    }
    return currentSessionId;
  }

  function updateBadge() {
    el.sessionBadge.textContent = currentSessionId ? currentSessionId.slice(-8) : '';
  }

  async function loadSessions() {
    try {
      const sessions = await api.get('/sessions');
      renderSessions(sessions);
    } catch (e) {
      console.error('load sessions', e);
    }
  }

  function renderSessions(sessions) {
    const list = el.sessionsList;
    if (!sessions || sessions.length === 0) {
      list.innerHTML = '<div class="sessions-empty">No conversations yet</div>';
      return;
    }

    const groups = {};
    sessions.forEach(s => {
      const label = getDateLabel(s.last_active || s.created_at);
      (groups[label] = groups[label] || []).push(s);
    });

    const sortedGroups = ['Today', 'Yesterday', 'This Week', 'This Month'];
    let html = '';
    sortedGroups.forEach(label => {
      if (!groups[label]) return;
      html += `<div class="session-group-label">${label}</div>`;
      groups[label].forEach(s => {
        const active = s.session_id === currentSessionId ? ' active' : '';
        const preview = s.message_count > 0 ? `${s.message_count} msgs` : 'Empty';
        html += `<div class="session-item${active}" data-sid="${s.session_id}">
          <span class="session-item-text">${esc(preview)}</span>
          <span class="session-item-actions">
            <button class="btn-delete-session" data-sid="${s.session_id}" title="Delete">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M4 3V2a1 1 0 011-1h2a1 1 0 011 1v1M5 5.5v3M7 5.5v3M3 3l.5 7a1 1 0 001 1h3a1 1 0 001-1L9 3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </span>
        </div>`;
      });
    });

    // Add any remaining groups not in sortedGroups
    Object.keys(groups).forEach(label => {
      if (sortedGroups.includes(label)) return;
      html += `<div class="session-group-label">${esc(label)}</div>`;
      groups[label].forEach(s => {
        const active = s.session_id === currentSessionId ? ' active' : '';
        const preview = s.message_count > 0 ? `${s.message_count} msgs` : 'Empty';
        html += `<div class="session-item${active}" data-sid="${s.session_id}">
          <span class="session-item-text">${esc(preview)}</span>
          <span class="session-item-actions">
            <button class="btn-delete-session" data-sid="${s.session_id}" title="Delete">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M4 3V2a1 1 0 011-1h2a1 1 0 011 1v1M5 5.5v3M7 5.5v3M3 3l.5 7a1 1 0 001 1h3a1 1 0 001-1L9 3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </span>
        </div>`;
      });
    });

    list.innerHTML = html;

    list.querySelectorAll('.session-item').forEach(item => {
      item.addEventListener('click', e => {
        if (e.target.closest('.btn-delete-session')) return;
        switchSession(item.dataset.sid);
      });
    });
    list.querySelectorAll('.btn-delete-session').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        await deleteSession(btn.dataset.sid);
      });
    });
  }

  async function switchSession(sid) {
    if (isStreaming && abortStream) { abortStream(); abortStream = null; isStreaming = false; }
    currentSessionId = sid;
    updateBadge();
    loadSessions();
    await loadHistory(sid);
  }

  async function deleteSession(sid) {
    try {
      await api.del(`/sessions/${sid}`);
      if (currentSessionId === sid) {
        currentSessionId = null;
        el.welcome.classList.remove('hidden');
        el.msgContainer.querySelectorAll('.message').forEach(m => m.remove());
        updateBadge();
      }
      loadSessions();
    } catch (e) {
      console.error('delete session', e);
    }
  }

  async function loadHistory(sid) {
    try {
      const data = await api.post(`/sessions/${sid}/history`, {session_id: sid, limit: 100});
      renderHistory(data.messages);
    } catch (e) {
      if (e.message.includes('404')) {
        currentSessionId = null;
        updateBadge();
      }
    }
  }

  function renderHistory(messages) {
    const inner = getOrCreateInner();
    inner.querySelectorAll('.message').forEach(m => m.remove());
    el.welcome.classList.add('hidden');

    if (!messages || messages.length === 0) {
      el.welcome.classList.remove('hidden');
      return;
    }

    messages.forEach(msg => {
      if (msg.role === 'system') return;
      addMsg(msg.role === 'user' ? 'user' : 'bot', msg.content, null, msg.timestamp, false);
    });
    scrollBottom();
  }

  function getOrCreateInner() {
    let inner = el.msgContainer.querySelector('.messages-inner');
    if (!inner) {
      inner = document.createElement('div');
      inner.className = 'messages-inner';
      el.msgContainer.appendChild(inner);
    }
    return inner;
  }

  /* ─── Messages ─── */
  function getSourceMeta(s) {
    const m = s.metadata || {};
    return {
      doc: m.source || s.source || 'Document',
      heading: m.heading || '',
    };
  }

  function addMsg(role, text, sources, timestamp, animate = true) {
    el.welcome.classList.add('hidden');
    const inner = getOrCreateInner();

    const div = document.createElement('div');
    div.className = `message ${role}`;
    if (animate) div.style.animation = 'none';

    const avatar = role === 'user' ? 'U' : 'G';
    const time = timestamp ? fmtTime(new Date(timestamp)) : fmtTime(new Date());

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
      const json = esc(JSON.stringify(sources));
      sourcesHtml = `<div class="message-sources">
        ${sources.map((s, i) => {
          const meta = getSourceMeta(s);
          return `<button class="source-badge" data-all='${json}' data-idx="${i}">
            <span class="source-badge-num">${i+1}</span>
            <span class="source-badge-info">
              <span class="source-badge-heading">${esc(meta.heading || 'Untitled Section')}</span>
              <span class="source-badge-doc">${esc(meta.doc)}</span>
            </span>
            <span class="source-badge-score">${(s.score * 100).toFixed(0)}%</span>
          </button>`;
        }).join('')}
      </div>`;
    }

    div.innerHTML = `<div class="message-avatar">${avatar}</div>
      <div class="message-content">
        <div class="message-text">${role === 'user' ? esc(text) : renderMarkdown(text)}</div>
        ${sourcesHtml}
        <div class="message-time">${time}</div>
      </div>`;

    inner.appendChild(div);

    if (animate) {
      requestAnimationFrame(() => { div.style.animation = ''; });
    }

    // Source clicks
    div.querySelectorAll('.source-badge').forEach(btn => {
      btn.addEventListener('click', () => {
        showSources(JSON.parse(btn.dataset.all));
      });
    });

    // Copy buttons
    attachCodeCopy(div);

    scrollBottom();
  }

  function scrollBottom() {
    requestAnimationFrame(() => {
      el.msgContainer.scrollTop = el.msgContainer.scrollHeight;
    });
  }

  function showSources(sources) {
    el.sourceBody.innerHTML = sources.map((s, i) => {
      const meta = getSourceMeta(s);
      return `<div class="source-item">
        <div class="source-item-header">
          <span class="source-item-title">${esc(meta.heading || 'Untitled Section')}</span>
          <span class="source-item-score">${(s.score * 100).toFixed(0)}% match</span>
        </div>
        <div class="source-item-meta">
          <span>${esc(meta.doc)}</span>
        </div>
        <div class="source-item-content">${esc(s.content)}</div>
      </div>`;
    }).join('');
    el.sourceModal.classList.remove('hidden');
  }

  /* ─── Streaming ─── */
  async function sendMessage() {
    const text = el.input.value.trim();
    if (!text || isStreaming) return;

    el.input.value = '';
    el.sendBtn.disabled = true;
    autoResize();

    addMsg('user', text, null);

    try {
      await ensureSession();
      showTyping();

      const sid = currentSessionId;

      // Try streaming first
      const resp = await fetch(API_BASE + '/chat/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session_id: sid, message: text}),
      });

      if (!resp.ok) {
        // Fallback to non-streaming
        hideTyping();
        const data = await api.post('/chat', {session_id: sid, message: text});
        addMsg('bot', data.answer, data.sources, data.timestamp);
        loadSessions();
        return;
      }

      isStreaming = true;

      // Create bot message placeholder
      const inner = getOrCreateInner();
      el.welcome.classList.add('hidden');
      const botDiv = document.createElement('div');
      botDiv.className = 'message bot';
      botDiv.innerHTML = `<div class="message-avatar">G</div>
        <div class="message-content">
          <div class="message-text"></div>
          <div class="message-time">${fmtTime(new Date())}</div>
        </div>`;
      inner.appendChild(botDiv);
      scrollBottom();

      const textEl = botDiv.querySelector('.message-text');
      let sources = null;
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let aborted = false;

      abortStream = () => { aborted = true; reader.cancel(); };

      while (!aborted) {
        const {done, value} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            if (ev.type === 'token' && ev.content) {
              textEl.innerHTML = renderMarkdown(textEl.textContent + ev.content);
              attachCodeCopy(botDiv);
              scrollBottom();
            } else if (ev.type === 'sources' && ev.sources) {
              sources = ev.sources;
            } else if (ev.type === 'done') {
              // done
            }
          } catch {}
        }
      }

      if (sources && sources.length > 0) {
        const json = esc(JSON.stringify(sources));
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';
        sourcesDiv.innerHTML = sources.map((s, i) => {
          const meta = getSourceMeta(s);
          return `<button class="source-badge" data-all='${json}' data-idx="${i}">
            <span class="source-badge-num">${i+1}</span>
            <span class="source-badge-info">
              <span class="source-badge-heading">${esc(meta.heading || 'Untitled Section')}</span>
              <span class="source-badge-doc">${esc(meta.doc)}</span>
            </span>
            <span class="source-badge-score">${(s.score * 100).toFixed(0)}%</span>
          </button>`;
        }).join('');
        botDiv.querySelector('.message-content').appendChild(sourcesDiv);
        sourcesDiv.querySelectorAll('.source-badge').forEach(btn => {
          btn.addEventListener('click', () => showSources(JSON.parse(btn.dataset.all)));
        });
      }

      isStreaming = false;
      abortStream = null;
      hideTyping();
      loadSessions();
    } catch (e) {
      hideTyping();
      isStreaming = false;
      abortStream = null;
      if (!e.message.includes('cancel')) {
        // Try non-streaming fallback
        try {
          const data = await api.post('/chat', {session_id: currentSessionId, message: text});
          addMsg('bot', data.answer, data.sources, data.timestamp);
        } catch {
          addMsg('bot', 'I apologize, but I encountered an error. Please try again.');
        }
      }
      loadSessions();
    }
  }

  /* ─── Typing ─── */
  function showTyping() { el.typing.classList.remove('hidden'); }
  function hideTyping() { el.typing.classList.add('hidden'); }

  /* ─── Input ─── */
  function autoResize() {
    el.input.style.height = 'auto';
    el.input.style.height = Math.min(el.input.scrollHeight, 150) + 'px';
  }

  function handleInput() {
    el.sendBtn.disabled = !el.input.value.trim().length;
    autoResize();
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function newChat() {
    if (isStreaming && abortStream) { abortStream(); abortStream = null; isStreaming = false; }
    currentSessionId = null;
    updateBadge();
    const inner = el.msgContainer.querySelector('.messages-inner');
    if (inner) inner.innerHTML = '';
    el.welcome.classList.remove('hidden');
    el.input.focus();
    await ensureSession();
    loadSessions();
  }

  /* ─── Init ─── */
  function bindEvents() {
    el.sendBtn.addEventListener('click', sendMessage);
    el.input.addEventListener('input', handleInput);
    el.input.addEventListener('keydown', handleKeydown);
    el.newChatBtn.addEventListener('click', newChat);

    el.sidebarToggle.addEventListener('click', () => {
      el.sidebar.classList.toggle('collapsed');
    });

    el.sourceClose.addEventListener('click', () => el.sourceModal.classList.add('hidden'));
    el.sourceModal.querySelector('.source-modal-backdrop').addEventListener('click', () => el.sourceModal.classList.add('hidden'));
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') el.sourceModal.classList.add('hidden');
    });

    document.querySelectorAll('.quick-action').forEach(btn => {
      btn.addEventListener('click', () => {
        el.input.value = btn.dataset.query;
        handleInput();
        sendMessage();
      });
    });
  }

  async function init() {
    bindEvents();
    await ensureSession();
    loadSessions();
    el.input.focus();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
