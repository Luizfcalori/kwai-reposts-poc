from pathlib import Path

p = Path('scripts/kwai_phone_remote.py')
s = p.read_text()

old = """async function call(data){
  if(busy)throw Error('Aguarde a operação anterior.');
  busy=true;
  try{
    const q=await pack(data);
    const r=await fetch('/cmd?q='+encodeURIComponent(q)+'&n='+Date.now(),{method:'GET',cache:'no-store',credentials:'include',signal:AbortSignal.timeout(20000)});
    if(!r.ok)throw Error(await r.text());
    return r;
  }finally{busy=false}
}"""
new = """async function call(data){
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
}"""
if old not in s and 'async function navigateCommand(data)' not in s:
    raise SystemExit('call block not found')
if 'async function navigateCommand(data)' not in s:
    s = s.replace(old, new, 1)

old_digits = """e.preventDefault();const n=document.querySelector('#number');
  try{say('Focando o campo e digitando...');await call({op:'digits',value:n.value});n.value='';say('Texto enviado ao Kwai.');setTimeout(refresh,300)}catch(err){say(err.message)}"""
new_digits = """e.preventDefault();const n=document.querySelector('#number'),value=n.value;
  try{say('Focando o campo e digitando...');n.value='';await navigateCommand({op:'digits',value})}catch(err){say(err.message)}"""
if old_digits in s:
    s = s.replace(old_digits, new_digits, 1)

replacements = {
    "await call({op:'tap',fx:x/w,fy:y/h});setTimeout(refresh,300)": "await navigateCommand({op:'tap',fx:x/w,fy:y/h})",
    "await call({op:'focus'});say('Campo do Kwai focado.');setTimeout(refresh,250)": "await navigateCommand({op:'focus'})",
    "await call({op:'scroll'});setTimeout(refresh,300)": "await navigateCommand({op:'scroll'})",
    "await call({op:'back'});setTimeout(refresh,300)": "await navigateCommand({op:'back'})",
}
for old_text, new_text in replacements.items():
    if old_text in s:
        s = s.replace(old_text, new_text, 1)

marker = """    def reply(self, code, body, typ=\"text/plain; charset=utf-8\"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header(\"Content-Type\", typ)
        self.send_header(\"Content-Length\", str(len(body)))
        self.send_header(\"Cache-Control\", \"no-store\")
        self.send_header(\"Pragma\", \"no-cache\")
        self.send_header(\"X-Content-Type-Options\", \"nosniff\")
        self.send_header(\"X-Frame-Options\", \"DENY\")
        self.send_header(\"Referrer-Policy\", \"no-referrer\")
        self.end_headers()
        self.wfile.write(body)
"""
add = marker + """
    def redirect_root(self):
        self.send_response(303)
        self.send_header(\"Location\", \"/\")
        self.send_header(\"Cache-Control\", \"no-store\")
        self.end_headers()
"""
if 'def redirect_root' not in s:
    if marker not in s:
        raise SystemExit('reply block not found')
    s = s.replace(marker, add, 1)

old_success = '                return self.reply(200, "ok")\n'
new_success = """                if parse_qs(parsed.query).get(\"nav\") == [\"1\"]:
                    return self.redirect_root()
                return self.reply(200, \"ok\")
"""
if old_success in s:
    s = s.replace(old_success, new_success, 1)
elif 'return self.redirect_root()' not in s:
    raise SystemExit('success reply not found')

p.write_text(s)
