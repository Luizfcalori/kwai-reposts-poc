# Loopback-only Android viewer; expose only behind verified email authentication.
import json
import io
from PIL import Image
import os
import re
import secrets
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PKG = 'com.kwai.kuaishou.video.live'
CSRF = secrets.token_urlsafe(32)
LOCK = threading.Lock()
DEADLINE = time.monotonic() + 1500
PAGE = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
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
<p>Brasil (+55) já é selecionado automaticamente. Para digitar, use o campo abaixo: o sistema localiza e foca o campo correto no Kwai antes de enviar os números.</p>
<img id="screen" draggable="false" alt="Tela ao vivo do Android"><p id="status">Carregando...</p>
<form id="digits">
  <input id="number" type="tel" inputmode="numeric" autocomplete="off" placeholder="Telefone ou código recebido" pattern="[0-9+ ]{1,30}" required>
  <div class="row"><button id="send" type="submit">Digitar no Kwai</button><button id="focus" type="button">Focar campo do Kwai</button></div>
</form>
<div class="row"><button id="back" type="button">Voltar</button><button id="refresh" type="button">Atualizar tela</button><button id="scroll" type="button">Rolar lista</button></div>
<hr><h3>Guardar os dados após entrar</h3>
<p>Quando o Kwai mostrar sua conta, defina uma senha com pelo menos 16 caracteres e baixe o backup criptografado. Guarde a senha: ela não será salva. A restauração do login ainda precisa de teste.</p>
<form id="backup"><input id="pass" type="password" autocomplete="new-password" minlength="16" required placeholder="Senha do backup (16+ caracteres)"><button>Baixar backup criptografado</button></form>
<p>O backup interrompe o Kwai para copiar seus dados. Não feche esta página antes de o download terminar.</p>
<script>
const token='__CSRF__', screen=document.querySelector('#screen'), status=document.querySelector('#status');
let busy=false, refreshing=false;
function say(t){status.textContent=t;}
async function call(path,data){
  if(busy) throw Error('Aguarde a operação anterior.');
  busy=true;
  try{
    const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Kwai-CSRF':token},body:JSON.stringify(data),cache:'no-store'});
    if(!r.ok)throw Error(await r.text());
    return r;
  }finally{busy=false;}
}
async function refresh(){
  if(busy||refreshing)return;
  refreshing=true;
  try{
    const r=await fetch('/screen?ts='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(15000)});
    if(!r.ok)throw Error('Sessão indisponível');
    const b=await r.blob(),old=screen.src;
    screen.src=URL.createObjectURL(b);
    await screen.decode();
    if(old.startsWith('blob:'))URL.revokeObjectURL(old);
    say('Conectado — toque na tela ou use o campo abaixo');
  }catch(e){say('Aguardando atualização da tela...');}
  finally{refreshing=false;}
}
async function tapScreen(e){
  e.preventDefault();
  if(busy)return;
  const r=screen.getBoundingClientRect();
  const scale=Math.min(r.width/screen.naturalWidth,r.height/screen.naturalHeight);
  const w=screen.naturalWidth*scale,h=screen.naturalHeight*scale;
  const x=e.clientX-r.left-(r.width-w)/2,y=e.clientY-r.top-(r.height-h)/2;
  if(x<0||y<0||x>w||y>h)return;
  try{
    say('Enviando toque...');
    await call('/tap',{fx:x/w,fy:y/h});
    setTimeout(refresh,350);
  }catch(err){say(err.message);}
}
screen.addEventListener('pointerup',tapScreen,{passive:false});
screen.addEventListener('contextmenu',e=>e.preventDefault());
screen.addEventListener('dragstart',e=>e.preventDefault());

document.querySelector('#digits').onsubmit=async e=>{
  e.preventDefault();
  const n=document.querySelector('#number');
  try{
    say('Focando o campo e digitando...');
    await call('/digits',{value:n.value});
    n.value='';
    say('Texto enviado ao Kwai.');
    setTimeout(refresh,350);
  }catch(err){say(err.message);}
};
document.querySelector('#focus').onclick=async()=>{
  try{say('Localizando campo do Kwai...');await call('/focus',{});say('Campo do Kwai focado.');setTimeout(refresh,300);}
  catch(err){say(err.message);}
};
document.querySelector('#scroll').onclick=async()=>{try{await call('/scroll',{});setTimeout(refresh,350)}catch(err){say(err.message)}};
document.querySelector('#back').onclick=async()=>{try{await call('/back',{});setTimeout(refresh,350)}catch(err){say(err.message)}};
document.querySelector('#refresh').onclick=refresh;
document.querySelector('#backup').onsubmit=async e=>{
  e.preventDefault();busy=true;say('Preparando backup criptografado...');
  try{
    const p=document.querySelector('#pass');
    const r=await fetch('/backup',{method:'POST',headers:{'Content-Type':'application/json','X-Kwai-CSRF':token},body:JSON.stringify({passphrase:p.value})});
    if(!r.ok)throw Error(await r.text());
    p.value='';
    const u=URL.createObjectURL(await r.blob()),a=document.createElement('a');
    a.href=u;a.download='kwai-session-encrypted.bin';a.click();
    setTimeout(()=>URL.revokeObjectURL(u),60000);
    say('Backup baixado. Guarde a senha e avise no chat apenas que concluiu.');
  }catch(err){say(err.message);}finally{busy=false;}
};
async function loop(){await refresh();setTimeout(loop,1800)}loop();
</script>'''

def adb(*args, binary=False, timeout=30):
    return subprocess.run(['adb', *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, timeout=timeout).stdout

def screen_size():
    try:
        out = adb('shell', 'wm', 'size').decode(errors='replace')
        matches = re.findall(r'(\d+)x(\d+)', out)
        if matches:
            return tuple(map(int, matches[-1]))
    except Exception:
        pass
    return 1080, 2400

def ui_nodes():
    path = '/sdcard/kwai-remote-ui.xml'
    adb('shell', 'rm', '-f', path)
    adb('shell', 'uiautomator', 'dump', path, timeout=45)
    xml = adb('shell', 'cat', path, timeout=45).decode(errors='replace')
    adb('shell', 'rm', '-f', path)
    return list(ET.fromstring(xml).iter('node'))

def tap_node(node):
    nums = list(map(int, re.findall(r'\d+', node.attrib.get('bounds', ''))))
    if len(nums) != 4:
        raise RuntimeError('Campo sem coordenadas.')
    x1, y1, x2, y2 = nums
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))
    time.sleep(0.35)

def focus_edit_text():
    nodes = ui_nodes()
    fields = [
        n for n in nodes
        if n.attrib.get('class') == 'android.widget.EditText'
        and n.attrib.get('package') == PKG
        and n.attrib.get('enabled', 'true') == 'true'
    ]
    if not fields:
        raise RuntimeError('Campo de telefone/código não encontrado.')
    field = next((n for n in fields if n.attrib.get('focused') == 'true'), fields[0])
    tap_node(field)
    return True

def encrypted_backup(passphrase):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    if len(passphrase) < 16 or len(passphrase) > 256:
        raise ValueError('A senha deve ter entre 16 e 256 caracteres.')
    adb('shell', 'am', 'force-stop', PKG)
    adb('root')
    adb('wait-for-device')
    raw = adb('exec-out', 'tar', '-C', '/data/user/0/' + PKG, '-cf', '-', '.', timeout=180)
    if len(raw) < 1024:
        raise RuntimeError('Backup vazio; tente novamente.')
    salt, nonce = os.urandom(16), os.urandom(12)
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
    header = b'KWAI-APPDATA-V1\n' + salt + nonce
    result = header + AESGCM(key).encrypt(nonce, raw, header)
    del raw, key
    return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No URLs, input, screenshots, or account data in public job logs.

    def reply(self, code, body, typ='text/plain; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', typ)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if time.monotonic() > DEADLINE:
            return self.reply(410, 'Sessão encerrada.')
        path = urlparse(self.path).path
        if path == '/':
            return self.reply(200, PAGE.replace('__CSRF__', CSRF), 'text/html; charset=utf-8')
        if path == '/health':
            return self.reply(200, 'ready')
        if path == '/screen':
            try:
                with LOCK:
                    png = adb('exec-out', 'screencap', '-p')
                frame = Image.open(io.BytesIO(png)).convert('RGB')
                frame.thumbnail((540, 1200))
                out = io.BytesIO()
                frame.save(out, format='JPEG', quality=70)
                return self.reply(200, out.getvalue(), 'image/jpeg')
            except Exception:
                return self.reply(503, 'Android indisponível.')
        self.reply(404, 'Não encontrado.')

    def do_POST(self):
        if time.monotonic() > DEADLINE:
            return self.reply(410, 'Sessão encerrada.')
        if not secrets.compare_digest(self.headers.get('X-Kwai-CSRF', ''), CSRF):
            return self.reply(403, 'Acesso recusado.')
        origin = self.headers.get('Origin', '')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self.reply(403, 'Origem recusada.')
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048:
                return self.reply(400, 'Solicitação inválida.')
            data = json.loads(self.rfile.read(length))
            with LOCK:
                if self.path == '/tap':
                    fx, fy = float(data['fx']), float(data['fy'])
                    if not (0 <= fx <= 1 and 0 <= fy <= 1):
                        raise ValueError('Toque fora da tela.')
                    w, h = screen_size()
                    x = min(w - 1, max(0, round(fx * w)))
                    y = min(h - 1, max(0, round(fy * h)))
                    adb('shell', 'input', 'tap', str(x), str(y))
                elif self.path == '/focus':
                    focus_edit_text()
                elif self.path == '/digits':
                    value = data['value']
                    if not re.fullmatch(r'[0-9+ ]{1,30}', value):
                        raise ValueError('Use apenas números, espaços ou +.')
                    focus_edit_text()
                    adb('shell', 'input', 'text', value.replace(' ', '%s'))
                elif self.path == '/scroll':
                    w, h = screen_size()
                    adb('shell', 'input', 'swipe', str(w//2), str(int(h*0.78)), str(w//2), str(int(h*0.30)), '400')
                elif self.path == '/back':
                    adb('shell', 'input', 'keyevent', '4')
                elif self.path == '/backup':
                    blob = encrypted_backup(data['passphrase'])
                    return self.reply(200, blob, 'application/octet-stream')
                else:
                    return self.reply(404, 'Não encontrado.')
            self.reply(200, 'ok')
        except ValueError:
            self.reply(400, 'Entrada inválida. Confira os dados e o tamanho da senha.')
        except Exception:
            self.reply(503, 'Operação não concluída. Tente novamente.')

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 6080), Handler).serve_forever()
