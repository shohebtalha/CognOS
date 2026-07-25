# CognOS Connectors

Connectors send user-approved application context to the local CognOS API at `http://127.0.0.1:8420`.

## Browser Connector

Supports Chromium browsers such as Chrome and Edge.

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable Developer Mode.
3. Click **Load unpacked**.
4. Select `C:\Users\ShOheb\CognOS\connectors\browser-extension`.

It sends:
- active tab URL and title
- completed navigation events
- download metadata

## VS Code Connector

From `C:\Users\ShOheb\CognOS\connectors\vscode-extension`:

```powershell
npm install
npm run compile
```

Then press `F5` in VS Code to launch an extension development host, or package it:

```powershell
npm run package
```

It sends:
- active file metadata
- warnings and errors from VS Code diagnostics

## Privacy

All connector traffic stays local. Disable connectors from their own settings or browser popup when you do not want that source observed.
