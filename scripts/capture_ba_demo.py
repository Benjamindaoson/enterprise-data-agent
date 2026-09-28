"""Capture a real-data BA Agent product proof with Playwright."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def capture(base_url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    video_dir = output_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1720, "height": 1080},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()

        await page.goto(f"{base_url.rstrip('/')}/ba", wait_until="networkidle")
        await page.wait_for_function(
            """() => {
              const text=document.querySelector('#datasetStatus')?.textContent || '';
              return text.includes('complete-journey') && text.includes('1,469,307');
            }""",
            timeout=30_000,
        )
        await page.screenshot(
            path=str(output_dir / "ba-agent-before-run.png"),
            full_page=True,
        )

        await page.click("#runBtn")
        await page.wait_for_selector("#report:not(.hidden)", timeout=60_000)
        await page.wait_for_function(
            """() =>
              document.querySelectorAll('.chart-card').length >= 4 &&
              Number(document.querySelector('#insightCount')?.textContent || '0') >= 4
            """,
            timeout=60_000,
        )
        await page.wait_for_timeout(800)
        await page.screenshot(
            path=str(output_dir / "ba-agent-real-data.png"),
            full_page=True,
        )

        async with page.expect_download() as download_info:
            await page.click("#exportReport")
        download = await download_info.value
        await download.save_as(str(output_dir / "ba-agent-executive-report.html"))

        async with page.expect_download() as pdf_download_info:
            await page.click("#exportPdf")
        pdf_download = await pdf_download_info.value
        await pdf_download.save_as(str(output_dir / "ba-agent-executive-report.pdf"))

        status_text = await page.locator("#datasetStatus").inner_text()
        hero_text = await page.locator("#hero").inner_text()
        (output_dir / "demo-proof.txt").write_text(
            f"dataset={status_text}\nhero={hero_text}\n",
            encoding="utf-8",
        )

        video = page.video
        await page.close()
        await context.tracing.stop(path=str(output_dir / "ba-agent-trace.zip"))
        await context.close()
        if video is not None:
            video_path = Path(await video.path())
            if video_path.exists():
                video_path.replace(output_dir / "ba-agent-real-data.webm")
        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/ba-demo"))
    args = parser.parse_args()
    asyncio.run(capture(args.base_url, args.output_dir))


if __name__ == "__main__":
    main()
