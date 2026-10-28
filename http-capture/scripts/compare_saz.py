"""Compare independently supplied Fiddler reference and generated archive structure."""
import argparse
import json
import zipfile
import xml.etree.ElementTree as ET

def inspect(path):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
        names=set(z.namelist());sessions=[]
        for name in sorted(n for n in names if n.startswith('raw/') and n.endswith('_c.txt')):
            prefix=name[:-6]
            request=z.read(name)
            metadata=prefix+'_m.xml';response=prefix+'_s.txt'
            if b'\r\n\r\n' not in request:raise ValueError('Missing HTTP separator')
            if metadata in names:ET.fromstring(z.read(metadata))
            sessions.append({'request':name,'responsePresent':response in names,'metadataPresent':metadata in names})
        return {'members':len(names),'sessions':sessions}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('generated');a=p.parse_args()
    print(json.dumps({'reference':inspect(a.reference),'generated':inspect(a.generated)},indent=2))
    print('Structure inspection only: actual Fiddler Import remains required.')
