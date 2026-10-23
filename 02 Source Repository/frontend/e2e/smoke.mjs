import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const BASE = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const BROWSER =
  process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const SHOTS = path.resolve('e2e/screenshots')

fs.mkdirSync(SHOTS, { recursive: true })

const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ` — ${detail}` : ''}`)
}

const browser = await chromium.launch({ executablePath: BROWSER, headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 950 } })
const consoleErrors = []
page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push(message.text())
})
page.on('pageerror', (error) => consoleErrors.push(String(error)))

const shot = (name) => page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true })

const login = async (email, password) => {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.getByLabel('Email').fill(email)
  await page.getByLabel(/^Password/).fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByRole('heading', { name: /^Welcome back,/ }).waitFor({ timeout: 20000 })
}

const signOut = async () => {
  await page.getByTitle('Sign out').click()
  await page.getByRole('heading', { name: 'Welcome back' }).waitFor()
}

try {
  // ---------------------------------------------------------------- #
  // 1. Login screen
  // ---------------------------------------------------------------- #
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  check('login page renders', await page.getByRole('heading', { name: 'Welcome back' }).isVisible())
  check('demo credentials available', await page.getByRole('button', { name: 'Customer' }).isVisible())
  await shot('01-login')

  // ---------------------------------------------------------------- #
  // 2. Customer dashboard (empty state is valid for this account)
  // ---------------------------------------------------------------- #
  await login('customer@assurex.com', 'customer123')
  await page.getByText('Total claims').first().waitFor()
  check('customer dashboard stats', await page.getByText('Covered products').first().isVisible())
  await shot('02-customer-dashboard')

  // ---------------------------------------------------------------- #
  // 3. Full claim intake wizard (inline product registration)
  // ---------------------------------------------------------------- #
  await page.getByRole('link', { name: 'New claim' }).click()
  await page.getByRole('heading', { name: 'Submit a warranty claim' }).waitFor()

  await page.getByRole('button', { name: 'New product' }).click()
  await page.getByLabel(/Product name/).fill('E2E Smoke Laptop')
  await page.getByLabel(/^Serial number/).fill(`E2E-${Date.now()}`)
  await page.getByLabel(/Purchase date/).fill('2025-06-01')
  await page.getByLabel(/Purchase price/).fill('1200')
  await page.getByLabel(/Warranty months/).fill('24')
  await shot('03-claim-product')

  await page.getByRole('button', { name: 'Continue' }).click()
  await page.getByRole('heading', { name: 'Incident details' }).waitFor()
  await page.getByLabel(/Fault occurrence date/).fill('2026-09-01')
  await page.getByLabel(/Description/).fill('E2E validation: display does not power on after normal use.')
  await shot('04-claim-incident')

  await page.getByRole('button', { name: 'Continue' }).click()
  await page.getByText('Attach from vault').waitFor()
  await shot('05-claim-evidence')

  await page.getByRole('button', { name: 'Continue' }).click()
  await page.getByText('Review & submit').waitFor()
  await shot('06-claim-review')

  await page.getByRole('button', { name: 'Submit for adjudication' }).click()
  await page.getByText('Dual-model adjudication').waitFor({ timeout: 60000 })
  check('claim submitted through wizard', page.url().includes('/claims/CLM-'))
  check('dossier comparison rendered', await page.getByText('Policy rule evaluation').isVisible())
  check('summary card rendered', await page.locator('img[alt^="Summary card"]').first().isVisible())
  await shot('07-claim-dossier')

  // ---------------------------------------------------------------- #
  // 4. Customer pages
  // ---------------------------------------------------------------- #
  await page.getByRole('link', { name: 'Claims', exact: true }).click()
  await page.getByRole('heading', { name: 'Claims', exact: true }).waitFor()
  await page.waitForFunction(
    () => document.querySelectorAll('table tbody tr').length > 0 || document.body.innerText.includes('No claims found'),
  )
  check('claims list populated', (await page.locator('table tbody tr').count()) > 0)

  await page.getByRole('link', { name: 'Products', exact: true }).click()
  await page.getByRole('heading', { name: 'Products & warranties' }).waitFor()
  await page.waitForFunction(
    () => document.querySelectorAll('a[href^="/products/PRD-"]').length > 0 || document.body.innerText.includes('No products found'),
  )
  const cards = page.locator('a[href^="/products/PRD-"]')
  check('products list populated', (await cards.count()) > 0, `${await cards.count()} cards`)
  await shot('08-products')

  await cards.first().click()
  await page.getByText('Coverage policy').waitFor()
  check('product detail renders', await page.getByText('Product information').isVisible())
  await shot('09-product-detail')

  await page.getByRole('link', { name: 'Documents', exact: true }).click()
  await page.getByRole('heading', { name: 'Document vault' }).waitFor()
  check('document vault renders', await page.getByText('Uploaded evidence').isVisible())
  await shot('10-documents')

  await page.getByRole('link', { name: 'Warranty Alerts' }).click()
  await page.getByRole('heading', { name: 'Warranty alerts' }).waitFor()
  check('alerts page renders', await page.getByText('Expiring soon').first().isVisible())

  await page.getByRole('link', { name: 'Repairs' }).click()
  await page.getByRole('heading', { name: 'Repair records' }).waitFor()
  check('repairs page renders', await page.getByText('All repairs').isVisible())

  await page.getByTitle('Profile').click()
  await page.getByRole('heading', { name: 'Profile & security' }).waitFor()
  check('profile page renders', await page.getByLabel(/Full name/).isVisible())
  await shot('11-profile')

  await signOut()

  // ---------------------------------------------------------------- #
  // 5. Reviewer queue + decision modal
  // ---------------------------------------------------------------- #
  await login('reviewer@assurex.com', 'reviewer123')
  await page.getByRole('link', { name: 'Review Queue' }).click().catch(async () => {
    await page.locator('aside').first().getByRole('link', { name: 'Review Queue' }).click()
  })
  await page.getByRole('heading', { name: 'Review queue' }).waitFor()
  await page.getByRole('button', { name: 'Decide' }).first().waitFor()
  check('review queue populated', (await page.getByRole('button', { name: 'Decide' }).count()) > 0)
  await shot('12-review-queue')

  await page.getByRole('button', { name: 'Decide' }).first().click()
  await page.getByText('Reviewer decision').waitFor()
  check('override modal opens', await page.getByLabel(/Reviewer comments/).isVisible())
  await page.getByRole('button', { name: 'Cancel' }).click()

  await signOut()

  // ---------------------------------------------------------------- #
  // 6. Admin: analytics, policies, audit, settings
  // ---------------------------------------------------------------- #
  await login('admin@assurex.com', 'admin123')
  await page.getByRole('link', { name: 'Administration' }).click()
  await page.getByRole('heading', { name: 'System control' }).waitFor()
  await page.getByText('Decision distribution').waitFor()
  check('admin analytics render', await page.getByText('Decision distribution').isVisible())
  await shot('13-admin-overview')

  await page.getByRole('button', { name: 'Policies' }).click()
  await page.locator('textarea').waitFor()
  check('policy editor renders JSON', (await page.locator('textarea').inputValue()).includes('covered_faults'))
  await shot('14-admin-policies')

  await page.getByRole('button', { name: 'Audit log' }).click()
  await page.getByText('Audit log', { exact: true }).first().waitFor()
  await page.waitForFunction(
    () => document.querySelectorAll('table tbody tr').length > 0 || document.body.innerText.includes('No audit events'),
  )
  check('audit trail populated', (await page.locator('table tbody tr').count()) > 0)
  await shot('15-admin-audit')

  await page.getByRole('button', { name: 'Settings' }).click()
  await page.getByText('Runtime thresholds').waitFor()
  check('settings form renders', await page.getByLabel(/Uncertainty threshold/).isVisible())
  await shot('16-admin-settings')

  // ---------------------------------------------------------------- #
  // 7. Responsive layout
  // ---------------------------------------------------------------- #
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })
  await page.getByRole('heading', { name: /^Welcome back,/ }).waitFor()
  check('mobile menu button', await page.getByRole('button', { name: 'Open navigation' }).isVisible())
  await page.getByRole('button', { name: 'Open navigation' }).click()
  check(
    'mobile drawer opens',
    await page.locator('aside').last().getByRole('link', { name: 'Products' }).isVisible(),
  )
  await shot('17-mobile')

  // ---------------------------------------------------------------- #
  // 8. 404
  // ---------------------------------------------------------------- #
  await page.goto(`${BASE}/does-not-exist`, { waitUntil: 'networkidle' })
  check('404 page renders', await page.getByText('Page not found').isVisible())
} catch (error) {
  check('e2e run completed', false, error.message)
  await shot('99-failure')
} finally {
  if (consoleErrors.length) {
    console.log('\nConsole/page errors:')
    consoleErrors.forEach((message) => console.log(` - ${message}`))
  }
  check('no console errors', consoleErrors.length === 0, `${consoleErrors.length} error(s)`)
  await browser.close()
}

const failed = results.filter((result) => !result.ok)
console.log(`\n${results.length - failed.length}/${results.length} checks passed`)
if (failed.length) process.exit(1)
