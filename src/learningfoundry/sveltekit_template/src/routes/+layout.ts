// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// This app is a client-side SPA: it loads `curriculum.json` at runtime,
// persists progress in IndexedDB, and uses sql.js (WASM) — none of which
// can run during server-side rendering. Disable SSR so the prerender
// pass does not subscribe to the curriculum store and trigger a relative
// `fetch('/curriculum.json')` on the server.
export const ssr = false;
export const prerender = false;
