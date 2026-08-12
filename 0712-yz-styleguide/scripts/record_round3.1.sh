#!/bin/bash
# Record round3.1 animated HTMLs to MP4
ROUND3="/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/round3.1"
FRAMES_BASE="/tmp/r3.1_frames"

record_one() {
    local HTML="$1"
    local NAME=$(basename "$HTML" -styled.html)
    local MP4="$ROUND3/$NAME.mp4"
    local FRAMES="$FRAMES_BASE/$NAME"
    
    mkdir -p "$FRAMES"
    rm -f "$FRAMES"/*
    
    python3 -c "
import asyncio, os
from playwright.async_api import async_playwright
async def go():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        page=await b.new_page(viewport={'width':1080,'height':1080})
        await page.goto('file://$HTML', wait_until='domcontentloaded')
        await page.evaluate('() => document.fonts.ready')
        await page.wait_for_timeout(300)
        await page.screenshot(path='$FRAMES/frame_0000.png')
        await page.evaluate('() => document.body.classList.add(\"play\")')
        for i in range(1, 105):
            await page.screenshot(path='$FRAMES/frame_{:04d}.png'.format(i))
            await asyncio.sleep(1/30)
        await b.close()
asyncio.run(go())
" 2>/dev/null
    
    local N=$(ls "$FRAMES"/frame_*.png 2>/dev/null | wc -l)
    if [ "$N" -lt 105 ]; then
        echo "[$NAME] FAIL: only $N frames"
        return
    fi
    
    ffmpeg -y -framerate 30 -i "$FRAMES/frame_%04d.png" -c:v libx264 -pix_fmt yuv420p -preset ultrafast "$FRAMES/entrance.mp4" 2>/dev/null
    ffmpeg -y -loop 1 -i "$FRAMES/frame_0104.png" -t 3 -r 30 -c:v libx264 -pix_fmt yuv420p -preset ultrafast "$FRAMES/static.mp4" 2>/dev/null
    ffmpeg -y -i "$FRAMES/entrance.mp4" -vf reverse -c:v libx264 -pix_fmt yuv420p -preset ultrafast "$FRAMES/exit.mp4" 2>/dev/null
    echo "file '$FRAMES/entrance.mp4'" > "$FRAMES/concat.txt"
    echo "file '$FRAMES/static.mp4'" >> "$FRAMES/concat.txt"
    echo "file '$FRAMES/exit.mp4'" >> "$FRAMES/concat.txt"
    ffmpeg -y -f concat -safe 0 -i "$FRAMES/concat.txt" -c:v libx264 -pix_fmt yuv420p -preset ultrafast "$MP4" 2>/dev/null
    
    if [ -f "$MP4" ] && [ $(stat -c%s "$MP4") -gt 50000 ]; then
        echo "[$NAME] OK $(stat -c%s "$MP4" | numfmt --to=iec)"
    else
        echo "[$NAME] FAIL"
    fi
    rm -rf "$FRAMES"
}

for HTML in "$ROUND3"/*-styled.html; do
    record_one "$HTML"
done
echo "ALL DONE: $(ls "$ROUND3"/*.mp4 2>/dev/null | wc -l) MP4s"
