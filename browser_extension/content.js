/**
 * Samir AI Companion — Content Script
 * استخراج نصوص الصفحة والكتابة في الحقول نيابة عن سمير
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // 1. استخراج النص المحدد أو نص الصفحة بالكامل
  if (request.action === 'get_page_text') {
    const selection = window.getSelection()?.toString().trim();
    if (selection) {
      sendResponse({
        text: selection,
        isSelection: true,
        title: document.title,
        url: window.location.href,
      });
      return true;
    }

    // استخراج النص المرئي الأساسي
    const bodyClone = document.body.cloneNode(true);
    // إزالة السكربتات والأنماط
    const toRemove = bodyClone.querySelectorAll('script, style, noscript, nav, footer');
    toRemove.forEach((el) => el.remove());

    const fullText = (bodyClone.innerText || bodyClone.textContent || '').replace(/\s+/g, ' ').trim();
    sendResponse({
      text: fullText.substring(0, 4000), // أول 4000 حرف
      isSelection: false,
      title: document.title,
      url: window.location.href,
    });
    return true;
  }

  // 2. الكتابة في الحقل النشط
  if (request.action === 'type_into_active_input') {
    const activeEl = document.activeElement;
    if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.isContentEditable)) {
      if (activeEl.isContentEditable) {
        activeEl.innerText = request.text;
      } else {
        activeEl.value = request.text;
      }
      activeEl.dispatchEvent(new Event('input', { bubbles: true }));
      activeEl.dispatchEvent(new Event('change', { bubbles: true }));
      sendResponse({ success: true, message: 'تمت الكتابة في الحقل بنجاح.' });
    } else {
      sendResponse({ success: false, message: 'لم يتم تحديد حقل إدخال نشط.' });
    }
    return true;
  }
});
