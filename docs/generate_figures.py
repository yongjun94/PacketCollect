from pathlib import Path
from html import escape
import subprocess
import shutil

OUT=Path(__file__).parent/'images'
OUT.mkdir(parents=True, exist_ok=True)
NAVY='#153451'; BLUE='#2463a0'; GRAY='#52657a'; LINE='#d9e3ed'; GREEN='#167b63'
class Svg:
 def __init__(self,w,h,title):
  self.w,self.h=w,h;self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title><defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0 0 L9 4.5 L0 9Z" fill="#6c8299"/></marker></defs><rect width="100%" height="100%" fill="#f4f7fb"/>']
 def rect(self,x,y,w,h,fill='white',stroke=LINE,r=14):self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>')
 def text(self,x,y,t,size=18,color=NAVY,weight=400):self.parts.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(t)}</text>')
 def lines(self,x,y,ls,size=17,color=GRAY,gap=26):
  for i,t in enumerate(ls):self.text(x,y+i*gap,t,size,color)
 def line(self,x,y,a,b,arrow=False):self.parts.append(f'<path d="M{x} {y} L{a} {b}" fill="none" stroke="#6c8299" stroke-width="2"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>')
 def badge(self,x,y,n):self.parts.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{BLUE}"/>');self.text(x-5,y+6,str(n),16,'white',700)
 def save(self,name):
  p=OUT/(name+'.svg');p.write_text(''.join(self.parts)+'</svg>');print(p)
  if shutil.which('inkscape'):
   subprocess.run(['inkscape',str(p),'--export-type=png','--export-filename='+str(OUT/(name+'.png'))],check=True,capture_output=True)

s=Svg(1440,930,'HTTP Capture desktop architecture: Windows and macOS')
s.text(46,60,'HTTP Capture / desktop architecture',32,weight=700)
s.text(46,94,'Windows x64 + Apple Silicon macOS. Mobile development discontinued.',18,GRAY)
s.rect(40,130,1360,110,'#eaf2fc')
s.text(65,169,'PROXY-AWARE DESKTOP BROWSER / APP',21,BLUE,700)
s.text(65,207,'OS HTTP/HTTPS proxy -> 127.0.0.1:8877 -> destination via mitmproxy',18)
s.line(720,245,720,275,True)
s.rect(40,280,1360,130)
s.text(65,319,'BUNDLED PYTHON / MITMPROXY ENGINE',21,BLUE,700)
s.lines(65,353,['Windows: WinINet + current-user CA | macOS: networksetup + Keychain',
                  'Forwards requests/responses; writes body files and emits session events.'],18,gap=28)
s.line(720,415,720,445,True)
s.rect(40,450,1360,108)
s.text(65,489,'SHARED FLUTTER DESKTOP UI + LOCAL STDIO JSON IPC',21,BLUE,700)
s.text(65,525,'Start / Pause / Stop / settings / session inspection / export',18)
s.line(720,563,720,593,True)
s.rect(40,598,1360,108)
s.text(65,637,'CAPTURE CORE / packages/capture_core',21,BLUE,700)
s.text(65,673,'CaptureSession + SQLite metadata + local binary body files',18)
s.line(720,711,720,741,True)
s.rect(40,746,1360,105)
s.text(65,785,'CAPTURE EXPORT / packages/capture_export',21,BLUE,700)
s.text(65,820,'SAZ: ZIP + HTTP messages + XML | HAR 1.2: entries + content + timings',18)
s.text(46,895,'Data-flow schematic. Not a full TCP/UDP sniffer; app trust/proxy policies still apply.',17,GRAY)
s.save('architecture')

s=Svg(1440,1030,'Desktop interface schematic with actual controls and synthetic sessions')
s.text(42,56,'Desktop UI / reading a capture',31,weight=700);s.text(42,87,'Windows and macOS share this Flutter screen.',18,GRAY)
s.rect(38,120,1035,810);s.rect(38,120,1035,62,'#eaf2fc');s.text(63,160,'HTTP Capture',25,weight=700);s.text(958,158,'Settings',17,BLUE)
buttons=[('Start',False,94),('Pause',True,100),('Stop',True,90),('Clear',False,85),('Export SAZ',False,145),('Export HAR',False,145)]
x=60
for label,on,w in buttons:
 s.rect(x,205,w,42,'#f7faff' if on else '#f0f2f5',LINE,20);s.text(x+15,233,label,16,BLUE if on else '#8794a4',600);x+=w+10
s.rect(60,265,760,47,'white',LINE,9);s.text(80,296,'Filter method, URL, status',17,'#738397')
s.rect(60,330,990,44,'#eaf3ee',r=4);s.text(78,359,'●  Capturing · 127.0.0.1:8877 · 3 sessions',18,GREEN)
cols=[(76,'ID'),(175,'Status'),(265,'Method'),(365,'Host'),(550,'URL'),(860,'Size'),(960,'Time')]
for x,t in cols:s.text(x,410,t,16,GRAY,700)
rows=[['a12b34cd','200','GET','example.test','https://example.test/','1.2 KB','sample'],['b23c45de','200','POST','api.example.test','https://api.example.test/items','84 B','sample'],['c34d56ef','302','GET','example.test','https://example.test/next','0 B','sample']]
for i,row in enumerate(rows):
 y=428+i*49;s.rect(60,y,990,46,'#dceafa' if i==1 else '#fff',r=3)
 for (x,_),t in zip(cols,row):s.text(x,y+29,t,14)
s.line(60,595,1050,595);s.text(100,632,'Request',18,GRAY);s.text(320,632,'Response',18,BLUE,700);s.line(280,647,455,647)
s.text(78,689,'HTTP/1.1 · complete',17,GRAY);s.text(78,726,'Content-Type: application/json',17);s.text(78,757,'Content-Length: 84',17);s.line(78,777,1025,777)
s.text(78,811,'84 bytes · raw entity bytes',16,GRAY);s.text(78,848,'{ "result": "illustrative response" }',18)
notes=[('Capture controls','Start, pause/resume and stop.','Export and Clear require Stop.'),('Connection state','Listener address and session count.','A green status alone is not proof of traffic.'),('Session list','Filter and choose a stored session.','Desktop uses paged list loading.'),('Inspector','Request / Response tabs show headers','and a body preview (up to 64 KiB).'),('Settings','Proxy port, HTTPS, CA management','and OS proxy controls.')]
for i,(title,a,b) in enumerate(notes):
 y=180+i*140;s.badge(1110,y,i+1);s.text(1136,y+6,title,17,BLUE,700);s.lines(1100,y+39,[a,b],13,gap=22)
for x,y,n in [(1034,225,1),(1034,351,2),(1034,457,3),(1034,688,4),(1041,150,5)]:s.badge(x,y,n)
s.text(42,982,'DOCUMENTATION SCHEMATIC · synthetic example.test traffic and sizes · not a runtime screenshot or benchmark',15,GRAY)
s.save('desktop-ui')

