import socketserver
from http import server
import logging
import urllib.parse
import time
from threading import Thread
import subprocess
import os
import base64
import socket # Import thêm socket để set timeout

import state
import wifi_manager

# --- CẤU HÌNH BẢO MẬT ---
# Tạo ID phiên đăng nhập dựa trên thời gian khởi động server
# Mỗi lần chạy lại code, ID này sẽ thay đổi, buộc trình duyệt hỏi lại mật khẩu
SESSION_REALM = f"RPi_Camera_{int(time.time())}"

# --- SHARED CSS ---
COMMON_STYLE = """
<style>
    :root {
        --bg-color: #1a1a1a;
        --card-bg: #2d2d2d;
        --text-color: #ffffff;
        --primary-color: #3498db;
        --primary-hover: #2980b9;
        --danger-color: #e74c3c;
        --danger-hover: #c0392b;
        --success-color: #2ecc71;
    }
    body {
        font-family: "Poppins", sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        min-height: 100vh;
    }
    h1, h2 { margin-top: 20px; font-weight: 600; letter-spacing: 1px; }
    
    .container {
        width: 90%;
        max-width: 1200px; 
        margin: 20px auto;
        text-align: center;
    }

    .form-container {
        max-width: 400px;
        background: var(--card-bg);
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
    }

    .video-wrapper {
        width: 100%;
        margin: 20px 0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0,0,0,0.5);
        background: #000;
        display: inline-block;
    }
    
    .video-wrapper img {
        width: 100%;       
        height: auto;      
        display: block;    
        max-width: 100%;
    }

    input {
        width: 100%;
        padding: 15px;
        margin: 10px 0 20px 0;
        box-sizing: border-box;
        border: 1px solid #444;
        border-radius: 6px;
        background: #3d3d3d;
        color: white;
        font-size: 16px;
    }
    input:focus { outline: none; border-color: var(--primary-color); }

    .btn {
        display: inline-block;
        padding: 15px 30px;
        background: var(--primary-color);
        color: white;
        text-decoration: none;
        border-radius: 50px;
        font-weight: bold;
        font-size: 1rem;
        border: none;
        cursor: pointer;
        transition: transform 0.2s, background 0.2s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        width: 100%;
        max-width: 300px;
        box-sizing: border-box;
        margin-bottom: 15px; /* Add spacing between buttons */
    }
    .btn:active { transform: scale(0.98); }
    .btn:hover { background: var(--primary-hover); }
    
    /* Danger Button Style (Red) */
    .btn-danger {
        background: var(--danger-color);
    }
    .btn-danger:hover {
        background: var(--danger-hover);
    }
    
    .btn-secondary { background: transparent; border: 2px solid #555; margin-top: 15px; color: #aaa; }
    .btn-secondary:hover { border-color: #777; color: white; background: transparent; }

    .alert { padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: left; font-size: 0.9rem; line-height: 1.4; word-wrap: break-word;}
    .alert-error { background: rgba(231, 76, 60, 0.2); border: 1px solid var(--danger-color); color: #ffadad; }
    .alert-success { background: rgba(46, 204, 113, 0.2); border: 1px solid var(--success-color); color: #abebc6; }

    @media (min-width: 768px) {
        .container { margin-top: 40px; }
        h1 { font-size: 2.5rem; }
    }
</style>
"""

# HTML: Home Page
PAGE_HOME = f"""\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>RPi Cam Control</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    {COMMON_STYLE}
    <script>
        function confirmShutdown() {{
            return confirm("⚠️ WARNING: Are you sure you want to turn off the Raspberry Pi?");
        }}
        function confirmReset() {{
            return confirm("⚠️ WARNING: Are you sure you want to reboot the Raspberry Pi?");
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>🎥 RPi LIVE CAMERA</h1>
        
        <div class="video-wrapper">
            <img src="stream.mjpg" alt="Camera Stream Loading...">
        </div>
        
        <a href="/wifi" class="btn">⚙️ Configure Wifi</a>
        
        <form action="/shutdown" method="POST" onsubmit="return confirmShutdown();">
            <button type="submit" class="btn btn-danger">🔌 Shutdown System</button>
        </form>
        <form action="/reboot" method="POST" onsubmit="return confirmReset();">
            <button type="submit" class="btn btn-danger">🔄 Reset System</button>
        </form>
    </div>
</body>
</html>
"""

# HTML: Wifi Config Page
PAGE_WIFI = f"""\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wifi Config</title>
    {COMMON_STYLE}
</head>
<body>
    <div class="container form-container">
        <h2>📶 Connect Wifi</h2>
        <form method="POST" action="/set_wifi">
            <div style="text-align: left; margin-bottom: 5px; color: #ccc;">Wifi Name (SSID)</div>
            <input type="text" name="ssid" required placeholder="Enter Wifi Name..." autocomplete="off">
            
            <div style="text-align: left; margin-bottom: 5px; color: #ccc;">Password</div>
            <input type="password" name="password" required placeholder="Enter Password...">
            
            <button type="submit" class="btn">Connect Now</button>
        </form>
        <a href="/" class="btn btn-secondary">⬅️ Back to Camera</a>
    </div>
</body>
</html>
"""

# HTML: Success Page
PAGE_SUCCESS_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Success</title>
    {style}
</head>
<body>
    <div class="container form-container">
        <h2 style="color: var(--success-color);">✅ Connected!</h2>
        <div class="alert alert-success">{msg}</div>
        <p style="color: #aaa;">System is switching to the new network...</p>
        <a href="/" class="btn btn-secondary">Return Home</a>
    </div>
</body>
</html>
"""

# HTML: Error Page
PAGE_ERROR_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error</title>
    {style}
</head>
<body>
    <div class="container form-container">
        <h2 style="color: var(--danger-color);">❌ Connection Failed!</h2>
        <div class="alert alert-error">
            <strong>Error Details:</strong><br>
            {msg}
        </div>
        <p style="color: #ccc;">Please check the Wifi Name and Password.</p>
        <a href="/wifi" class="btn">🔄 Try Again</a>
    </div>
</body>
</html>
"""

# HTML: Shutdown Page
PAGE_SHUTDOWN = f"""\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shutting Down</title>
    {COMMON_STYLE}
</head>
<body>
    <div class="container form-container">
        <h2 style="color: var(--danger-color);">💀 Shutting Down...</h2>
        <p>The system is turning off safely.</p>
        <p>Please wait 30 seconds before unplugging power.</p>
        <p style="color: #666; font-size: 0.8rem;">Program Terminated.</p>
    </div>
</body>
</html>
"""

PAGE_REBOOT = f"""\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rebooting</title>
    {COMMON_STYLE}
</head>
<body>
    <div class="container form-container">
        <h2 style="color: var(--danger-color);">🔄 Rebooting...</h2>
        <p>The system is restarting.</p>
        <p>Please wait about 30 seconds.</p>
        <p style="color: #666; font-size: 0.8rem;">Program Terminated.</p>
    </div>
</body>
</html>
"""

class StreamingHandler(server.BaseHTTPRequestHandler):
    
    # 1. SETUP TIMEOUT: Ngắt kết nối nếu client treo quá 5 giây
    def setup(self):
        try:
            self.request.settimeout(5) # Set timeout 5 giây
        except:
            pass
        server.BaseHTTPRequestHandler.setup(self)

    def log_message(self, format, *args):
        return  # Disable console logs
    
    # --- AUTHENTICATION LOGIC ---
    def check_auth(self):
        auth_header = self.headers.get('Authorization')
        
        if auth_header is None:
            self.send_auth_request()
            return False
            
        try:
            auth_type, encoded_auth = auth_header.split(' ', 1)
            if auth_type.lower() == 'basic':
                decoded_auth = base64.b64decode(encoded_auth).decode('utf-8')
                username, password = decoded_auth.split(':', 1)
                
                if username == 'admin' and password == 'admin123':
                    return True 
                    
        except Exception:
            pass 
            
        self.send_auth_request()
        return False

    def send_auth_request(self):
        self.send_response(401)
        # Sử dụng SESSION_REALM động để trình duyệt không nhớ mật khẩu cũ
        self.send_header('WWW-Authenticate', f'Basic realm="{SESSION_REALM}"')
        # 2. FORCE CLOSE: Bắt buộc trình duyệt ngắt kết nối ngay khi sai pass
        # Điều này giúp hiện lại bảng nhập ngay lập tức thay vì bị treo
        self.send_header('Connection', 'close') 
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Login Required</h1><p>Please enter username and password.</p>')
    # ----------------------------

    def do_GET(self):
        # Bọc toàn bộ trong try/except để xử lý timeout
        try:
            if not self.check_auth():
                return

            if self.path == '/':
                content = PAGE_HOME.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                
            elif self.path == '/wifi':
                content = PAGE_WIFI.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)

            elif self.path == '/stream.mjpg':
                self.send_response(200)
                self.send_header('Age', 0)
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
                self.end_headers()
                try:
                    while True:
                        # Reset timeout cho stream (stream cần chạy lâu dài)
                        self.request.settimeout(None) 
                        
                        with state.streaming_output.condition:
                            state.streaming_output.condition.wait()
                            frame = state.streaming_output.frame
                        
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                except Exception as e:
                    pass
            else:
                self.send_error(404)
                self.end_headers()
        except socket.timeout:
            # Nếu kết nối bị treo quá 5s (ví dụ lúc nhập pass), nó sẽ tự ngắt
            pass
        except Exception as e:
            pass

    def do_POST(self):
        try:
            if not self.check_auth():
                return

            if self.path == '/shutdown':
                content = PAGE_SHUTDOWN.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)
                
                def perform_shutdown():
                    print("[SYSTEM] Shutting down in 2 seconds...")
                    time.sleep(2)
                    os.system('sudo poweroff')
                    
                Thread(target=perform_shutdown).start()
                return
                
            if self.path == '/reboot':
                content = PAGE_REBOOT.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)

                def perform_reboot():
                    print("[SYSTEM] Rebooting in 2 seconds...")
                    time.sleep(2)
                    os.system('sudo reboot')

                Thread(target=perform_reboot).start()
                return            

            if self.path == '/set_wifi':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode('utf-8')
                
                params = urllib.parse.parse_qs(post_data)
                ssid = params.get('ssid', [''])[0]
                password = params.get('password', [''])[0]

                if ssid and password:
                    try:
                        print(f"[WIFI] Scanning networks to find '{ssid}'...")
                        subprocess.run(["sudo", "nmcli", "device", "wifi", "rescan"], check=False)
                        time.sleep(3) 
                    except Exception as e:
                        print(f"[SCAN ERROR] {e}")

                    success, msg = wifi_manager.save_wifi_config(ssid, password)
                    
                    if success:
                        response_content = PAGE_SUCCESS_TEMPLATE.format(style=COMMON_STYLE, msg=msg).encode('utf-8')
                        def reboot_later():
                            time.sleep(2)
                            pass 
                        Thread(target=reboot_later).start()
                    else:
                        response_content = PAGE_ERROR_TEMPLATE.format(style=COMMON_STYLE, msg=msg).encode('utf-8')

                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(response_content)
                else:
                    self.send_error(400, "Missing Wifi Information")
        except Exception:
            pass

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
