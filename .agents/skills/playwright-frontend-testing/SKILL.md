---
name: playwright-frontend-testing
description: "Use when writing or running end-to-end / visual / performance checks for the Project Baymax React frontend with Playwright — driving login→chat/dashboard flows, role toggle, document upload, slot booking, and especially verifying the 3D background stays smooth on mobile and laptop viewports before a demo. NOT for Python/pytest backend tests or unit-testing pure functions."
metadata:
  author: baymax-project
  version: "1.0.0"
---

# Playwright Frontend Testing

## Status: not installed yet
Playwright is **not** in `frontend/package.json`. To set it up (Windows / npm):
```bash
cd frontend
npm i -D @playwright/test
npx playwright install          # downloads browser binaries (Chromium/WebKit/Firefox)
```
Put tests in `frontend/tests/` and config in `frontend/playwright.config.js`.
Run with `npx playwright test` (add `--headed` / `--ui` while developing).

## Why it fits this project
- **Mobile before the workshop:** the biggest risk is the R3F background stuttering or draining
  battery on phones. Playwright device emulation lets you drive real flows at phone viewports and
  sample frame cadence — catch jank before demoing.
- **Testing tool, not a content/instruction skill** → no supply-chain/prompt concern.

## Principles
1. **Auto-start the app via `webServer`** so tests don't depend on a manually-running dev server.
   Point it at Vite (port 3000). Note the frontend proxies `/api` to the backend on :8000, so the
   **FastAPI backend must be running** for chat/booking flows (or mock `/api/*` with
   `page.route`).
2. **Use `projects` for desktop + mobile** (e.g. Desktop Chrome + Pixel 5 + iPhone 13) to exercise
   both form factors the spec calls out.
3. **Web-first assertions, no fixed sleeps.** Use `await expect(locator).toBeVisible()` etc.;
   never `waitForTimeout` to "let it settle."
4. **Frame-cadence sampling for the 3D background.** Playwright can't read GPU FPS, but sampling
   `requestAnimationFrame` deltas in-page is a reliable proxy for main-thread jank/stalls (see
   snippet). Assert median frame time stays roughly ≤ ~20 ms (≈50 fps) and that there are no
   multi-hundred-ms stalls.
5. **Stabilise visual snapshots.** The animated canvas will make full-page screenshots flaky —
   `mask` the `<canvas>` (or assert on DOM/UI regions only) when using `toHaveScreenshot`.
6. **Mock external cost where possible.** For pure UI/flow tests, `page.route('**/api/**', …)` to
   return canned responses — faster, deterministic, and avoids hitting the live Supabase / NVIDIA
   during CI.

## Quick reference

**`frontend/playwright.config.js`:**
```js
import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  testDir: './tests',
  webServer: { command: 'npm run dev', url: 'http://localhost:3000', reuseExistingServer: true },
  use: { baseURL: 'http://localhost:3000' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile',  use: { ...devices['Pixel 5'] } },
  ],
})
```

**Frame-cadence probe (jank guard for the background):**
```js
test('background stays smooth', async ({ page }) => {
  await page.goto('/')
  const frames = await page.evaluate(() => new Promise((resolve) => {
    const deltas = []; let last = performance.now(), n = 0
    const tick = (t) => { deltas.push(t - last); last = t
      if (++n < 120) requestAnimationFrame(tick); else resolve(deltas) }
    requestAnimationFrame(tick)
  }))
  const sorted = [...frames].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)]
  expect(median).toBeLessThan(20)                 // ~50fps main-thread cadence
  expect(Math.max(...frames)).toBeLessThan(250)   // no long stall
})
```

**Happy-path flow (login → chat), API mocked:**
```js
test('patient can log in and chat', async ({ page }) => {
  await page.route('**/api/initialize_session', r => r.fulfill({ json: { greeting: 'Hello Chester', chronic_conditions: [] } }))
  await page.route('**/api/chat', r => r.fulfill({ json: { response: 'Hi!', available_slots: [] } }))
  await page.goto('/')
  await page.getByPlaceholder(/P001/i).fill('P001')
  await page.getByRole('button', { name: /enter|start|continue/i }).click()
  await expect(page.getByText(/Hello Chester/i)).toBeVisible()
})
```

## Verify
- `npx playwright test` (from `frontend/`) — all projects green.
- Run the mobile project specifically: `npx playwright test --project=mobile`.
- Selectors above are illustrative — confirm against the real DOM in `App.jsx` and adjust
  roles/placeholders.
