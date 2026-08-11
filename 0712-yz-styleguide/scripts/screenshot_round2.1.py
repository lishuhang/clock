#!/usr/bin/env python3
"""Screenshot round2.1 HTML to PNG."""
import os, asyncio, glob
from playwright.async_api import async_playwright

ROUND = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round2.1"

async def main():
    htmls = sorted(glob.glob(os.path.join(ROUND, "*-styled.html")))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for html_path in htmls:
            name = os.path.basename(html_path).replace(".html", ".png")
            page = await browser.new_page(viewport={"width": 1200, "height": 1200}, device_scale_factor=1)
            await page.goto("file://" + html_path, wait_until="networkidle", timeout=60000)
            try: await page.evaluate("() => document.fonts.ready")
            except: pass
            await page.wait_for_timeout(800)
            await page.evaluate("() => { const b = document.getElementById('yz-selfcheck-banner'); if (b) b.style.display = 'none'; }")
            try:
                result = await page.evaluate("() => (typeof yzSelfCheck1x1 === 'function') ? yzSelfCheck1x1() : 'no fn'")
            except:
                result = "no fn"
            cc = await page.query_selector(".chart-container-1x1")
            if cc:
                box = await cc.bounding_box()
                await cc.screenshot(path=os.path.join(ROUND, name))
                print(f"  {name}  size={box['width']:.0f}x{box['height']:.0f}  selfcheck={result}")
            await page.close()
        await browser.close()

asyncio.run(main())
