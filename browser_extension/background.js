/**
 * Samir AI Companion — Background Service Worker
 * فحص حالة سمير في الخلفية وتحديث الشارة الحية (Badge) على شريط المتصفح
 */

const HEALTH_URL = 'http://localhost:8000/health';
const CHAT_URL = 'http://localhost:8000/api/v1/chat/message';

// فحص الحالة وتحديث الشارة
async function checkSamirStatus() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);

    const res = await fetch(HEALTH_URL, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      chrome.action.setBadgeText({ text: 'ON' });
      chrome.action.setBadgeBackgroundColor({ color: '#10b981' }); // أخضر زمردي
      chrome.action.setTitle({ title: 'سمير الذكي: متصل وشغال 🟢' });
      chrome.storage.local.set({ samirOnline: true, lastCheck: Date.now() });
      return true;
    }
  } catch (err) {
    // السيرفر متوقف أو غير متصل
  }

  chrome.action.setBadgeText({ text: 'OFF' });
  chrome.action.setBadgeBackgroundColor({ color: '#ef4444' }); // أحمر
  chrome.action.setTitle({ title: 'سمير الذكي: متوقف 🔴' });
  chrome.storage.local.set({ samirOnline: false, lastCheck: Date.now() });
  return false;
}

// ضبط منبه الفحص الدوري كل 10 ثوانٍ
chrome.alarms.create('checkSamirHealth', { periodInMinutes: 0.15 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'checkSamirHealth') {
    checkSamirStatus();
  }
});

// فحص فوري عند تشغيل المتصفح أو تثبيت الإضافة
chrome.runtime.onInstalled.addListener(() => {
  checkSamirStatus();
});

chrome.runtime.onStartup.addListener(() => {
  checkSamirStatus();
});

// الاستماع لرسائل الـ Popup أو الـ Content Script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'check_status_now') {
    checkSamirStatus().then((online) => sendResponse({ online }));
    return true;
  }

  if (request.action === 'ask_samir') {
    fetch(CHAT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: request.message,
        session_id: 'browser_extension_session',
        provider: 'auto',
        synthesize_voice: false,
      }),
    })
      .then((r) => r.json())
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // async response
  }
});
