const checkbox = document.getElementById("enabled");

chrome.storage.local.get({ enabled: true }).then((state) => {
  checkbox.checked = state.enabled;
});

checkbox.addEventListener("change", () => {
  chrome.storage.local.set({ enabled: checkbox.checked });
});
