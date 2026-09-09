import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.maximize_window()

context = {
    "name": os.getenv('NAME'),
    "email": os.getenv('LINKEDIN_EMAIL'),
    "phone": os.getenv('Phone_Number'),
    "location": os.getenv('Residency'),
    "currently employed": os.getenv('Employed_Currently'),
    "Need a Visa": os.getenv('Need_Visa'),
    "Years of Coding": os.getenv('YearsOfCoding'),
    "Experience": os.getenv('EXPERIENCE'),
    "Languages Known": os.getenv('LanguagesKnown'),
    "Coding Languages Known": os.getenv('CodingLanguagesKnown')
}

# --- Login ---
driver.get("https://app.joinhandshake.com/login?ref=app-domain")
username = os.getenv("HANDSHAKE_EMAIL")
password = os.getenv("HANDSHAKE_PASSWORD")

# Step 1: Enter email
emailBox = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @name='email' or @id='email']"))
)
emailBox.send_keys(username)
nextButton = driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
nextButton.click()

# Step 2: Enter password
passwordBox = WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
)
passwordBox.send_keys(password)
signIn = driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
signIn.click()

# Wait for login to complete
WebDriverWait(driver, 30).until(EC.url_contains("app.joinhandshake.com"))
time.sleep(4)

# --- Navigate to job search and click Full-time filter ---
driver.get("https://app.joinhandshake.com/job-search")
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Jobs List']"))
)
time.sleep(3)

# Debug: print all clickable elements that mention "full" or "time" or filter-like text
print("Looking for Full-time filter button...")
all_clickables = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'full-time') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'full time')]")
print(f"  Found {len(all_clickables)} elements with 'full-time' text:")
for i, el in enumerate(all_clickables):
    print(f"    [{i}] tag={el.tag_name}, text='{el.text[:50]}', displayed={el.is_displayed()}, classes='{el.get_attribute('class') or ''}'")

# Try multiple strategies to click the Full-time filter
clicked = False

# Strategy 1: Find by exact visible text in any element and click it
for el in all_clickables:
    try:
        if el.is_displayed() and "full-time" in el.text.lower() and len(el.text.strip()) < 30:
            print(f"  Strategy 1: Clicking '{el.text.strip()}' ({el.tag_name})")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", el)
            clicked = True
            time.sleep(3)
            break
    except:
        continue

# Strategy 2: Use JavaScript to find and click by innerText
if not clicked:
    print("  Strategy 2: Using JS to find and click...")
    clicked = driver.execute_script("""
        var elements = document.querySelectorAll('button, a, div[role="button"], span[role="button"], [class*="filter"], [class*="chip"], [class*="pill"], [class*="tag"]');
        for (var el of elements) {
            if (el.innerText && el.innerText.trim().toLowerCase().includes('full-time') && el.offsetParent !== null) {
                console.log('Found: ' + el.tagName + ' - ' + el.innerText.trim());
                el.click();
                return true;
            }
        }
        return false;
    """)
    if clicked:
        print("  Strategy 2: Clicked via JS!")
        time.sleep(3)

# Strategy 3: Simulate mouse click via ActionChains
if not clicked:
    from selenium.webdriver.common.action_chains import ActionChains
    print("  Strategy 3: Trying ActionChains click...")
    for el in all_clickables:
        try:
            if el.is_displayed() and "full-time" in el.text.lower() and len(el.text.strip()) < 30:
                ActionChains(driver).move_to_element(el).pause(0.5).click(el).perform()
                clicked = True
                print(f"  Strategy 3: Clicked '{el.text.strip()}'!")
                time.sleep(3)
                break
        except:
            continue

if not clicked:
    print("  WARNING: Could not click Full-time filter with any strategy!")

# Verify: check current URL for filter params
current_url = driver.current_url
print(f"  Current URL after filter attempt: {current_url}")

# Wait for filtered results
try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Jobs List']"))
    )
except:
    pass
time.sleep(2)

# --- Job Search Loop (stays on filtered page, uses next button) ---
page = 1
applied_count = 0
skipped_count = 0

while True:
    print(f"\n=== Page {page} ===")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Jobs List']"))
        )
    except TimeoutException:
        print("Job list didn't load. Stopping.")
        break

    time.sleep(3)

    # Collect unique job IDs from links on this page
    links = driver.find_elements(By.CSS_SELECTOR, "[aria-label='Jobs List'] a[href*='/job-search/']")
    job_ids = []
    for link in links:
        href = link.get_attribute("href") or ""
        match = re.search(r'/job-search/(\d+)', href)
        if match and match.group(1) not in job_ids:
            job_ids.append(match.group(1))

    print(f"Found {len(job_ids)} jobs")
    if not job_ids:
        print("No jobs on this page. Stopping.")
        break

    for idx, job_id in enumerate(job_ids):
        try:
            # Click the job card in the list to load its details
            job_link = driver.find_element(
                By.CSS_SELECTOR, f"[aria-label='Jobs List'] a[href*='/job-search/{job_id}']"
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_link)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", job_link)
            time.sleep(2)

            # Check if the job detail pane says "Internship" — skip if so
            try:
                detail_pane = driver.find_element(By.CSS_SELECTOR,
                    "[aria-label='Job Preview'], [class*='job-detail'], [class*='preview']"
                )
                detail_text = detail_pane.text
                if re.search(r'\bInternship\b', detail_text):
                    print(f"  [{idx+1}/{len(job_ids)}] Internship. Skipping.")
                    skipped_count += 1
                    continue
            except:
                pass

            # Find a visible Apply button (not "Apply externally", not inside a dialog)
            apply_buttons = driver.find_elements(
                By.XPATH, "//button[@type='button'][normalize-space(.)='Apply']"
            )
            apply_btn = None
            for btn in apply_buttons:
                try:
                    if not btn.is_displayed():
                        continue
                    btn.find_element(By.XPATH, "./ancestor::dialog | ./ancestor::*[@role='dialog']")
                except NoSuchElementException:
                    apply_btn = btn
                    break
                except:
                    continue

            if not apply_btn:
                # Also skip "Apply externally" jobs
                ext_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Apply externally')]")
                if ext_buttons:
                    print(f"  [{idx+1}/{len(job_ids)}] External application. Skipping.")
                else:
                    print(f"  [{idx+1}/{len(job_ids)}] No Apply button. Skipping.")
                skipped_count += 1
                continue

            apply_btn.click()
            time.sleep(2)

            # Wait for the Submit Application button to appear in the dialog
            try:
                submit_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//button[normalize-space(.)='Submit Application']")
                    )
                )
            except TimeoutException:
                print(f"  [{idx+1}/{len(job_ids)}] No Submit button. Skipping.")
                try:
                    driver.find_element(By.XPATH, "//button[contains(., 'Cancel application')]").click()
                except:
                    pass
                skipped_count += 1
                time.sleep(1)
                continue

            # Check the dialog for cover letter requirement
            try:
                dialog = submit_btn.find_element(
                    By.XPATH, "./ancestor::dialog | ./ancestor::*[@role='dialog']"
                )
                dialog_text = dialog.text.lower()
            except:
                dialog_text = ""

            if "cover letter" in dialog_text:
                print(f"  [{idx+1}/{len(job_ids)}] Requires cover letter. Skipping.")
                try:
                    driver.find_element(By.XPATH, "//button[contains(., 'Cancel application')]").click()
                except:
                    pass
                skipped_count += 1
                time.sleep(1)
                continue

            # Submit the application
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[normalize-space(.)='Submit Application']")
                )).click()
                applied_count += 1
                print(f"  [{idx+1}/{len(job_ids)}] Applied! (Total: {applied_count})")
                time.sleep(2)
            except:
                print(f"  [{idx+1}/{len(job_ids)}] Submit not clickable. Skipping.")
                try:
                    driver.find_element(By.XPATH, "//button[contains(., 'Cancel application')]").click()
                except:
                    pass
                skipped_count += 1
                time.sleep(1)

        except Exception as e:
            print(f"  [{idx+1}/{len(job_ids)}] Error: {e}")
            skipped_count += 1
            try:
                driver.find_element(By.XPATH, "//button[contains(., 'Cancel application')]").click()
            except:
                pass
            time.sleep(1)

    # Click the next page button instead of loading a new URL (preserves filters)
    try:
        next_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[@aria-label='Next' or contains(@aria-label, 'next')]"
                " | //a[@aria-label='Next' or contains(@aria-label, 'next')]"
            ))
        )
        driver.execute_script("arguments[0].click();", next_btn)
        page += 1
        time.sleep(3)
    except TimeoutException:
        print("No next page button. Done with all pages.")
        break

print(f"\nDone! Applied: {applied_count}, Skipped: {skipped_count}")
driver.quit()
