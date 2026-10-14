"""End-to-end browser smoke test.

Prereqs: backend + frontend running, demo user seeded (python -m scripts.seed_demo),
`pip install playwright && python -m playwright install chromium`.
Run: python e2e/smoke_test.py   (screenshots are written to e2e/screenshots/)
"""
import re, sys, time
from playwright.sync_api import sync_playwright, expect
import os
BASE=os.environ.get("BMC_URL","http://127.0.0.1:5173")
SAMPLES=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","backend","sample_data")
S=os.path.join(os.path.dirname(os.path.abspath(__file__)),"screenshots"); os.makedirs(S, exist_ok=True)
errors=[]
with sync_playwright() as p:
    b=p.chromium.launch()
    pg=b.new_page(viewport={"width":1366,"height":900})
    pg.on("console", lambda m: errors.append(m.text) if m.type=="error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE); pg.wait_for_url("**/login")
    pg.screenshot(path=f"{S}/01_login.png")
    pg.click("text=Create an account")
    email=f"e2e{int(time.time())}@example.com"
    pg.fill("#name","Riya Sharma"); pg.fill("#email",email); pg.fill("#password","Password123"); pg.fill("#confirm","Password123")
    pg.check("input[type=checkbox]")
    pg.click("button:has-text('Create account')")
    pg.wait_for_url("**/profile")
    expect(pg.get_by_text("Welcome to BookMyCare!")).to_be_visible()
    pg.fill("#dob","1998-06-10"); pg.select_option("#sex","male"); pg.fill("#h","172"); pg.fill("#w","68")
    pg.select_option("#act","moderate")
    pg.fill("#allergies","Sulfa drugs")
    pg.click("button:has-text('Save profile')")
    expect(pg.get_by_text("Profile saved.")).to_be_visible()
    pg.screenshot(path=f"{S}/02_profile.png", full_page=True)
    # history
    pg.click("nav >> text=Medical history")
    pg.click("button:has-text('Add entry')")
    pg.fill("#title","Childhood asthma"); pg.check("text=Ongoing / current")
    pg.click("form button:has-text('Add entry')")
    expect(pg.get_by_text("Childhood asthma")).to_be_visible()
    # upload report
    pg.click("nav >> text=Reports & images")
    pg.set_input_files("[data-testid=file-input]", f"{SAMPLES}/synthetic_fever_cbc.pdf")
    pg.click("form button:has-text('Upload')")
    expect(pg.get_by_text(re.compile(r"lab value\(s\) recognised"))).to_be_visible(timeout=15000)
    # upload image
    pg.click("role=tab[name='Medical image']")
    pg.set_input_files("[data-testid=file-input]", f"{SAMPLES}/synthetic_grayscale_image.png")
    pg.click("form button:has-text('Upload')")
    expect(pg.get_by_text("Image uploaded. Quality checks complete.")).to_be_visible(timeout=15000)
    pg.screenshot(path=f"{S}/03_reports.png", full_page=True)
    pg.click("text=View details"); pg.wait_for_url("**/reports/*")
    expect(pg.get_by_text("Image quality checks")).to_be_visible()
    # report detail of pdf
    pg.click("text=All files"); pg.click("text=synthetic_fever_cbc")
    expect(pg.get_by_text("Recognised lab values")).to_be_visible()
    pg.screenshot(path=f"{S}/04_report_detail.png", full_page=True)
    # analysis
    pg.click("nav >> text=New analysis")
    pg.fill("[aria-label='Search symptoms']","joint"); pg.click("button:has-text('+ Joint pain')")
    pg.fill("#desc","High fever for 4 days with severe headache, pain behind the eyes and body aches. No cough.")
    pg.fill("#dur","4"); pg.select_option("#sev","moderate")
    pg.click("text=Fever CBC (synthetic)") if pg.get_by_text("Fever CBC (synthetic)").count() else pg.locator("li:has-text('labs') input[type=checkbox]").first.check()
    pg.locator("li:has-text('synthetic_grayscale_image') input[type=checkbox]").first.check()
    pg.screenshot(path=f"{S}/05_new_analysis.png", full_page=True)
    pg.click("button:has-text('Run analysis')")
    pg.wait_for_url(re.compile(r".*/analyses/\d+$"))
    expect(pg.get_by_test_id("urgency-banner")).to_be_visible()
    expect(pg.get_by_role("heading", name="Dengue fever")).to_be_visible()
    expect(pg.get_by_text("Mock AI").first).to_be_visible()
    expect(pg.get_by_text("Why this was suggested")).to_be_visible()
    pg.screenshot(path=f"{S}/06_result.png", full_page=True)
    # library
    pg.click("nav >> text=Health library")
    pg.click("button:has-text('stroke signs')")
    expect(pg.get_by_text(re.compile("Stroke signs", re.I)).first).to_be_visible()
    pg.screenshot(path=f"{S}/07_library.png", full_page=True)
    # dashboard
    pg.click("nav >> text=Dashboard")
    expect(pg.get_by_text("Hello, Riya")).to_be_visible()
    pg.screenshot(path=f"{S}/08_dashboard.png", full_page=True)
    # mobile
    m=b.new_page(viewport={"width":390,"height":844})
    m.goto(BASE+"/login")
    m.fill("#email","demo@bookmycare.dev"); m.fill("#password","DemoPass123"); m.click("button:has-text('Sign in')")
    expect(m.get_by_text("Hello, Demo")).to_be_visible()
    m.screenshot(path=f"{S}/09_mobile_dash.png", full_page=True)
    m.click("[aria-label='Open menu']"); m.screenshot(path=f"{S}/10_mobile_menu.png")
    m.click("role=dialog >> text=New analysis")
    m.fill("#desc","I have chest pain, sweating and I am short of breath"); m.select_option("#sev","severe")
    m.click("button:has-text('Run analysis')")
    m.wait_for_url(re.compile(r".*/analyses/\d+$"))
    expect(m.get_by_text("Seek emergency medical care now.").first).to_be_visible()
    m.screenshot(path=f"{S}/11_mobile_emergency.png", full_page=True)
    # horizontal overflow check
    ow=m.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    print("mobile horizontal overflow:", ow)
    # logout
    m.click("[aria-label='Open menu']"); m.click("role=dialog >> text=Sign out"); m.wait_for_url("**/login")
    b.close()
print("console errors:", errors)
print("E2E PASSED")
