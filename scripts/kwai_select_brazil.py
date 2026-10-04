"""Select Brazil via the legitimate country picker before remote interaction."""
import subprocess
import time
import re
import xml.etree.ElementTree as ET

def adb(*args):
    return subprocess.run(['adb',*args],check=True,stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL,timeout=45).stdout.decode(errors='replace')

def nodes():
    adb('shell','rm','-f','/sdcard/kwai-country.xml')
    adb('shell','uiautomator','dump','/sdcard/kwai-country.xml')
    xml=adb('shell','cat','/sdcard/kwai-country.xml')
    adb('shell','rm','-f','/sdcard/kwai-country.xml')
    return list(ET.fromstring(xml).iter('node'))

def tap(node):
    x1,y1,x2,y2=map(int,re.findall(r'\d+',node.attrib['bounds']))
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
    time.sleep(1)

def code_node(items):
    return next((n for n in items if n.attrib.get('resource-id','').endswith('/tv_country_code')),None)

items=nodes()
code=code_node(items)
if code is None:
    raise SystemExit('country_selector_not_visible')
if '+55' not in code.attrib.get('text',''):
    tap(code)
    selected=False
    for attempt in range(14):
        items=nodes()
        brazil=next((n for n in items if re.fullmatch(r'(?:Brazil|Brasil)(?:\s*\(?\+?55\)?)?',n.attrib.get('text','').strip(),re.I)),None)
        if brazil is not None:
            tap(brazil)
            selected=True
            break
        # Only scroll the country picker; do not type or submit any login data.
        adb('shell','input','swipe','540','1850','540','650','450')
        time.sleep(0.5)
    if not selected:
        raise SystemExit('brazil_not_found_in_country_picker')
items=nodes()
code=code_node(items)
if code is None or '+55' not in code.attrib.get('text',''):
    raise SystemExit('brazil_selection_not_confirmed')
field=next((n for n in items if n.attrib.get('class')=='android.widget.EditText' and n.attrib.get('package')=='com.kwai.kuaishou.video.live'),None)
if field is not None:tap(field)
print('brazil_country_code_confirmed=true')
