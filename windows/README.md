# Windows / Store QA candidate

This branch adds a **Windows 10/11 desktop shell for the existing offline HTML application** under docs/. No accounting calculations are changed.

## Build

A Windows runner with .NET 8 SDK and Windows 10 SDK runs the workflow **Windows MSIX QA (unsigned)**. The workflow publishes the WinForms/WebView2 host for win-x64, bundles docs/ inside App/, generates placeholder QA-only PNG assets, builds a **non-signed** MSIX with MakeAppx, unpacks it for structural inspection, and uploads the MSIX and SHA-256 text.

## Release safeguards

- The manifest Identity `TsuhaTools.InternalAccounting.QA` and Publisher `CN=UnsignedQA` are **QA placeholders only**, not Microsoft Partner Center identity values.
- This unsigned MSIX is **not an installable Store submission** until the correct Partner Center Identity/Publisher are verified and the store ingestion requirements are met.
- UI state is stored in the user's LocalAppData WebView2 profile, not in the read-only installation folder. HTML does not call a local Flask server.
- Requires Microsoft Edge WebView2 Runtime on the target Windows machine.
- The existing JavaScript imports JSON files and retains WIP data in the local WebView2 profile. The application does not ship users' private JSON.
- Never include credentials, local input data, debug traces, personal authentication tokens or other private artifacts in GitHub Action upload.
- QA items remaining: examine 1024x768 / 1280x720 layout, import/save/restart, export/links, Windows 10/11 startup, WebView2 Runtime availability, and Partner Center Store certification validation.
