from pathlib import Path
from html import escape
import subprocess

OUT=Path(__file__).parent/'images'
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
  p=OUT/(name+'.svg');p.write_text(''.join(self.parts)+'</svg>');subprocess.run(['inkscape',str(p),'--export-type=png','--export-filename='+str(OUT/(name+'.png'))],check=True,capture_output=True)

s=Svg(1440,1040,'HTTP Capture architecture: platform engines and shared Dart core')
s.text(46,60,'HTTP Capture / architecture',32,weight=700);s.text(46,93,'Platform-specific collection. Shared session storage and file export.',18,GRAY)
s.rect(40,125,665,405,'#eaf2fc');s.rect(735,125,665,405,'#e8f5f0')
s.text(62,162,'WINDOWS + macOS',19,BLUE,700);s.text(757,162,'ANDROID',19,GREEN,700)
for x,title,ls in [(62,'Proxy-aware browser / app',['OS HTTP/HTTPS proxy → 127.0.0.1:8877']), (757,'Proxy-aware app',['VpnService advertises a temporary HTTP proxy'])]:
 s.rect(x,182,620,75);s.text(x+18,213,title,20,weight=700);s.text(x+18,240,ls[0],16,GRAY)
s.line(370,260,370,284,True);s.line(1065,260,1065,284,True)
s.rect(62,290,620,100);s.text(80,322,'Python / mitmproxy child process',21,weight=700);s.lines(80,350,['HTTP/TLS forwarding ↔ destination server','OS adapters: WinINet + user CA / networksetup + Keychain'],16,gap=24)
s.rect(757,290,620,100);s.text(775,322,'Dart local HTTP/TLS proxy',21,weight=700);s.lines(775,350,['HTTP/TLS forwarding ↔ destination server','Kotlin bridge: VPN lifecycle + Android Keystore CA'],16,gap=24)
s.line(370,393,370,416,True);s.line(1065,393,1065,416,True)
s.rect(62,422,620,78);s.text(80,452,'Shared desktop Flutter UI',20,weight=700);s.text(80,479,'Local stdio JSON commands and session events',16,GRAY)
s.rect(757,422,620,78);s.text(775,452,'Android Flutter UI',20,weight=700);s.text(775,479,'In-process Dart events + Kotlin MethodChannel',16,GRAY)
s.line(370,503,370,555,True);s.line(1065,503,1065,555,True)
s.rect(40,560,1360,112,'#fff');s.text(65,595,'SHARED DART LAYER  ·  packages/capture_core',21,BLUE,700);s.lines(65,626,['CaptureSession → request / response / ordered header entries / body references','SessionStore: SQLite metadata + body files on the local device'],18,gap=26)
s.line(720,675,720,703,True)
s.rect(40,710,1360,140,'#fff');s.text(65,747,'SHARED DART EXPORT  ·  packages/capture_export',21,BLUE,700)
s.rect(65,770,620,55,'#eef4fb');s.text(86,805,'SAZ: ZIP + raw request/response + session XML',18)
s.rect(715,770,655,55,'#eef4fb');s.text(736,805,'HAR 1.2: entries + bodies + capture extensions',18)
s.rect(40,880,1360,120,'#fff8e9','#e6d4ab');s.text(64,914,'BOUNDARIES',18,'#835c17',700);s.lines(64,944,['Not a full TCP/UDP packet sniffer. Proxy bypasses, pinned TLS and unsupported protocols can be missed.','Local capture/storage; user-directed export may choose another destination. No iOS standalone engine.'],17,gap=27)
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

s=Svg(1200,1030,'Android interface schematic and capture setup walkthrough')
s.text(42,56,'Android UI / capture workflow',31,weight=700);s.text(42,88,'A separate mobile screen; the session model and exporters remain shared.',18,GRAY)
s.rect(55,125,455,805,'#fff','#b9c9d9',30);s.rect(76,148,414,62,'#e8f3ef');s.text(95,187,'HTTP Capture · HTTPS Preview',20,weight=700)
s.text(95,246,'Stopped · VPN proxy released',17,GREEN,600)
s.lines(95,283,['HTTP + optional HTTPS decryption','for all proxy-aware hosts.','Switching apps keeps capture active.'],15,gap=25)
s.lines(95,378,['Temporary VPN proxy only.','Wi-Fi proxy settings stay unchanged.','Proxy-aware apps only; replaces','an existing VPN connection.'],14,GRAY,gap=24)
for x,y,w,label,active in [(95,484,106,'Licenses',True),(212,484,126,'HTTPS on',True),(348,484,111,'Test TLS',True),(95,539,106,'Start',True),(212,539,106,'Pause',False),(330,539,129,'Test HTTP',False),(95,594,106,'SAZ',True),(212,594,106,'HAR',True),(330,594,129,'Clear',True)]:
 s.rect(x,y,w,40,'#e8f0fa' if active else '#f2f4f6',LINE,18);s.text(x+17,y+26,label,15,BLUE if active else '#8794a4',600)
s.text(95,673,'Wi-Fi settings · legacy proxy cleanup',14,BLUE)
s.rect(95,698,364,39,'#fff');s.text(110,724,'Filter method, URL, status',14,GRAY)
for i,(a,b) in enumerate([('GET 200','https://example.test/'),('POST 200','https://api.example.test/items')]):
 y=756+i*72;s.text(100,y,a,17,weight=700);s.text(100,y+26,b,13,GRAY);s.line(95,y+40,460,y+40)
items=[('1  Prepare HTTPS trust',['Open HTTPS settings and opt in.','Save the public CA and complete Android’s','system CA installation with user approval.']),('2  Start capture',['Approve the VPN request.','Only proxy-aware traffic is redirected;','this is not a full packet-processing VPN.']),('3  Use the target app',['Open another app and trigger a request.','Switching apps does not stop capture.','Some apps ignore proxies or reject user CAs.']),('4  Stop and export',['Stop releases the VPN proxy first.','SAZ / HAR use the shared Dart exporters.','The system document picker saves the file.'])]
for i,(title,ls) in enumerate(items):
 y=170+i*185;s.rect(555,y-35,600,155,'#fff');s.text(580,y,title,21,BLUE,700);s.lines(580,y+34,ls,17,gap=28)
s.text(555,925,'Session details: URL, state, headers and body size.',17,GRAY)
s.text(42,982,'DOCUMENTATION SCHEMATIC · synthetic sessions · text abbreviated for readability · not a runtime screenshot',15,GRAY)
s.save('android-ui')
