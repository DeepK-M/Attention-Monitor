// background.js — Service Worker
// Keeps the extension alive and re-injects content.js when tabs reload

// ── Re-inject content script when a Meet tab finishes loading ──
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (
    changeInfo.status === 'complete' &&
    tab.url &&
    tab.url.startsWith('https://meet.google.com/')
  ) {
    chrome.scripting.executeScript({
      target : { tabId },
      files  : ['content.js']
    }).then(() => {
      console.log('[AttentionMonitor BG] content.js injected into tab', tabId);
    }).catch(err => {
      // Tab may have been closed or navigated away — ignore
      console.warn('[AttentionMonitor BG] inject failed:', err.message);
    });
  }
});

// ── Keep service worker alive with a periodic alarm ───────────
chrome.runtime.onInstalled.addListener(() => {
  if (chrome.alarms?.create) {
    chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
  } else {
    console.warn('[AttentionMonitor BG] alarms API unavailable; skipping keepAlive alarm');
  }
  console.log('[AttentionMonitor BG] Extension installed / updated');
});

if (chrome.alarms?.onAlarm) {
  chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === 'keepAlive') {
      // No-op — just wakes the service worker
    }
  });
}

// ── Relay messages between popup (dashboard) and content script ─
// The popup cannot always reach the content script directly because
// the service worker context may differ. This relay fixes that.
function isMeetTabUrl(url) {
  return typeof url === 'string' && url.startsWith('https://meet.google.com/');
}

function resolveTargetTab(msg, sender, callback) {
  if (Number.isInteger(msg?.tabId)) {
    chrome.tabs.get(msg.tabId, tab => {
      if (chrome.runtime.lastError) {
        callback(null);
        return;
      }
      callback(tab || null);
    });
    return;
  }

  chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
    callback(tabs?.[0] || null);
  });
}

function sendToContent(tabId, payload, sendResponse) {
  chrome.tabs.sendMessage(tabId, payload, response => {
    if (!chrome.runtime.lastError) {
      sendResponse(response || {});
      return;
    }

    const firstError = chrome.runtime.lastError.message || 'Could not deliver message';
    chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] }, () => {
      if (chrome.runtime.lastError) {
        sendResponse({ error: chrome.runtime.lastError.message || firstError });
        return;
      }

      chrome.tabs.sendMessage(tabId, payload, retryResponse => {
        if (chrome.runtime.lastError) {
          sendResponse({ error: chrome.runtime.lastError.message || firstError });
          return;
        }
        sendResponse(retryResponse || {});
      });
    });
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.target === 'content') {
    resolveTargetTab(msg, sender, tab => {
      if (!tab?.id) {
        sendResponse({ error: 'No active tab' });
        return;
      }
      if (!isMeetTabUrl(tab.url)) {
        sendResponse({ error: 'Active tab is not a Google Meet page' });
        return;
      }
      sendToContent(tab.id, msg.payload || {}, sendResponse);
    });
    return true; // keep channel open for async response
  }
});