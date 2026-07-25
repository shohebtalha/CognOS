const API = "http://127.0.0.1:8420/events/ingest";

async function isEnabled() {
  const state = await chrome.storage.local.get({ enabled: true });
  return state.enabled;
}

async function send(event_type, payload, confidence = 1.0) {
  if (!(await isEnabled())) return;
  try {
    await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: "browser_extension",
        event_type,
        payload,
        confidence
      })
    });
  } catch {
    // Local assistant may be offline; fail quietly.
  }
}

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const tab = await chrome.tabs.get(tabId);
  if (tab.url) {
    send("browser_navigation", {
      url: tab.url,
      title: tab.title || "",
      active: true
    });
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    send("browser_navigation", {
      url: tab.url,
      title: tab.title || "",
      active: tab.active
    });
  }
});

chrome.downloads.onCreated.addListener((download) => {
  send("download_started", {
    url: download.url,
    filename: download.filename || "",
    mime: download.mime || "",
    danger: download.danger || "unknown",
    total_bytes: download.totalBytes || 0
  });
});
