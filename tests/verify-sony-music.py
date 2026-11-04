#!/usr/bin/env python3
"""Verify the Sony port contract on the built APK, without installing it."""
import argparse,hashlib,json,re,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from sony import port
args=argparse.ArgumentParser()
args.add_argument('--rom-root',type=Path,required=True)
a=args.parse_args(); tools=port.Tools(a.rom_root)
sys.path.insert(0,str(tools.rom/'tools/extract-utils'))
config=json.loads((ROOT/'sony-sources.json').read_text())['SemcMusicApp']
port.verify('SemcMusicApp',config,tools); port.verify_pins('SemcMusicApp',config)
p=port.output('SemcMusicApp')
xml=subprocess.check_output([tools.aapt,'dump','xmltree','--file','AndroidManifest.xml',p],text=True)
for name in config['manifest_remove_uses_libraries']+config['manifest_remove_services']:
    assert '="'+name+'"' not in xml,name
assert 'android.permission.READ_MEDIA_AUDIO' in xml
assert 'android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK' in xml
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    assert sorted(n for n in z.namelist() if n.startswith('lib/arm64-v8a/') and n.endswith('.so')) == sorted('lib/arm64-v8a/'+n for n in config['jni'])
    report=json.loads(p.with_suffix('.native.json').read_text())
    assert all(not item['external_nonpublic'] and all(v >= 16384 for v in item['load_alignments']) for item in report.values())
    with tempfile.TemporaryDirectory() as temp:
        t=Path(temp); (t/'classes2.dex').write_bytes(z.read('classes2.dex'))
        subprocess.run([tools.java,'-Xmx2g','-jar',tools.baksmali,'d',t/'classes2.dex','-o',t/'smali'],check=True,stdout=subprocess.DEVNULL)
        root=t/'smali'
        for relative,expected in config['preserved_smali_sha256'].items():
            assert port.digest(root/relative)==expected,'Modified preserved playback/EQ class: '+relative
        gates=config['patched_method_signatures']
        total=0
        for relative,names in gates.items():
            for method in re.findall(r'(?ms)^\.method .*?^\.end method',(root/relative).read_text()):
                if any(method.splitlines()[0] == '.method '+n for n in names):
                    assert 'invoke-' not in method and 'new-instance' not in method,relative
                    total+=1
        assert total==4,total
print('PASS Sony: no required OEM libraries/service, four current-version safe gates, unchanged playback/EQ, stored DEX, two 16KB ARM64 JNI libraries and pinned output')
