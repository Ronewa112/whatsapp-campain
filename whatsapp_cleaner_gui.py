# proitech_campaign_final_v2.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading, time, re, smtplib
import pandas as pd
import pywhatkit as kit
import pyautogui
import phonenumbers
from docx import Document
from PyPDF2 import PdfReader
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------- CONFIG ----------
APP_TITLE = "ProItech Campaign Sender — Pro"
DEFAULT_DELAY = 6
# Email placeholder (replace with your Gmail and app password)
GMAIL_USER = "your_email@gmail.com"
GMAIL_APP_PASS = "your_app_password"
# Theme colors (Green & Black ProItech)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ---------- Utilities ----------
def extract_numbers_from_text(text):
    matches = re.findall(r"(\+?\d[\d\s\-\(\)]{6,20}\d)", text)
    if not matches:
        matches = re.findall(r"\d{6,15}", text)
    return [m.strip() for m in matches]

def normalize_and_validate(numbers_list, default_region="ZA"):
    valid = []
    removed = []
    for raw in numbers_list:
        s = str(raw).strip()
        if not s:
            continue
        s = s.replace("\u200b", "")
        try:
            if s.startswith("+"):
                parsed = phonenumbers.parse(s, None)
            else:
                parsed = phonenumbers.parse(s, default_region)
            if phonenumbers.is_valid_number(parsed):
                e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                if e164 not in valid:
                    valid.append(e164)
            else:
                removed.append(s)
        except Exception:
            digits = re.sub(r"\D", "", s)
            if len(digits) >= 9 and digits.startswith("0"):
                try:
                    parsed = phonenumbers.parse(digits, "ZA")
                    if phonenumbers.is_valid_number(parsed):
                        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                        if e164 not in valid:
                            valid.append(e164)
                        continue
                except Exception:
                    pass
            removed.append(s)
    return valid, removed

def read_numbers_file(path):
    rows = []
    pl = path.lower()
    if pl.endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, header=None, dtype=str)
        for _, r in df.iterrows():
            for v in r.tolist():
                if v is not None and str(v).strip() and str(v) != 'nan':
                    rows.append(str(v).strip())
    elif pl.endswith(".csv"):
        df = pd.read_csv(path, header=None, dtype=str)
        for _, r in df.iterrows():
            for v in r.tolist():
                if v is not None and str(v).strip() and str(v) != 'nan':
                    rows.append(str(v).strip())
    elif pl.endswith(".txt"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    rows.append(line.strip())
    return rows

def read_message_file(path):
    pl = path.lower()
    if pl.endswith(".txt"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if pl.endswith(".docx"):
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    if pl.endswith(".pdf"):
        rd = PdfReader(path)
        txt = []
        for pg in rd.pages:
            t = pg.extract_text()
            if t:
                txt.append(t)
        return "\n".join(txt)
    return ""

def send_completion_email(to_email, subject, body):
    if not GMAIL_USER or not GMAIL_APP_PASS:
        return False, "No Gmail credentials configured."
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
        server.quit()
        return True, "Email sent"
    except Exception as e:
        return False, str(e)

# ---------- App ----------
class CampaignApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x780")
        self.minsize(900, 650)

        self.valid_numbers = []
        self.removed_numbers = []
        self.sending = False

        self._build_ui()
        self.after(300, self._live_preview_loop)

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, corner_radius=0)
        header.pack(fill="x", padx=12, pady=8)
        self.lbl_title = ctk.CTkLabel(header, text=APP_TITLE, font=("Roboto", 20, "bold"))
        self.lbl_title.pack(side="left", padx=(10,12))
        self.lbl_sub = ctk.CTkLabel(header, text="Modern • International • ProItech", font=("Roboto", 12))
        self.lbl_sub.pack(side="left")
        # right: theme toggle (CTk has built-in) and help
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=6)
        self.theme_btn = ctk.CTkButton(btn_frame, text="Toggle Theme", width=110, command=self._toggle_theme)
        self.theme_btn.pack(side="right", padx=6)
        self.help_btn = ctk.CTkButton(btn_frame, text="Help", width=70, command=self._show_help)
        self.help_btn.pack(side="right", padx=6)

        # Main panes: left (inputs) and right (preview + log)
        main_panes = ctk.CTkFrame(self)
        main_panes.pack(fill="both", expand=True, padx=12, pady=(6,12))

        # use grid for responsive distribution
        main_panes.grid_columnconfigure(0, weight=3)
        main_panes.grid_columnconfigure(1, weight=1)
        main_panes.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(main_panes)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=0)
        right_frame = ctk.CTkFrame(main_panes, width=360)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=0)

        # --- LEFT: Numbers, cleaned lists, message, send control ---
        # Numbers input
        nums_card = ctk.CTkFrame(left_frame, corner_radius=6)
        nums_card.pack(fill="x", padx=6, pady=(6,8))
        ctk.CTkLabel(nums_card, text="1) Numbers — Paste / Type / Import", font=("Roboto", 13, "bold")).pack(anchor="w", pady=(8,4), padx=8)
        self.numbers_text = ScrolledText(nums_card, height=6, wrap="word")
        self.numbers_text.pack(fill="both", padx=8, pady=(0,8), expand=False)

        nums_btns = ctk.CTkFrame(nums_card, fg_color="transparent")
        nums_btns.pack(fill="x", padx=8, pady=(0,8))
        ctk.CTkButton(nums_btns, text="📂 Import Numbers", command=self._import_numbers, width=180).pack(side="left", padx=(0,8))
        ctk.CTkButton(nums_btns, text="🧹 Clean Numbers", command=self._clean_numbers, width=140).pack(side="left", padx=(0,8))
        ctk.CTkButton(nums_btns, text="🔁 Re-clean", command=self._reclean, width=110).pack(side="left")

        counts_frame = ctk.CTkFrame(nums_card, fg_color="transparent")
        counts_frame.pack(fill="x", padx=8, pady=(0,6))
        self.lbl_valid = ctk.CTkLabel(counts_frame, text="Valid: 0")
        self.lbl_valid.pack(side="left", padx=(0,8))
        self.lbl_removed = ctk.CTkLabel(counts_frame, text="Removed: 0")
        self.lbl_removed.pack(side="left")

        # Cleaned & removed lists (side-by-side)
        lists_frame = ctk.CTkFrame(left_frame, corner_radius=6)
        lists_frame.pack(fill="both", expand=True, padx=6, pady=(0,8))
        lists_frame.grid_rowconfigure(0, weight=1)
        lists_frame.grid_columnconfigure(0, weight=1)
        lists_frame.grid_columnconfigure(1, weight=1)

        # cleaned list
        c_frame = ctk.CTkFrame(lists_frame)
        c_frame.grid(row=0, column=0, sticky="nsew", padx=(6,3), pady=6)
        ctk.CTkLabel(c_frame, text="✅ Cleaned Numbers").pack(anchor="w", padx=6, pady=(6,2))
        self.tree_clean = ctk.CTkTextbox(c_frame, width=10, height=200)
        self.tree_clean.pack(fill="both", expand=True, padx=6, pady=(0,6))
        # removed list
        r_frame = ctk.CTkFrame(lists_frame)
        r_frame.grid(row=0, column=1, sticky="nsew", padx=(3,6), pady=6)
        ctk.CTkLabel(r_frame, text="❌ Removed / Invalid").pack(anchor="w", padx=6, pady=(6,2))
        self.tree_removed = ctk.CTkTextbox(r_frame, width=10, height=200)
        self.tree_removed.pack(fill="both", expand=True, padx=6, pady=(0,6))

        # --- Message card (above Activity Log as requested) ---
        msg_card = ctk.CTkFrame(left_frame, corner_radius=6)
        msg_card.pack(fill="x", padx=6, pady=(0,8))
        ctk.CTkLabel(msg_card, text="2) Message — Type or Import (emojis supported)", font=("Roboto", 13, "bold")).pack(anchor="w", pady=(8,6), padx=8)
        self.msg_text = ScrolledText(msg_card, height=8, wrap="word")
        self.msg_text.pack(fill="both", padx=8, pady=(0,8), expand=False)

        msg_btns = ctk.CTkFrame(msg_card, fg_color="transparent")
        msg_btns.pack(fill="x", padx=8, pady=(0,8))
        ctk.CTkButton(msg_btns, text="📄 Import Message", command=self._import_message, width=180).pack(side="left", padx=(0,8))
        ctk.CTkButton(msg_btns, text="🔎 Preview", command=self._preview_message, width=110).pack(side="left", padx=(0,8))
        ctk.CTkButton(msg_btns, text="➡ Send Area", command=lambda: self.msg_text.focus_set(), width=110).pack(side="left")

        # Send control (large visible button)
        send_card = ctk.CTkFrame(left_frame, corner_radius=6)
        send_card.pack(fill="x", padx=6, pady=(0,8))
        send_ctrl = ctk.CTkFrame(send_card, fg_color="transparent")
        send_ctrl.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(send_ctrl, text="3) Send — choose Delay & Mode", anchor="w").pack(side="left")
        # controls right
        right_controls = ctk.CTkFrame(send_ctrl, fg_color="transparent")
        right_controls.pack(side="right")
        self.delay_spin = ctk.CTkEntry(right_controls, width=70)
        self.delay_spin.insert(0, str(DEFAULT_DELAY))
        self.delay_spin.pack(side="left", padx=(0,8))
        ctk.CTkLabel(right_controls, text="Delay(s)").pack(side="left", padx=(0,8))
        # send mode
        self.send_mode = ctk.StringVar(value="immediate")
        ctk.CTkRadioButton(right_controls, text="Immediate", variable=self.send_mode, value="immediate").pack(side="left", padx=6)
        ctk.CTkRadioButton(right_controls, text="Schedule", variable=self.send_mode, value="schedule").pack(side="left", padx=6)
        # schedule time
        self.hour_spin = ctk.CTkEntry(right_controls, width=50)
        self.hour_spin.insert(0, time.strftime("%H"))
        self.hour_spin.pack(side="left", padx=(6,2))
        self.min_spin = ctk.CTkEntry(right_controls, width=50)
        self.min_spin.insert(0, f"{(int(time.strftime('%M'))+2)%60:02d}")
        self.min_spin.pack(side="left", padx=(2,6))

        # big send button (centered)
        send_btn_frame = ctk.CTkFrame(send_card, fg_color="transparent")
        send_btn_frame.pack(fill="x", padx=8, pady=(6,6))
        self.send_btn = ctk.CTkButton(send_btn_frame, text="🚀 SEND MESSAGES", width=300, height=48, command=self._confirm_and_send)
        self.send_btn.pack(anchor="center")

        # Progress + ETA
        prog_frame = ctk.CTkFrame(send_card, fg_color="transparent")
        prog_frame.pack(fill="x", padx=8, pady=(4,8))
        self.progress = ctk.CTkProgressBar(prog_frame)
        self.progress.set(0.0)
        self.progress.pack(fill="x", side="left", expand=True, padx=(0,8))
        self.eta_label = ctk.CTkLabel(prog_frame, text="ETA: 0s")
        self.eta_label.pack(side="right")

        # --- RIGHT: Preview & Collapsible Activity Log ---
        right_inner = ctk.CTkFrame(right_frame, corner_radius=6)
        right_inner.pack(fill="both", expand=True, padx=6, pady=6)

        ctk.CTkLabel(right_inner, text="Preview", font=("Roboto", 12, "bold")).pack(anchor="w", padx=8, pady=(8,4))
        self.preview_box = ScrolledText(right_inner, height=10, wrap="word")
        self.preview_box.pack(fill="both", expand=False, padx=8, pady=(0,8))

        stats_frame = ctk.CTkFrame(right_inner, fg_color="transparent")
        stats_frame.pack(fill="x", padx=8)
        self.stat_total = ctk.CTkLabel(stats_frame, text="Total: 0")
        self.stat_total.pack(side="left", padx=(0,6))
        self.stat_valid = ctk.CTkLabel(stats_frame, text="Valid: 0")
        self.stat_valid.pack(side="left", padx=(0,6))
        self.stat_removed = ctk.CTkLabel(stats_frame, text="Removed: 0")
        self.stat_removed.pack(side="left", padx=(0,6))

        # Collapsible Activity Log
        log_header = ctk.CTkFrame(right_inner, fg_color="transparent")
        log_header.pack(fill="x", padx=8, pady=(12,0))
        self.log_toggle_btn = ctk.CTkButton(log_header, text="▼ Activity Log (click to collapse)", width=260, command=self._toggle_log)
        self.log_toggle_btn.pack(anchor="w")

        self.log_container = ctk.CTkFrame(right_inner, fg_color="transparent")
        self.log_container.pack(fill="both", expand=True, padx=8, pady=(6,8))
        self.log_box = ScrolledText(self.log_container, height=10, wrap="word")
        self.log_box.pack(fill="both", expand=True)

        # initial state: log visible
        self.log_visible = True

    # ---------- Actions ----------
    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if current == "dark" else "dark")

    def _show_help(self):
        messagebox.showinfo("Help", "1. Paste/import numbers -> 2. Clean -> 3. Type/import message -> 4. Send.\nKeep WhatsApp Web logged in. Use delay >=4s for safer sending.")

    def _import_numbers(self):
        path = filedialog.askopenfilename(filetypes=[("Number files","*.xlsx *.xls *.csv *.txt")])
        if not path:
            return
        rows = read_numbers_file(path)
        if rows:
            cur = self.numbers_text.get("1.0", "end").strip()
            to_add = "\n".join(rows)
            if cur:
                self.numbers_text.insert("end", "\n" + to_add)
            else:
                self.numbers_text.insert("end", to_add)
            self._log(f"Imported {len(rows)} rows from file.")
        else:
            self._log("No rows found in file.")

    def _clean_numbers(self):
        raw = self.numbers_text.get("1.0", "end")
        candidates = extract_numbers_from_text(raw)
        if not candidates:
            messagebox.showwarning("No numbers", "Please paste, type, or import numbers first.")
            return
        valid, removed = normalize_and_validate(candidates)
        self._populate_number_views(valid, removed)
        self._log(f"Cleaned: {len(valid)} valid • {len(removed)} removed.")

    def _reclean(self):
        current = self.tree_clean.get("1.0", "end").strip().splitlines()
        current = [c.strip() for c in current if c.strip()]
        if not current:
            messagebox.showwarning("Nothing to re-clean", "Clean list is empty.")
            return
        valid, removed = normalize_and_validate(current)
        self._populate_number_views(valid, removed)
        self._log("Re-clean completed.")

    def _import_message(self):
        path = filedialog.askopenfilename(filetypes=[("Message files","*.txt *.docx *.pdf")])
        if not path:
            return
        text = read_message_file(path)
        if text:
            self.msg_text.delete("1.0", "end")
            self.msg_text.insert("1.0", text)
            self._log("Message imported.")
        else:
            messagebox.showwarning("Empty", "No text extracted from file.")

    def _preview_message(self):
        txt = self.msg_text.get("1.0", "end").strip()
        if not txt:
            messagebox.showwarning("No message", "Type or import a message first.")
            return
        preview = txt if len(txt) < 900 else txt[:900] + "\n\n...[truncated]"
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", preview)
        self._log("Message preview updated.")

    def _populate_number_views(self, valid, removed):
        # populate two textboxes
        self.tree_clean.delete("1.0", "end")
        self.tree_removed.delete("1.0", "end")
        for n in valid:
            self.tree_clean.insert("end", n + "\n")
        for r in removed:
            self.tree_removed.insert("end", r + "\n")
        self.valid_numbers = valid
        self.removed_numbers = removed
        tot = len(valid) + len(removed)
        self.lbl_valid.configure(text=f"Valid: {len(valid)}")
        self.lbl_removed.configure(text=f"Removed: {len(removed)}")
        self.stat_total.configure(text=f"Total: {tot}")
        self.stat_valid.configure(text=f"Valid: {len(valid)}")
        self.stat_removed.configure(text=f"Removed: {len(removed)}")
        preview_list = "\n".join(valid[:80]) if valid else "No valid numbers yet."
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", "Preview (first entries):\n" + preview_list)

    def _toggle_log(self):
        if self.log_visible:
            self.log_container.forget()
            self.log_toggle_btn.configure(text="► Activity Log (click to expand)")
            self.log_visible = False
        else:
            self.log_container.pack(fill="both", expand=True, padx=8, pady=(6,8))
            self.log_toggle_btn.configure(text="▼ Activity Log (click to collapse)")
            self.log_visible = True

    def _confirm_and_send(self):
        if not getattr(self, 'valid_numbers', None):
            messagebox.showwarning("No numbers", "Please clean and validate numbers before sending.")
            return
        message = self.msg_text.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("No message", "Type or import a message first.")
            return
        total = len(self.valid_numbers)
        try:
            delay = float(self.delay_spin.get())
        except Exception:
            messagebox.showerror("Delay error", "Invalid delay value.")
            return
        mode = self.send_mode.get()
        if mode == "schedule":
            try:
                hh = int(self.hour_spin.get()) % 24
                mm = int(self.min_spin.get()) % 60
            except Exception:
                messagebox.showerror("Time error", "Invalid schedule time.")
                return
            resp = messagebox.askyesno("Confirm schedule", f"Schedule sending to {total} numbers at {hh:02d}:{mm:02d}?\nDelay: {delay}s")
            if resp:
                threading.Thread(target=self._send_messages, args=(self.valid_numbers, message, delay, True, hh, mm), daemon=True).start()
        else:
            resp = messagebox.askyesno("Confirm send", f"Send immediately to {total} numbers?\nDelay: {delay}s")
            if resp:
                threading.Thread(target=self._send_messages, args=(self.valid_numbers, message, delay, False, 0, 0), daemon=True).start()

    def _send_messages(self, numbers, message, delay, use_schedule, hh, mm):
        if self.sending:
            return
        self.sending = True
        total = len(numbers)
        self.progress.set(0.0)
        self.progress.set(0.0)
        start = time.time()
        sent = 0
        for idx, num in enumerate(numbers, start=1):
            try:
                self._log(f"[{idx}/{total}] Sending → {num}")
                snippet = message if len(message) < 700 else message[:700] + "..."
                self.preview_box.delete("1.0", "end")
                self.preview_box.insert("1.0", f"Sending to: {num}\n\n{snippet}")
                if use_schedule:
                    scheduled_hour = hh
                    scheduled_minute = mm + (idx - 1)
                    scheduled_hour += scheduled_minute // 60
                    scheduled_minute = scheduled_minute % 60
                    scheduled_hour = scheduled_hour % 24
                    kit.sendwhatmsg(num, message, scheduled_hour, scheduled_minute, wait_time=15, tab_close=True)
                    self._log(f"[SCHEDULED] {num} at {scheduled_hour:02d}:{scheduled_minute:02d}")
                else:
                    kit.sendwhatmsg_instantly(num, message, wait_time=10, tab_close=True)
                    time.sleep(2)
                    try:
                        pyautogui.press('enter')
                    except Exception:
                        pass
                    self._log(f"[SENT] {num}")
                sent += 1
            except Exception as e:
                self._log(f"[ERR] {num} -> {e}", level="err")
            # update progress
            self.progress.set(idx/total)
            elapsed = time.time() - start
            avg = elapsed / idx if idx else 0
            remaining = int((total - idx) * avg)
            self.eta_label.configure(text=f"ETA: {remaining}s")
            if not use_schedule and idx < total:
                time.sleep(delay)
        self._log(f"Finished. Sent {sent}/{total}")
        # send completion email (try)
        user_email = None
        # if user logged in / provided email: you can replace below with actual target
        if GMAIL_USER and GMAIL_APP_PASS:
            subject = "Campaign Complete"
            body = f"Your WhatsApp campaign completed. Sent {sent}/{total} messages."
            ok, msg = send_completion_email(GMAIL_USER, subject, body)
            self._log(f"Completion email attempt: {msg}")
        self.sending = False
        messagebox.showinfo("Done", f"Finished. Sent {sent}/{total} messages.")

    def _log(self, text, level="info"):
        ts = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {text}\n")
        self.log_box.see("end")

    def _live_preview_loop(self):
        # update preview frequently (non-blocking)
        txt = self.msg_text.get("1.0", "end").strip()
        if txt:
            preview = txt if len(txt) < 900 else txt[:900] + "\n\n...[truncated]"
            # only update when changed to reduce flicker
            cur = self.preview_box.get("1.0", "end").strip()
            if not cur.startswith("Sending to:") and cur != preview:
                self.preview_box.delete("1.0", "end")
                self.preview_box.insert("1.0", preview)
        self.after(400, self._live_preview_loop)

# ---------- Run ----------
if __name__ == "__main__":
    app = CampaignApp()
    app.mainloop()
