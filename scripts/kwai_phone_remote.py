# Loopback-only Android viewer; expose only behind verified email authentication.
import base64
import io
import json
import os
import re
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from PIL import Image

PKG = "com.kwai.kuaishou.video.live"
CONTROL_KEY = os.urandom(32)
CONTROL_KEY_B64 = base64.urlsafe_b64encode(CONTROL_KEY).decode().rstrip("=")
LOCK = threading.Lock()
DEADLINE = time.monotonic() + 1500

PAGE = r'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Kwai — login protegido</title>
<style>
body{font:16px system-ui;background:#151820;color:white;max-width:550px;margin:auto;padding:16px}
button,input{font:inherit;padding:12px;margin:4px 0;box-sizing:border-box;max-width:100%}
button{cursor:pointer;min-height:46px}
#screen{width:100%;max-height:70vh;object-fit:contain;touch-action:none;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none;border-radius:8px;background:#000}
p{line-height:1.4}.row{display:flex;gap:8px;flex-wrap:wrap}.row button{flex:1 1 120px}
#status{color:#ffd69b;min-height:24px}#number{width:100%;font-size:20px}
</style>
<h2>Kwai — login por telefone</h2>
<p>Brasil (+55) já é selecionado automaticamente. O controle usa requisições GET com payload criptografado para funcionar dentro do túnel protegido.</p>
<img id="screen" draggable="false" alt="Tela ao vivo do Android"><p id="status">Carregando...</p>
<form id="digits">
  <input id="number" type="tel" inputmode="numeric" autocomplete="off" placeholder="Telefone ou código recebido" pattern="[0-9+ ]{1,30}" required>
  <div class="row"><button type="submit">Digitar no Kwai</button><button id="focus" type="button">Focar campo do Kwai</button></div>
</form>
<div class="row"><button id="back" type="button">Voltar</button><button id="refresh" type="button">Atualizar tela</button><button id="scroll" type="button">Rolar lista</button></div>
<hr><h3>Guardar os dados após entrar</h3>
<p>Quando o Kwai mostrar sua conta, defina uma senha com pelo menos 16 caracteres e baixe o backup criptografado. Guarde a senha: ela não será salva.</p>
<form id="backup"><input id="pass" type="password" autocomplete="new-password" minlength="16" required placeholder="Senha do backup (16+ caracteres)"><button>Baixar backup criptografado</button></form>
<p>O backup interrompe o Kwai para copiar seus dados. Não feche esta página antes de o download terminar.</p>
<script>
const screen=document.querySelector('#screen'), status=document.querySelector('#status');
const keyText='__CONTROL_KEY__';
let busy=false,refreshing=false;
function say(t){status.textContent=t}
function b64url(bytes){let s='';for(const b of bytes)s+=String.fromCharCode(b);return btoa(s).replaceAll('+','-').replaceAll('/','_').replaceAll('=','')}
function keyBytes(){let s=keyText.replaceAll('-','+').replaceAll('_','/');while(s.length%4)s+='=';const raw=atob(s),out=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)out[i]=raw.charCodeAt(i);return out}
const keyPromise=crypto.subtle.importKey('raw',keyBytes(),{name:'AES-GCM'},false,['encrypt']);
async function pack(data){
  data.ts=Date.now();
  const iv=crypto.getRandomValues(new Uint8Array(12));
  const key=await keyPromise;
  const plain=new TextEncoder().encode(JSON.stringify(data));
  const enc=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},key,plain));
  return b64url(iv)+'.'+b64url(enc);
}
async function call(data){
  if(busy)throw Error('Aguarde a operação anterior.');
  busy=true;
  try{
    const q=await pack(data);
    const r=await fetch('/cmd?q='+encodeURIComponent(q)+'&n='+Date.now(),{method:'GET',cache:'no-store',credentials:'include',signal:AbortSignal.timeout(20000)});
    if(!r.ok)throw Error(await r.text());
    return r;
  }finally{busy=false}
}
async function navigateCommand(data){
  if(busy)throw Error('Aguarde a operação anterior.');
  busy=true;
  try{
    const q=await pack(data);
    window.location.assign('/cmd?nav=1&q='+encodeURIComponent(q)+'&n='+Date.now());
  }catch(err){busy=false;throw err}
}
async function refresh(){
  if(busy||refreshing)return;
  refreshing=true;
  try{
    const r=await fetch('/screen?ts='+Date.now(),{cache:'no-store',credentials:'include',signal:AbortSignal.timeout(15000)});
    if(!r.ok)throw Error('Sessão indisponível');
    const b=await r.blob(),old=screen.src;
    screen.src=URL.createObjectURL(b);
    await screen.decode();
    if(old.startsWith('blob:'))URL.revokeObjectURL(old);
    say('Conectado — toque na tela ou use o campo abaixo');
  }catch(e){say('Aguardando atualização da tela...')}finally{refreshing=false}
}
async function tapScreen(e){
  e.preventDefault();if(busy)return;
  const r=screen.getBoundingClientRect(),scale=Math.min(r.width/screen.naturalWidth,r.height/screen.naturalHeight);
  const w=screen.naturalWidth*scale,h=screen.naturalHeight*scale;
  const x=e.clientX-r.left-(r.width-w)/2,y=e.clientY-r.top-(r.height-h)/2;
  if(x<0||y<0||x>w||y>h)return;
  try{say('Enviando toque...');await navigateCommand({op:'tap',fx:x/w,fy:y/h})}catch(err){say(err.message)}
}
screen.addEventListener('pointerup',tapScreen,{passive:false});
screen.addEventListener('contextmenu',e=>e.preventDefault());
screen.addEventListener('dragstart',e=>e.preventDefault());
document.querySelector('#digits').onsubmit=async e=>{
  e.preventDefault();const n=document.querySelector('#number'),value=n.value;
  try{say('Focando o campo e digitando...');n.value='';await navigateCommand({op:'digits',value})}catch(err){say(err.message)}
};
document.querySelector('#focus').onclick=async()=>{try{say('Localizando campo do Kwai...');await navigateCommand({op:'focus'})}catch(err){say(err.message)}};
document.querySelector('#scroll').onclick=async()=>{try{await navigateCommand({op:'scroll'})}catch(err){say(err.message)}};
document.querySelector('#back').onclick=async()=>{try{await navigateCommand({op:'back'})}catch(err){say(err.message)}};
document.querySelector('#refresh').onclick=refresh;
document.querySelector('#backup').onsubmit=async e=>{
  e.preventDefault();const p=document.querySelector('#pass');
  try{
    say('Preparando backup criptografado...');
    const r=await call({op:'backup',passphrase:p.value});
    p.value='';
    const u=URL.createObjectURL(await r.blob()),a=document.createElement('a');
    a.href=u;a.download='kwai-session-encrypted.bin';a.click();
    setTimeout(()=>URL.revokeObjectURL(u),60000);
    say('Backup baixado. Guarde a senha e avise no chat apenas que concluiu.');
  }catch(err){say(err.message)}
};
async function loop(){await refresh();setTimeout(loop,1800)}loop();
</script>'''

def adb(*args, timeout=30):
    return subprocess.run(
        ["adb", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
    ).stdout

def screen_size():
    try:
        out = adb("shell", "wm", "size").decode(errors="replace")
        matches = re.findall(r"(\d+)x(\d+)", out)
        if matches:
            return tuple(map(int, matches[-1]))
    except Exception:
        pass
    return 1080, 2400

def ui_nodes():
    path = "/sdcard/kwai-remote-ui.xml"
    adb("shell", "rm", "-f", path)
    adb("shell", "uiautomator", "dump", path, timeout=45)
    xml = adb("shell", "cat", path, timeout=45).decode(errors="replace")
    adb("shell", "rm", "-f", path)
    return list(ET.fromstring(xml).iter("node"))

def tap_node(node):
    nums = list(map(int, re.findall(r"\d+", node.attrib.get("bounds", ""))))
    if len(nums) != 4:
        raise RuntimeError("Campo sem coordenadas.")
    x1, y1, x2, y2 = nums
    adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
    time.sleep(0.35)

def focus_edit_text():
    fields = [
        n for n in ui_nodes()
        if n.attrib.get("class") == "android.widget.EditText"
        and n.attrib.get("package") == PKG
        and n.attrib.get("enabled", "true") == "true"
    ]
    if not fields:
        raise RuntimeError("Campo de telefone/código não encontrado.")
    field = next((n for n in fields if n.attrib.get("focused") == "true"), fields[0])
    tap_node(field)

def b64d(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def decode_command(raw):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    left, sep, right = raw.partition(".")
    if not sep:
        raise ValueError("Comando inválido.")
    iv, ciphertext = b64d(left), b64d(right)
    if len(iv) != 12 or len(ciphertext) > 4096:
        raise ValueError("Comando inválido.")
    plain = AESGCM(CONTROL_KEY).decrypt(iv, ciphertext, None)
    data = json.loads(plain.decode("utf-8"))
    ts = int(data.get("ts", 0))
    if abs(int(time.time() * 1000) - ts) > 120000:
        raise ValueError("Comando expirado.")
    return data

def encrypted_backup(passphrase):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    if len(passphrase) < 16 or len(passphrase) > 256:
        raise ValueError("A senha deve ter entre 16 e 256 caracteres.")
    adb("shell", "am", "force-stop", PKG)
    adb("root")
    adb("wait-for-device")
    raw = adb("exec-out", "tar", "-C", "/data/user/0/" + PKG, "-cf", "-", ".", timeout=180)
    if len(raw) < 1024:
        raise RuntimeError("Backup vazio; tente novamente.")
    salt, nonce = os.urandom(16), os.urandom(12)
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
    header = b"KWAI-APPDATA-V1\n" + salt + nonce
    result = header + AESGCM(key).encrypt(nonce, raw, header)
    del raw, key
    return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body, typ="text/plain; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def redirect_root(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self):
        if time.monotonic() > DEADLINE:
            return self.reply(410, "Sessão encerrada.")
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            return self.reply(200, PAGE.replace("__CONTROL_KEY__", CONTROL_KEY_B64), "text/html; charset=utf-8")
        if path == "/health":
            return self.reply(200, "ready")
        if path == "/screen":
            try:
                with LOCK:
                    png = adb("exec-out", "screencap", "-p")
                frame = Image.open(io.BytesIO(png)).convert("RGB")
                frame.thumbnail((540, 1200))
                out = io.BytesIO()
                frame.save(out, format="JPEG", quality=70)
                return self.reply(200, out.getvalue(), "image/jpeg")
            except Exception:
                return self.reply(503, "Android indisponível.")
        if path == "/cmd":
            try:
                values = parse_qs(parsed.query, keep_blank_values=False).get("q", [])
                if len(values) != 1 or len(values[0]) > 6000:
                    raise ValueError("Comando inválido.")
                data = decode_command(values[0])
                op = data.get("op")
                with LOCK:
                    if op == "tap":
                        fx, fy = float(data["fx"]), float(data["fy"])
                        if not (0 <= fx <= 1 and 0 <= fy <= 1):
                            raise ValueError("Toque fora da tela.")
                        w, h = screen_size()
                        x = min(w - 1, max(0, round(fx * w)))
                        y = min(h - 1, max(0, round(fy * h)))
                        adb("shell", "input", "tap", str(x), str(y))
                    elif op == "focus":
                        focus_edit_text()
                    elif op == "digits":
                        value = data["value"]
                        if not re.fullmatch(r"[0-9+ ]{1,30}", value):
                            raise ValueError("Use apenas números, espaços ou +.")
                        focus_edit_text()
                        adb("shell", "input", "text", value.replace(" ", "%s"))
                    elif op == "scroll":
                        w, h = screen_size()
                        adb("shell", "input", "swipe", str(w // 2), str(int(h * 0.78)), str(w // 2), str(int(h * 0.30)), "400")
                    elif op == "back":
                        adb("shell", "input", "keyevent", "4")
                    elif op == "backup":
                        blob = encrypted_backup(data["passphrase"])
                        return self.reply(200, blob, "application/octet-stream")
                    else:
                        raise ValueError("Comando inválido.")
                if parse_qs(parsed.query).get("nav") == ["1"]:
                    return self.redirect_root()
                return self.reply(200, "ok")
            except ValueError as exc:
                return self.reply(400, str(exc))
            except Exception:
                return self.reply(503, "Operação não concluída. Tente novamente.")
        return self.reply(404, "Não encontrado.")

    def do_POST(self):
        return self.reply(405, "Método não permitido.")

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 6080), Handler).serve_forever()
