/**
 * Extracts the real design tokens from https://iwarranty.ai/ using a headless
 * Chromium instance. Writes JSON + reference screenshots to e2e/iwarranty/.
 *
 * Usage: node scripts/extract-iwarranty.mjs
 */
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const OUT = path.resolve('e2e/iwarranty')
fs.mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({
  executablePath:
    process.env.BROWSER_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})

const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('https://iwarranty.ai/', { waitUntil: 'networkidle', timeout: 90_000 })
await page.waitForTimeout(4000)

await page.screenshot({ path: path.join(OUT, 'desktop-full.png'), fullPage: true })
await page.screenshot({ path: path.join(OUT, 'desktop-fold.png') })

// Trigger scroll reveals before inspecting animations.
for (let y = 0; y < 6000; y += 700) {
  await page.evaluate((top) => window.scrollTo(0, top), y)
  await page.waitForTimeout(180)
}
await page.waitForTimeout(1200)
await page.evaluate(() => window.scrollTo(0, 0))
await page.waitForTimeout(600)

const data = await page.evaluate(() => {
  const isVisible = (el) => {
    if (el.closest('#seo-snapshot')) return false
    const rect = el.getBoundingClientRect()
    const s = getComputedStyle(el)
    return (
      rect.width > 1 &&
      rect.height > 1 &&
      s.visibility !== 'hidden' &&
      s.display !== 'none' &&
      Number(s.opacity) > 0.01
    )
  }

  const styleOf = (el) => {
    if (!el) return null
    const s = getComputedStyle(el)
    return {
      tag: el.tagName.toLowerCase(),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 140),
      className: typeof el.className === 'string' ? el.className.slice(0, 260) : '',
      fontFamily: s.fontFamily,
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
      lineHeight: s.lineHeight,
      letterSpacing: s.letterSpacing,
      textTransform: s.textTransform,
      color: s.color,
      backgroundColor: s.backgroundColor,
      backgroundImage: s.backgroundImage,
      borderColor: s.borderColor,
      borderWidth: s.borderWidth,
      borderRadius: s.borderRadius,
      boxShadow: s.boxShadow,
      padding: s.padding,
      transition: s.transition,
      animation: s.animation,
      maxWidth: s.maxWidth,
      display: s.display,
      gap: s.gap,
    }
  }

  const all = [...document.querySelectorAll('body *')].filter(isVisible)
  const counter = (values, limit = 25) => {
    const map = new Map()
    for (const value of values) if (value) map.set(value, (map.get(value) || 0) + 1)
    return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit)
  }

  const headings = ['h1', 'h2', 'h3', 'h4'].map((tag) =>
    all.filter((el) => el.tagName === tag).slice(0, 5).map(styleOf),
  )

  const hero = all.find((el) => el.tagName === 'H1')
  const heroSection = hero?.closest('section') || hero?.parentElement?.parentElement

  const buttons = all
    .filter((el) => el.tagName === 'BUTTON' || (el.tagName === 'A' && /rounded/.test(el.className)))
    .slice(0, 20)
    .map(styleOf)

  const navLinks = all
    .filter((el) => el.closest('header') && el.tagName === 'A')
    .slice(0, 12)
    .map(styleOf)

  const cards = all
    .filter(
      (el) =>
        /rounded/.test(String(el.className)) &&
        (Number.parseFloat(getComputedStyle(el).borderWidth) > 0 ||
          getComputedStyle(el).boxShadow !== 'none'),
    )
    .slice(0, 20)
    .map(styleOf)

  const sections = all
    .filter((el) => el.tagName === 'SECTION' || el.tagName === 'FOOTER')
    .slice(0, 24)
    .map(styleOf)

  const cssVars = {}
  const keyframes = []
  const fontFaces = []
  for (const sheet of document.styleSheets) {
    let rules
    try {
      rules = sheet.cssRules
    } catch {
      continue
    }
    for (const rule of rules) {
      if (rule.style && rule.selectorText === ':root') {
        for (const name of rule.style) {
          if (name.startsWith('--')) cssVars[name] = rule.style.getPropertyValue(name).trim()
        }
      }
      if (rule.type === CSSRule.KEYFRAMES_RULE) {
        keyframes.push({ name: rule.name, css: rule.cssText.slice(0, 500) })
      }
      if (rule.type === CSSRule.FONT_FACE_RULE) fontFaces.push(rule.cssText)
    }
  }

  const animations = document.getAnimations().slice(0, 60).map((animation) => {
    const timing = animation.effect?.getComputedTiming?.() || {}
    const target = animation.effect?.target
    return {
      animationName: animation.animationName || animation.id || '',
      duration: timing.duration,
      delay: timing.delay,
      iterations: timing.iterations,
      easing: timing.easing,
      playState: animation.playState,
      target: target?.tagName + (target?.className ? `.${String(target.className).split(' ')[0]}` : ''),
    }
  })

  const transitioned = all
    .map((el) => getComputedStyle(el).transition)
    .filter((value) => value && value !== 'all 0s ease 0s' && !value.startsWith('all 0s'))

  const marquees = all
    .filter((el) => /marquee|animate|scroll/i.test(String(el.className)))
    .slice(0, 15)
    .map(styleOf)

  return {
    title: document.title,
    fonts: [...document.fonts].map((f) => ({ family: f.family, weight: f.weight, status: f.status })),
    body: styleOf(document.body),
    hero: styleOf(hero),
    heroSection: styleOf(heroSection),
    headings,
    paragraphs: all.filter((el) => el.tagName === 'P').slice(0, 10).map(styleOf),
    navLinks,
    buttons,
    cards,
    sections,
    fontFamilies: counter(all.map((el) => getComputedStyle(el).fontFamily), 10),
    fontSizes: counter(all.map((el) => getComputedStyle(el).fontSize), 30),
    colors: counter(all.map((el) => getComputedStyle(el).color), 20),
    backgrounds: counter(
      all.map((el) => {
        const s = getComputedStyle(el)
        return s.backgroundImage !== 'none' ? `IMG ${s.backgroundImage}` : s.backgroundColor
      }),
      25,
    ),
    borders: counter(all.map((el) => getComputedStyle(el).borderColor), 15),
    radii: counter(all.map((el) => getComputedStyle(el).borderRadius), 20),
    shadows: counter(all.map((el) => getComputedStyle(el).boxShadow), 10),
    transitions: counter(transitioned, 15),
    cssVars,
    keyframes,
    fontFaces,
    animations,
    marquees,
    scrollHeight: document.documentElement.scrollHeight,
  }
})

fs.writeFileSync(path.join(OUT, 'tokens.json'), JSON.stringify(data, null, 2))
await browser.close()
console.log(`Saved ${path.join(OUT, 'tokens.json')}`)
console.log('hero:', JSON.stringify(data.hero, null, 2))
console.log('heroSection:', JSON.stringify(data.heroSection, null, 2))
