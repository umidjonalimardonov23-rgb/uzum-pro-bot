import os, asyncio, threading
from werkzeug.serving import make_server
from app import app, init_db as web_init_db

def run_flask():
    port = int(os.getenv("PORT", 5000))
    server = make_server("0.0.0.0", port, app)
    print(f"[web] Flask listening on port {port}")
    server.serve_forever()

async def main():
    web_init_db()

    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    import bot as bot_module
    print("[bot] Starting polling...")
    await bot_module.main()

if __name__ == "__main__":
    asyncio.run(main())
