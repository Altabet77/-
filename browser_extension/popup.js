/**
 * Samir AI Companion — Popup Logic
 */

const statusBadge = document.getElementById('status-badge');
const statusText = document.getElementById('status-text');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const responseArea = document.getElementById('response-area');
const btnTranslate = document.getElementById('btn-translate-page');
const btnSummarize = document.getElementById('btn-summarize-page');

async function updateStatus() {
  try {
    const res = await fetch('http://localhost:8000/health', { method: 'GET' });
    if (res.ok) {
      statusBadge.className = 'status-badge online';
      statusText.innerText = 'شغال ومتصل 🟢';
      return true;
    }
  } catch (e) {}

  statusBadge.className = 'status-badge offline';
  statusText.innerText = 'متوقف 🔴';
  return false;
}

function showResponse(text) {
  responseArea.style.display = 'block';
  responseArea.innerText = text;
}

async function askSamir(prompt) {
  showResponse('يفكر سمير ويحلل المهمة...');
  try {
    const res = await fetch('http://localhost:8000/api/v1/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: prompt,
        session_id: 'extension_' + Date.now(),
        provider: 'auto',
        synthesize_voice: false,
      }),
    });
    const data = await res.json();
    const modelTag = data.routing_reason ? `[${data.routing_reason}]\n\n` : '';
    showResponse(modelTag + (data.reply || 'تم التنفيذ يا غالي.'));
  } catch (err) {
    showResponse('تعذر الاتصال بخادم سمير. تأكد من تشغيل الخادم.');
  }
}

sendBtn.addEventListener('click', () => {
  const txt = chatInput.value.trim();
  if (txt) {
    chatInput.value = '';
    askSamir(txt);
  }
});

chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    sendBtn.click();
  }
});

// زر "ترجم ما أمامي"
btnTranslate.addEventListener('click', async () => {
  showResponse('جاري استخراج نصوص الصفحة الحالية لترجمتها...');
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return;

  chrome.tabs.sendMessage(tab.id, { action: 'get_page_text' }, (resp) => {
    if (chrome.runtime.lastError || !resp || !resp.text) {
      askSamir('ترجملي الكلام اللي قدامي على الشاشة الآن.');
      return;
    }
    const label = resp.isSelection ? 'النص المحدد في الصفحة' : `الصفحة (${resp.title})`;
    askSamir(`ترجملي هذا المحتوى المعروض أمامي في ${label} للغة العربية بدقة وأسلوب واضح:\n\n${resp.text}`);
  });
});

// زر "لخص الصفحة"
btnSummarize.addEventListener('click', async () => {
  showResponse('جاري قراءة الصفحة لتلخيصها...');
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return;

  chrome.tabs.sendMessage(tab.id, { action: 'get_page_text' }, (resp) => {
    if (chrome.runtime.lastError || !resp || !resp.text) {
      showResponse('تعذر قراءة محتوى الصفحة الحالية.');
      return;
    }
    askSamir(`لخص لي محتوى هذه الصفحة (${resp.title}) في نقاط رئيسية مركزة ومفيدة:\n\n${resp.text}`);
  });
});

// فحص الحالة عند فتح الـ Popup
updateStatus();
