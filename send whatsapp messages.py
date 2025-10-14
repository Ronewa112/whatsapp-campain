import pywhatkit as kit
import pandas as pd
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from docx import Document
from PyPDF2 import PdfReader
import threading
import re
import phonenumbers

cleaned_numbers = []

# ========== Utility Functions ==========

def extract_numbers_from_text(text):
    """Extract all potential numbers from text."""
    potential_numbers = re.findall(r"(\+?\d[\d\s\-()]{8,20})", text)
    return [n.strip() for n in potential_numbers]


def clean_numbers(raw_numbers, default_region="ZA"):
    """Use phonenumbers library to parse and validate international numbers."""
    clean, removed = [], []
    for num in raw_numbers:
        try:
            parsed = phonenumbers.parse(num, default_region)
            if phonenumbers.is_valid_number(parsed):
                e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                if e164 not in clean:
                    clean.append(e164)
            else:
                removed.append(num)
        except Exception:
            removed.append(num)
    return clean, removed


# ========== File Loading ==========

def load_numbers_from_file():
    """Allow importing of numbers from Excel, CSV, or TXT."""
    file_path = filedialog.askopenfilename(filetypes=[("Supported Files", "*.xlsx *.csv *.txt")])
    if not file_path:
        return

    raw_numbers = []
    try:
        if file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)
            raw_text = " ".join(df.astype(str).apply(lambda x: " ".join(x), axis=1))
            raw_numbers = extract_numbers_from_text(raw_text)
        elif file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
            raw_text = " ".join(df.astype(str).apply(lambda x: " ".join(x), axis=1))
            raw_numbers = extract_numbers_from_text(raw_text)
        elif file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                raw_numbers = extract_numbers_from_text(f.read())
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load numbers: {e}")
        return

    clean, removed = clean_numbers(raw_numbers)
    show_clean_numbers(clean, removed)


def load_numbers_from_textbox():
    """Clean numbers typed or pasted manually."""
    raw_input = numbers_box.get(1.0, tk.END).strip()
    if not raw_input:
        messagebox.showwarning("Warning", "Please type or paste numbers first.")
        return

    raw_numbers = extract_numbers_from_text(raw_input)
    clean, removed = clean_numbers(raw_numbers)
    show_clean_numbers(clean, removed)


def show_clean_numbers(clean, removed):
    global cleaned_numbers
    cleaned_numbers = clean
    clean_box.delete(1.0, tk.END)
    clean_box.insert(tk.END, "\n".join(clean))

    removed_box.delete(1.0, tk.END)
    removed_box.insert(tk.END, "\n".join(removed))

    messagebox.showinfo("Cleaning Done", f"✅ {len(clean)} valid numbers, ❌ {len(removed)} removed.")


# ========== Message Loading ==========

def load_message_from_file():
    """Import message text from txt, docx, or pdf."""
    file_path = filedialog.askopenfilename(filetypes=[("Supported Files", "*.txt *.docx *.pdf")])
    if not file_path:
        return

    text = ""
    try:
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif file_path.endswith(".pdf"):
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load message: {e}")
        return

    message_box.delete(1.0, tk.END)
    message_box.insert(tk.END, text)


# ========== Sending Logic ==========

def send_messages():
    """Start sending messages in background."""
    if not cleaned_numbers:
        messagebox.showwarning("Warning", "Please clean or load numbers first.")
        return

    message = message_box.get(1.0, tk.END).strip()
    if not message:
        messagebox.showwarning("Warning", "Please type or import a message first.")
        return

    progress["maximum"] = len(cleaned_numbers)
    send_button.config(state="disabled")
    threading.Thread(target=process_sending, args=(message,)).start()


def process_sending(message):
    """Send messages with progress feedback."""
    sent_count = 0
    for num in cleaned_numbers:
        try:
            print(f"Sending to {num}...")
            kit.sendwhatmsg_instantly(num, message, wait_time=15, tab_close=True)
            sent_count += 1
            progress["value"] = sent_count
            root.update_idletasks()
            time.sleep(5)
        except Exception as e:
            print(f"❌ Failed to send to {num}: {e}")
            continue

    messagebox.showinfo("Completed", f"✅ Sent {sent_count} message(s) successfully.")
    send_button.config(state="normal")


# ========== GUI ==========

root = tk.Tk()
root.title("🌍 International WhatsApp Bulk Sender")
root.geometry("950x800")
root.config(bg="#eef5f9")

# ---- Title ----
tk.Label(root, text="🌍 WhatsApp Campaign Tool (International Supported)", font=("Arial", 20, "bold"), fg="#007bff", bg="#eef5f9").pack(pady=10)

# ---- Number Input Section ----
tk.Label(root, text="Enter or Paste Numbers Below (or Import from File):", bg="#eef5f9", font=("Arial", 12, "bold")).pack()
numbers_box = scrolledtext.ScrolledText(root, width=70, height=8, font=("Arial", 11))
numbers_box.pack(pady=5)

frame_num = tk.Frame(root, bg="#eef5f9")
frame_num.pack(pady=5)
tk.Button(frame_num, text="📂 Import Numbers", command=load_numbers_from_file, bg="#007bff", fg="white", width=18, height=2).grid(row=0, column=0, padx=10)
tk.Button(frame_num, text="🧹 Clean Numbers", command=load_numbers_from_textbox, bg="#17a2b8", fg="white", width=18, height=2).grid(row=0, column=1, padx=10)

# ---- Cleaned Numbers Display ----
tk.Label(root, text="✅ Valid Numbers", bg="#eef5f9", font=("Arial", 12, "bold")).pack()
clean_box = scrolledtext.ScrolledText(root, width=70, height=6, font=("Arial", 10))
clean_box.pack(pady=5)

tk.Label(root, text="❌ Invalid or Removed Numbers", bg="#eef5f9", font=("Arial", 12, "bold")).pack()
removed_box = scrolledtext.ScrolledText(root, width=70, height=5, font=("Arial", 10))
removed_box.pack(pady=5)

# ---- Message Input ----
tk.Label(root, text="💬 Type or Import Your Message Below:", bg="#eef5f9", font=("Arial", 12, "bold")).pack()
message_box = scrolledtext.ScrolledText(root, width=80, height=8, font=("Arial", 11))
message_box.pack(pady=5)

tk.Button(root, text="📄 Import Message File", command=load_message_from_file, bg="#28a745", fg="white", width=20, height=2).pack(pady=5)

# ---- Send Button ----
send_button = tk.Button(root, text="🚀 Send Messages", command=send_messages, bg="#dc3545", fg="white", font=("Arial", 14, "bold"), width=20, height=2)
send_button.pack(pady=15)

# ---- Progress Bar ----
progress = ttk.Progressbar(root, length=600, mode="determinate")
progress.pack(pady=10)

root.mainloop()
