import os
import time
import shutil
import re
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException

# ---------------- Chrome Driver Setup ---------------- #
def _setup_driver():
    chrome_path = None

    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]

    for path in possible_paths:
        if os.path.exists(path):
            chrome_path = path
            break

    if not chrome_path:
        chrome_path = shutil.which("chrome") or shutil.which("chrome.exe")

    if not chrome_path:
        print("❌ ERROR: Chrome browser not found. Please install Google Chrome.")
        return None

    print(f"✅ Chrome found at: {chrome_path}")

    options = webdriver.ChromeOptions()
    options.binary_location = chrome_path
    options.add_argument("--user-data-dir=" + os.path.expanduser("~") + "\\AppData\\Local\\Google\\Chrome\\User Data")
    options.add_argument("--profile-directory=Default")
    options.add_experimental_option("detach", True)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")

    try:
        service = Service(shutil.which("chromedriver") or "./chromedriver.exe")
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://web.whatsapp.com")
        print("🌐 WhatsApp Web launched — please wait for chats to load...")
        time.sleep(10)
        return driver
    except WebDriverException as e:
        print("❌ WebDriver failed to start:", e)
        print("TIP: Make sure ChromeDriver matches your Chrome version.")
        return None


# ---------------- Auto-Reply Logic ---------------- #
FOLLOWUP_MESSAGE = (
    "Awesome! 🎓✨\n\n"
    "Here’s what I’ll need to help you with your NRF bursary application:\n\n"
    "📄 Please send:\n"
    "1️⃣ Certified copy of your ID\n"
    "2️⃣ Proof of funding (if any)\n"
    "3️⃣ Academic record\n"
    "4️⃣ Intended institution\n"
    "5️⃣ Degree you want to pursue\n"
    "6️⃣ Your email address & cellphone number\n\n"
    "💰 Application support fee: *R60* (covers admin & verification)\n\n"
    "Once I receive your documents, I’ll help you complete and submit your NRF application.\n\n"
    "Let’s get you funded! 🚀\n"
    "— Ronewa | NRF Application Support\n"
    "📱 Save my number & share with others who might need help 💚"
)

def _auto_reply(driver):
    print("🤖 Auto-reply system running. Listening for 'Yes' messages...")

    while True:
        try:
            # Find unread chats
            unread_chats = driver.find_elements(By.XPATH, '//span[@aria-label and contains(@aria-label, "unread message")]')
            for chat in unread_chats:
                chat.click()
                time.sleep(2)

                # Find the latest message
                messages = driver.find_elements(By.CSS_SELECTOR, "div._21Ahp span.selectable-text")
                if not messages:
                    continue

                last_msg = messages[-1].text.strip().lower()
                print(f"💬 New message detected: {last_msg}")

                if re.search(r"\b(yes|yeah|yep|yebo|sure|okay|ok)\b", last_msg):
                    print("✅ Sending follow-up message...")
                    msg_box = driver.find_element(By.XPATH, '//div[@title="Type a message"]')
                    msg_box.click()
                    msg_box.send_keys(FOLLOWUP_MESSAGE)
                    send_btn = driver.find_element(By.XPATH, '//button[@aria-label="Send"]')
                    send_btn.click()
                    print("📤 Follow-up message sent successfully!")

            time.sleep(5)
        except NoSuchElementException:
            pass
        except Exception as e:
            print("⚠️ Error in auto-reply loop:", e)
            time.sleep(5)


# ---------------- Main Runner ---------------- #
if __name__ == "__main__":
    print("🚀 Starting WhatsApp Auto-Replier...")
    driver = _setup_driver()
    if driver:
        thread = threading.Thread(target=_auto_reply, args=(driver,), daemon=True)
        thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Auto-replier stopped manually.")
