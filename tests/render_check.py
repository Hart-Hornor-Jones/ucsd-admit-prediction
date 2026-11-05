"""Render check for index.html.

Opens the page in headless Chromium with Playwright, exercises every menu,
button, preset, checkbox, chart interaction, the school finder and the four
export formats on both charts, and fails on any console error, page error,
failed request or HTTP error response.

Run from anywhere:  python tests/render_check.py
Requires:           pip install playwright && python -m playwright install chromium
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"

problems = []   # anything that fails the run
steps = []      # what was exercised, for the report

MODEL_OK = "window.UCSDPRED && window.UCSDPRED.FA && window.UCSDPRED.FA.ok && window.UCSDPRED.FB.ok"


def note(msg):
    steps.append(msg)
    print("  " + msg)


def fail(msg):
    problems.append(msg)
    print("  FAIL: " + msg)


def wait_model(page):
    """Wait for the two charts to hold a fitted model and for the page to be idle."""
    try:
        page.wait_for_function(MODEL_OK, timeout=30000)
    except Exception as e:
        state = page.evaluate("window.UCSDPRED ? [window.UCSDPRED.FA.ok, window.UCSDPRED.FB.ok, window.UCSDPRED.FA.why, window.UCSDPRED.FB.why, JSON.stringify(window.UCSDPRED.state, (k, v) => v instanceof Set ? [...v] : v)] : 'no UCSDPRED'")
        raise RuntimeError(f"charts did not reach a fitted model: {state}") from e


def pick_menu(page, button_id, menu_id, label_contains=None, index=None):
    """Open a dropdown menu by its button and click one of its options."""
    page.click("#" + button_id)
    menu = page.locator("#" + menu_id)
    if not menu.evaluate("m => m.classList.contains('open')"):
        fail(f"menu {menu_id} did not open after clicking #{button_id}")
    options = menu.locator("button")
    if index is not None:
        target = options.nth(index)
    else:
        target = options.filter(has_text=label_contains).first
    text = target.inner_text().split("\n")[0]
    target.click()
    if menu.evaluate("m => m.classList.contains('open')"):
        fail(f"menu {menu_id} stayed open after choosing '{text}'")
    return text


def check_page_state(page, where):
    """After an interaction the charts, stats and tables must hold finite numbers."""
    ok = page.evaluate(MODEL_OK)
    if not ok:
        why = page.evaluate("window.UCSDPRED ? [window.UCSDPRED.FA.why, window.UCSDPRED.FB.why] : null")
        fail(f"{where}: a chart has no fitted model ({why})")
        return
    body = page.evaluate("document.body.innerText")
    if "NaN" in body or "undefined" in body or "Infinity" in body:
        fail(f"{where}: page text contains NaN/undefined/Infinity")
    for which in ("A", "B"):
        dots = page.locator(f"#panel{which} circle.dot").count()
        if dots == 0:
            fail(f"{where}: chart {which} shows no dots")
        stats = page.locator(f"#stats{which}").inner_text()
        if "R²" not in stats:
            fail(f"{where}: chart {which} stats text lacks R² ('{stats[:60]}')")
    if page.locator("#grptable table tr").count() < 9:
        fail(f"{where}: group table has too few rows")
    if page.locator("#coeftable table tr").count() < 3:
        fail(f"{where}: coefficient table has too few rows")


def run_export(page, which, kind):
    """Click an export option and wait for the file download it produces."""
    page.click(f"#btnExp{which}")
    btn = page.locator(f"#menuExp{which} button[data-x='{kind}']")
    try:
        with page.expect_download(timeout=30000) as dl:
            btn.click()
        name = dl.value.suggested_filename
        note_txt = page.locator(f"#xnote{which}").inner_text()
        note(f"export {kind} on chart {which}: downloaded {name} ({note_txt})")
    except Exception as e:  # timeout or browser refusal
        note_txt = page.locator(f"#xnote{which}").inner_text()
        fail(f"export {kind} on chart {which} produced no download: {type(e).__name__} (note: '{note_txt}')")


def main():
    if not PAGE.exists():
        print(f"missing {PAGE}")
        return 2
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # browser not installed: say so instead of failing obscurely
            print("could not launch Chromium; run 'python -m playwright install chromium' first")
            print(str(e).splitlines()[0])
            return 2
        ctx = browser.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
        page = ctx.new_page()
        page.on("console", lambda m: fail(f"console {m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: fail(f"page error: {e}"))
        page.on("requestfailed", lambda r: fail(f"request failed: {r.url} ({r.failure})"))
        page.on("response", lambda r: fail(f"HTTP {r.status} for {r.url}") if r.status >= 400 else None)

        print("opening", PAGE.as_uri())
        page.goto(PAGE.as_uri(), wait_until="load")
        wait_model(page)
        note("page loaded; default model fitted on both charts")
        check_page_state(page, "initial load")

        # ---- top-bar menus: every option of every menu ----
        for btn, menu, key in (("btnView", "menuView", "view"), ("btnModel", "menuModel", "model"),
                               ("btnColor", "menuColor", "color"), ("btnFit", "menuFit", "fitOn")):
            n = page.locator(f"#{menu} button").count()
            for i in range(n):
                text = pick_menu(page, btn, menu, index=i)
                wait_model(page)
                check_page_state(page, f"{btn} -> {text}")
                note(f"menu {btn}: chose '{text}' (state.{key} = {page.evaluate(f'window.UCSDPRED.state.{key}')})")
        # leave the page fitted to all schools so the geography indicators are enabled
        pick_menu(page, "btnFit", "menuFit", label_contains="All schools")
        wait_model(page)
        if page.evaluate("window.UCSDPRED.state.fitOn") != "all":
            fail("Fit model to -> All schools did not take effect")

        # ---- era menus on both charts ----
        for which in ("A", "B"):
            n = page.locator(f"#menuEra{which} button").count()
            for i in range(n):
                text = pick_menu(page, f"btnEra{which}", f"menuEra{which}", index=i)
                wait_model(page)
                check_page_state(page, f"era {which} -> {text}")
                note(f"chart {which}: period '{text}'")
        pick_menu(page, "btnEraA", "menuEraA", index=1)
        pick_menu(page, "btnEraB", "menuEraB", index=2)
        wait_model(page)

        # ---- presets ----
        presets = page.locator("#presets button")
        for i in range(presets.count()):
            text = presets.nth(i).inner_text()
            presets.nth(i).click()
            wait_model(page)
            check_page_state(page, f"preset '{text}'")
            note(f"preset '{text}': {page.evaluate('window.UCSDPRED.state.sel.size')} variables selected")
        presets.nth(0).click()  # back to GPA only
        wait_model(page)

        # ---- every variable checkbox: toggle each twice, from a two-variable baseline ----
        presets.nth(2).click()  # GPA + other campuses, so unchecking any one box never empties the model
        wait_model(page)
        boxes = page.locator("#varlist label.v input")
        skipped = []
        for i in range(boxes.count()):
            box = boxes.nth(i)
            v = box.get_attribute("data-v")
            if box.is_disabled():
                skipped.append(v)
                continue
            was = box.is_checked()
            for turn in (1, 2):
                box.click()
                wait_model(page)
                now = box.is_checked()
                expected = (not was) if turn == 1 else was
                if now != expected:
                    fail(f"checkbox {v}: click {turn} left it {'checked' if now else 'unchecked'}")
                check_page_state(page, f"checkbox {v} {'on' if now else 'off'}")
        note(f"toggled {boxes.count() - len(skipped)} variable checkboxes on and off" + (f"; disabled: {skipped}" if skipped else ""))
        # the two mutually exclusive geography indicators, together
        page.locator("#varlist input[data-v='local']").click()
        wait_model(page)
        page.locator("#varlist input[data-v='groups']").click()
        wait_model(page)
        if page.locator("#varlist input[data-v='local']").is_checked():
            fail("checking 'groups' did not clear 'local'")
        check_page_state(page, "groups indicator")
        note("geography indicators: 'local' then 'groups' (mutually exclusive)")
        # the curvature box pulls in GPA
        page.locator("#varlist input[data-v='gpacurve']").click()
        wait_model(page)
        if not page.locator("#varlist input[data-v='appgpa']").is_checked():
            fail("checking 'gpacurve' did not select 'appgpa'")
        check_page_state(page, "gpa curvature")
        # with fitOn=out the indicators must be disabled again and dropped from the model
        pick_menu(page, "btnFit", "menuFit", index=0)
        wait_model(page)
        if not page.locator("#varlist input[data-v='groups']").is_disabled():
            fail("'groups' checkbox not disabled when fitting outside San Diego/Imperial")
        check_page_state(page, "back to out-of-sample fit")
        note("fit switched back to schools outside San Diego and Imperial counties")

        # ---- chart interactions: hover, click a dot, zoom, reset, double-click ----
        for which in ("A", "B"):
            dot = page.locator(f"#panel{which} circle.dot").last
            dot.hover()
            if page.locator("#tip").evaluate("t => getComputedStyle(t).display") == "none":
                fail(f"tooltip did not appear when hovering a dot on chart {which}")
            dot.click()
            name = page.locator("#schoolbox h4").inner_text()
            if not name:
                fail(f"clicking a dot on chart {which} did not fill the school box")
            note(f"chart {which}: clicked dot -> school box shows '{name}'")
            svg = page.locator(f"#panel{which} svg.plot")
            box = svg.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.wheel(0, -400)
            page.wait_for_timeout(300)
            reset = page.locator(f"#panel{which} button.zreset")
            if not reset.is_visible():
                fail(f"reset-zoom button not shown after wheel zoom on chart {which}")
            reset.click()
            page.wait_for_timeout(400)
            if reset.is_visible():
                fail(f"reset-zoom button still shown after reset on chart {which}")
            page.mouse.wheel(0, -400)
            page.wait_for_timeout(300)
            svg.dblclick(position={"x": box["width"] / 2, "y": box["height"] / 2})
            page.wait_for_timeout(400)
            note(f"chart {which}: wheel zoom, reset button, double-click reset")
        check_page_state(page, "after zooming")

        # ---- find a school ----
        options = page.locator("#schoollist option")
        if options.count() == 0:
            fail("school datalist is empty")
        else:
            target = options.nth(options.count() // 2).get_attribute("value")
            page.fill("#find", target)
            page.dispatch_event("#find", "change")
            shown = page.locator("#schoolbox h4").inner_text()
            if not shown or shown not in target:
                fail(f"finding '{target}' showed '{shown}' in the school box")
            note(f"find box: '{target}' -> school box '{shown}'")
        # the definitions disclosure
        page.click("details.defs summary")
        if not page.evaluate("document.querySelector('details.defs').open"):
            fail("definitions <details> did not open on click")
        note("definitions disclosure opened")

        # ---- exports: four formats on each chart, one chart per view ----
        for which, view_index in (("A", 1), ("B", 0)):
            pick_menu(page, "btnView", "menuView", index=view_index)
            wait_model(page)
            for kind in ("csv", "svg", "png2", "png4"):
                run_export(page, which, kind)

        # ---- narrower layouts ----
        for w in (1000, 700, 390):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(200)
            check_page_state(page, f"viewport {w}px")
            note(f"viewport {w}px wide renders")

        browser.close()

    print()
    print(f"{len(steps)} interactions exercised")
    if problems:
        print(f"{len(problems)} problem(s):")
        for p_ in problems:
            print("  - " + p_)
        return 1
    print("render check passed: no console errors, page errors, failed requests or HTTP errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
