from pathlib import Path

p = Path('scripts/kwai_phone_remote.py')
s = p.read_text()

s = s.replace(
    'import base64\nimport io\nimport json\nimport os\nimport re\nimport subprocess\nimport threading\nimport time\n',
    'import base64\nimport hashlib\nimport hmac\nimport io\nimport json\nimport os\nimport re\nimport secrets\nimport subprocess\nimport threading\nimport time\n',
    1,
)

s = s.replace(
    'CONTROL_KEY_B64 = base64.urlsafe_b64encode(CONTROL_KEY).decode().rstrip("=")\nLOCK = threading.Lock()\nDEADLINE = time.monotonic() + 1500\n\nPAGE = r\'\'\'',
    'CONTROL_KEY_B64 = base64.urlsafe_b64encode(CONTROL_KEY).decode().rstrip("=")\nAUTH_HASH = "0644b3e91ed4d38920eaf999febbf37bd552f86b3f0fbd99dda542d154503b14"\nSESSION_TOKEN = secrets.token_urlsafe(32)\nLOCK = threading.Lock()\nDEADLINE = time.monotonic() + 1500\n\nLOGIN_PAGE = r\'\'\'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Kwai — acesso protegido</title>\n<style>body{font:16px system-ui;background:#151820;color:white;max-width:420px;margin:60px auto;padding:20px}input,button{font:inherit;width:100%;padding:12px;margin:8px 0;box-sizing:border-box}button{cursor:pointer}</style>\n<h2>Kwai — acesso protegido</h2>\n<p>Digite a senha temporária desta sessão.</p>\n<form method="post" action="/login"><input name="password" type="password" autocomplete="current-password" required autofocus><button type="submit">Entrar</button></form>\n\'\'\'\n\nPAGE = r\'\'\'',
    1,
)

s = s.replace(
    'Brasil (+55) já é selecionado automaticamente. O controle usa requisições GET com payload criptografado para funcionar dentro do túnel protegido.',
    'Brasil (+55) já é selecionado automaticamente. O acesso usa uma sessão protegida própria e os comandos continuam criptografados no navegador.',
    1,
)

needle = '''class Handler(BaseHTTPRequestHandler):\n    def log_message(self, *args):\n        pass\n\n'''
insert = '''class Handler(BaseHTTPRequestHandler):\n    def log_message(self, *args):\n        pass\n\n    def authenticated(self):\n        cookie = self.headers.get("Cookie", "")\n        for item in cookie.split(";"):\n            name, sep, value = item.strip().partition("=")\n            if sep and name == "kwai_session":\n                return hmac.compare_digest(value, SESSION_TOKEN)\n        return False\n\n'''
if needle not in s:
    raise SystemExit('handler marker not found')
s = s.replace(needle, insert, 1)

old = '''        if path == "/":\n            return self.reply(200, PAGE.replace("__CONTROL_KEY__", CONTROL_KEY_B64), "text/html; charset=utf-8")\n        if path == "/health":\n            return self.reply(200, "ready")\n        if path == "/screen":\n'''
new = '''        if path == "/health":\n            return self.reply(200, "ready")\n        if path == "/":\n            if not self.authenticated():\n                return self.reply(200, LOGIN_PAGE, "text/html; charset=utf-8")\n            return self.reply(200, PAGE.replace("__CONTROL_KEY__", CONTROL_KEY_B64), "text/html; charset=utf-8")\n        if path in ("/screen", "/cmd") and not self.authenticated():\n            return self.reply(401, "Autenticação necessária.")\n        if path == "/screen":\n'''
if old not in s:
    raise SystemExit('GET auth marker not found')
s = s.replace(old, new, 1)

old_post = '''    def do_POST(self):\n        return self.reply(405, "Método não permitido.")\n'''
new_post = '''    def do_POST(self):\n        if time.monotonic() > DEADLINE:\n            return self.reply(410, "Sessão encerrada.")\n        parsed = urlparse(self.path)\n        if parsed.path != "/login":\n            return self.reply(405, "Método não permitido.")\n        try:\n            length = int(self.headers.get("Content-Length", "0"))\n            if length < 1 or length > 1024:\n                raise ValueError\n            body = self.rfile.read(length).decode("utf-8")\n            values = parse_qs(body, keep_blank_values=False)\n            password = values.get("password", [""])[0]\n            digest = hashlib.sha256(password.encode("utf-8")).hexdigest()\n            if not hmac.compare_digest(digest, AUTH_HASH):\n                return self.reply(403, LOGIN_PAGE.replace("</form>", "</form><p>Senha incorreta.</p>"), "text/html; charset=utf-8")\n            self.send_response(303)\n            self.send_header("Location", "/")\n            self.send_header("Set-Cookie", f"kwai_session={SESSION_TOKEN}; Path=/; Max-Age=1800; HttpOnly; Secure; SameSite=Strict")\n            self.send_header("Cache-Control", "no-store")\n            self.end_headers()\n        except Exception:\n            return self.reply(400, "Login inválido.")\n'''
if old_post not in s:
    raise SystemExit('POST marker not found')
s = s.replace(old_post, new_post, 1)

s = s.replace(
    '# Loopback-only Android viewer; expose only behind verified email authentication.',
    '# Loopback-only Android viewer; expose through an HTTPS tunnel with app-level authentication.',
    1,
)

p.write_text(s)
