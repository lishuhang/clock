#!/usr/bin/env python3
"""Screenshot round1.2 HTML to PNG."""
import os, asyncio
from playwright.async_api import async_playwright

ROUND = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round1.2"
IDS = ["img1", "img2", "img3", "img4", "img5", "img6"]

async def shot(browser, html_name, png_name):
    page = await browser.new_page(viewport={"width": 1200, "height": 1600}, device_scale_factor=2)
    url = "file://" + os.path.join(ROUND, html_name)
    print(f"  open {html_name}")
    await page.goto(url, wait_until="networkidle", timeout=60000)
    try:
        await page.evaluate("() => document.fonts.ready")
    except:
        pass
    await page.wait_for_timeout(800)
    await page.evaluate("""() => {
        const b = document.getElementById('yz-selfcheck-banner');
        if (b) b.style.display = 'none';
    }""")
    try:
        result = await page.evaluate("() => (typeof yzSelfCheck === 'function') ? yzSelfCheck() : 'no fn'")
        print(f"    selfcheck: {result}")
    except Exception as e:
        print(f"    selfcheck error: {e}")
    cc = await page.query_selector(".chart-container")
    if cc:
        box = await cc.bounding_box()
        print(f"    container size: {box['width']:.0f} x {box['height']:.0f}  ratio(h/w)={box['height']/box['width']:.2f}")
        await cc.screenshot(path=os.path.join(ROUND, png_name))
        print(f"    -> {png_name}")
    else:
        await page.screenshot(path=os.path.join(ROUND, png_name), full_page=True)
        print(f"    -> {png_name} (fallback full page)")
    await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for img_id in IDS:
            await shot(browser, f"{img_id}-styled.html", f"{img_id}-styled.png")
            await shot(browser, f"{img_id}.html", f"{img_id}.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
