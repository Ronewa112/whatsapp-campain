import tkinter as tk
from tkinter import messagebox, scrolledtext
import pywhatkit as kit
import re
import time

# --------------- Cleaning Function ----------------
def clean_numbers(raw_text):
    # Remove all letters or words (like "number", "contact", etc.)
    text = re.sub(r"[A-Za-z]", " ", raw_text)
    # Find all phone number patterns like +27 79 361 2279
    matches = re.findall(r"\+?\d[\d\s]{7,}", text)
    cleaned = []
    for m in matches:
        n = "+" + re.sub(r"\D", "", m.lstrip("+"))
        cleaned.append(n)
    # Remove duplicates
    cleaned = list(dict.fromkeys(cleaned))
    return cleaned

# --------------- Button Actions ----------------
def process_numbers():
    raw_text = numbers_input.get("1.0", tk.END)
    cleaned = clean_numbers(raw_text)
    if not cleaned:
        messagebox.showwarning("No Valid Numbers", "No valid phone numbers found. Please check your input.")
        return

    # Show cleaned numbers
    cleaned_output.config(state="normal")
    cleaned_output.delete("1.0", tk.END)
    formatted = ""
    for i, num in enumerate(cleaned, 1):
        end = ",\n" if i % 4 == 0 else ", "
        formatted += f'    "{num}"' + end
    cleaned_output.insert(tk.END, formatted)
    cleaned_output.config(state="disabled")

    # Save cleaned numbers
    with open("cleaned_numbers.txt", "w") as f:
        for num in cleaned:
            f.write(num + "\n")

    global cleaned_numbers
    cleaned_numbers = cleaned
    messagebox.showinfo("Success", f"{len(cleaned)} numbers cleaned and saved!")

def send_messages():
    global cleaned_numbers
    if not cleaned_numbers:
        messagebox.showerror("No Numbers", "Please clean numbers first before sending.")
        return

    message = message_input.get("1.0", tk.END).strip()
    if not message:
        messagebox.showerror("No Message", "Please type your message before sending.")
        return

    confirm = messagebox.askyesno("Confirm Send", f"Send message to {len(cleaned_numbers)} numbers?")
    if not confirm:
        return

    # Send messages
    for num in cleaned_numbers:
        try:
            print(f"Sending to {num}...")
            kit.sendwhatmsg_instantly(num, message, 15, True, 3)
            time.sleep(6)
        except Exception as e:
            print(f"Failed to send to {num}: {e}")
    messagebox.showinfo("Done", "All messages attempted!")

# --------------- GUI Setup ----------------
root = tk.Tk()
root.title("📱 WhatsApp Cleaner & Sender")
root.geometry("850x600")
root.resizable(False, False)
cleaned_numbers = []

# Title
tk.Label(root, text="WhatsApp Cleaner & Bulk Sender", font=("Arial", 18, "bold"), fg="#0b5394").pack(pady=10)

# Input for numbers
tk.Label(root, text="Paste your messy numbers here:", font=("Arial", 12, "bold")).pack()
numbers_input = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=7)
numbers_input.pack(pady=5)

# Clean button
tk.Button(root, text="🧹 Clean Numbers", bg="#6aa84f", fg="white", font=("Arial", 12, "bold"), command=process_numbers).pack(pady=5)

# Output area for cleaned numbers
tk.Label(root, text="Cleaned Numbers (copied automatically to cleaned_numbers.txt):", font=("Arial", 12, "bold")).pack()
cleaned_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=7, state="disabled")
cleaned_output.pack(pady=5)

# Message box
tk.Label(root, text="Type or paste your WhatsApp message:", font=("Arial", 12, "bold")).pack()
message_input = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=5)
message_input.pack(pady=5)

# Send button
tk.Button(root, text="🚀 Send WhatsApp Messages", bg="#0b5394", fg="white", font=("Arial", 12, "bold"), command=send_messages).pack(pady=10)

root.mainloop()
