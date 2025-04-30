import os
import time
import random
import string
import logging
import threading
from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration & Logging ---
logging.basicConfig(
    filename='account_creator.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

SIGNUP_URL = os.environ.get("SIGNUP_URL", "https://playinexch247.com/#")
DELAY_SECONDS = int(os.environ.get("DELAY_SECONDS", "5"))

# --- Account Creation Logic ---
def create_accounts(base, password, count, custom_phone):
    driver_opts = Options()
    driver_opts.add_argument("--headless")
    driver_opts.add_argument("--disable-gpu")
    driver_opts.add_argument("--no-sandbox")
    driver_opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=driver_opts)
    success = 0

    for i in range(1, count + 1):
        username = f"{base}{i}"
        email = f"{base}{i}@gmail.com"
        phone = custom_phone or "".join(random.choices(string.digits, k=10))
        try:
            driver.get(SIGNUP_URL)
            driver.find_element(By.NAME, "username").send_keys(username)
            driver.find_element(By.NAME, "email").send_keys(email)
            driver.find_element(By.NAME, "password").send_keys(password)
            driver.find_element(By.NAME, "mobile").send_keys(phone)
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            logging.info(f"[OK]   {username} / {email} / {phone}")
            success += 1
        except Exception as e:
            logging.error(f"[FAIL] {username}: {e}")
        time.sleep(DELAY_SECONDS)

    driver.quit()
    logging.info(f"Finished batch: {success}/{count} created.")
    return success

# --- Flask App & Routes ---
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        base = request.form.get("base_username", "").strip()
        password = request.form.get("password", "").strip()
        count_str = request.form.get("count", "").strip()
        phone = request.form.get("phone", "").strip()
        error = None

        if not base or not password or not count_str:
            error = "Base username, password, and count are required."
        elif not count_str.isdigit() or int(count_str) < 1:
            error = "Count must be a positive integer."
        elif phone and (not phone.isdigit() or len(phone) != 10):
            error = "Phone must be a 10-digit number."
        
        if error:
            return render_template("index.html", error=error)
        
        count = int(count_str)
        thread = threading.Thread(target=create_accounts, args=(base, password, count, phone), daemon=True)
        thread.start()
        success = f"Started batch: base='{base}', count={count}, delay={DELAY_SECONDS}s"
        return render_template("index.html", success=success)

    return render_template("index.html")

@app.route("/create", methods=["POST"])
def create_endpoint():
    data = request.get_json() or {}
    base      = data.get("base_username")
    password  = data.get("password")
    count     = data.get("count")
    phone     = data.get("phone", "")

    if not base or not password or not isinstance(count, int) or count < 1:
        return jsonify({"error": "base_username, password, and positive integer count required"}), 400
    if phone and (not phone.isdigit() or len(phone) != 10):
        return jsonify({"error": "phone must be a 10-digit string"}), 400

    thread = threading.Thread(target=create_accounts, args=(base, password, count, phone), daemon=True)
    thread.start()
    return jsonify({
        "status": "started",
        "base_username": base,
        "count": count,
        "delay_seconds": DELAY_SECONDS
    }), 202

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
