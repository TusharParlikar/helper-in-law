"""Record the real app (Streamlit on 127.0.0.1:8501, API on :8000) in a headless browser.

uv run --no-project --with playwright python scripts/film/record.py OUT_DIR
Writes OUT_DIR/screen.webm and OUT_DIR/marks.json: for each moment, seconds from the start of
the recording and the on-screen box of the element that matters then (for zooms and highlights).
"""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = "http://127.0.0.1:8501"
W, H = 1600, 1000
SCENARIO = (
    "My client was arrested at night by the police and kept in custody for two days. "
    "He was not told why he was arrested and was not allowed to call a lawyer."
)


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    marks: dict[str, dict[str, object]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(out),
            record_video_size={"width": W, "height": H},
        )
        t0 = time.monotonic()
        page = ctx.new_page()

        def mark(name: str, selector: str | None = None) -> None:
            box = None
            if selector:
                loc = page.locator(selector).filter(visible=True).first
                b = loc.bounding_box()
                if b:
                    box = [round(b["x"]), round(b["y"]), round(b["width"]), round(b["height"])]
            marks[name] = {"t": round(time.monotonic() - t0, 2), "box": box}

        def glide(dy: int, seconds: float) -> None:
            steps = int(seconds * 30)
            for _ in range(steps):
                page.mouse.wheel(0, dy / steps)
                page.wait_for_timeout(1000 / 30)

        page.goto(APP, wait_until="commit")
        page.get_by_role("button", name="Analyse").wait_for(timeout=60000)
        page.wait_for_timeout(1500)
        mark("home")
        page.wait_for_timeout(3000)

        box = page.locator("textarea").first
        box.click()
        mark("typing")
        box.press_sequentially(SCENARIO, delay=28)
        page.wait_for_timeout(600)
        mark("typed", "div[data-testid=stForm]")
        page.get_by_role("button", name="Analyse").click()
        page.get_by_text("Constitutional provisions").wait_for(timeout=120000)
        page.wait_for_timeout(700)
        mark("results")
        page.mouse.move(W / 2, H / 2)
        glide(420, 2.5)
        page.wait_for_timeout(2500)
        mark("provisions", ".card.prov")
        glide(650, 4.0)
        page.wait_for_timeout(2500)
        mark("analysis", ".card:has(.point)")
        glide(700, 4.0)
        page.wait_for_timeout(3000)
        mark("judgments", ".card.case")

        page.mouse.wheel(0, -20000)
        page.wait_for_timeout(800)
        page.get_by_role("tab", name="Constitution lookup").click()
        page.wait_for_timeout(1200)
        mark("lookup")
        field = page.get_by_placeholder("Article number, e.g. 21, 21A, 300A")
        field.click()
        field.press_sequentially("21", delay=180)
        page.get_by_role("button", name="Look up").click()
        page.get_by_text("Article 21. Protection of life and personal liberty").wait_for(
            timeout=60000
        )
        page.wait_for_timeout(4500)
        mark("article", ".card.prov")

        page.get_by_role("tab", name="Research").click()
        page.wait_for_timeout(800)
        box = page.locator("textarea").first
        box.click()
        box.press("Control+a")
        box.press_sequentially("What is the recipe for butter chicken?", delay=40)
        page.get_by_role("button", name="Analyse").click()
        page.get_by_text("Nothing in the indexed sources").wait_for(timeout=60000)
        page.mouse.wheel(0, 380)
        page.wait_for_timeout(4000)
        mark("notfound", ".card.empty")

        video = page.video
        ctx.close()
        browser.close()
        if video:
            Path(video.path()).replace(out / "screen.webm")
    (out / "marks.json").write_text(json.dumps(marks, indent=1))
    print(json.dumps(marks))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
