# web_config.py - Simple web interface for the controller
import os
import wifi
import socketpool
import asyncio
from adafruit_httpserver import Server, Request, Response, JSONResponse, FileResponse

class WebConfig:
    def __init__(self, settings, save_callback=None):
        self.settings = settings
        self.save_callback = save_callback
        self.pool = None
        self.server = None

    def start(self):
        try:
            self.pool = socketpool.SocketPool(wifi.radio)
            self.server = Server(self.pool, "/static", debug=True)
            
            @self.server.route("/")
            def home(request: Request):
                html = f"""
                <html><head><title>{self.settings.get('machine', 'Pico Controller')}</title></head>
                <body>
                    <h1>🎛️ {self.settings.get('machine', 'Controller')} Status</h1>
                    <p><strong>IP:</strong> {wifi.radio.ipv4_address}</p>
                    <p><strong>MACHINE:</strong> {self.settings.get('machine')}</p>
                    <hr>
                    <h2>Quick Settings</h2>
                    <form method="POST" action="/save">
                        <label>OSC Host:</label><input name="OSC_HOST" value="{os.getenv('OSC_HOST')}"><br><br>
                        <label>Flash Brightness (%):</label><input name="FLASH_BRIGHTNESS" value="{os.getenv('FLASH_BRIGHTNESS', 100)}"><br><br>
                        <input type="submit" value="Save & Reboot">
                    </form>
                </body></html>
                """
                return Response(request, html, content_type="text/html")

            @self.server.route("/save", method="POST")
            def save(request: Request):
                try:
                    data = request.json() or {}
                    updates = {}
                    for key, value in data.items():
                        updates[key] = value
                    if self.save_callback:
                        self.save_callback(updates)
                    return JSONResponse(request, {"status": "saved", "reboot": True})
                except:
                    return Response(request, "Error", status_code=500)

            print(f"🌐 Web server starting on http://{wifi.radio.ipv4_address}")
            self.server.start()

        except Exception as e:
            print("Web server failed to start:", e)

    async def poll(self):
        """Call this regularly in your main loop"""
        while True:
            try:
                self.server.poll()
            except:
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.05)