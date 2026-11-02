#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect final DEX feature gates and preserve ordinary app/file operations.

Run after extraction: python3 tests/verify-local-features.py --rom-root <rom>
This is an artifact regression check, not an ART/device execution test.
"""
from pathlib import Path
import argparse,re,subprocess,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom-root',type=Path,required=True)
args=parser.parse_args()
java=args.rom_root/'prebuilts/jdk/jdk21/linux-x86/bin/java'
bak=args.rom_root/'prebuilts/extract-tools/common/smali/baksmali.jar'
groups=[('OplusDocumentsReader','classes.dex',[
 'andes/oplus/documentsreader/clouddrive/a',
 'andes/oplus/documentsreader/superapp/hepler/SuperAppHelper',
 'andes/oplus/documentsreader/core/common/compat/FeatureCompat$sIsSupportEncryption$2',
 'andes/oplus/documentsreader/core/common/w']),
 ('OplusDocumentsReader','classes2.dex',['com/oplus/encrypt/f']),
 ('OplusDocumentsReader','classes8.dex',['zy/a']),
 ('OcrScanner','classes4.dex',['com/oplus/scanner/ui/settings/SettingsActivity']),
 ('OcrScanner','classes.dex',['androidx/preference/Preference']),
 ('ConsumerIRApp','classes.dex',['androidx/preference/Preference']),
 ('ConsumerIRApp','classes2.dex',['com/oplus/consumerIRApp/navigation/fragment/SettingFragment',
 'com/oplus/consumerIRApp/navigation/fragment/SettingFragment$c'])]
# Explicit final artifact class sets; a missing expected class must fail.
raw={};built={}
with tempfile.TemporaryDirectory(prefix='pagani-feature-check-') as tmp:
 work=Path(tmp)
 for app,dex,classes in groups:
  for variant,base,store in [('stock','stock',raw),('fixed','product/app',built)]:
   with zipfile.ZipFile(ROOT/'proprietary'/base/app/(app+'.apk')) as archive:data=archive.read(dex)
   folder=work/app/variant/dex;folder.mkdir(parents=True)
   input_dex=folder/'input.dex';input_dex.write_bytes(data)
   subprocess.run([str(java),'-jar',str(bak),'d','--jobs','1','--classes',','.join('L'+c+';' for c in classes),str(input_dex),'-o',str(folder/'smali')],check=True)
   for cls in classes:
    file=folder/'smali'/(cls+'.smali');assert file.is_file(),file
    store[cls]=file.read_text()
    if cls=='androidx/preference/Preference' and variant=='stock':
     signature='M0(Z)V' if app=='OcrScanner' else 'setVisible(Z)V'
     assert re.search(r'^\.method[^\n]* '+re.escape(signature)+r'$',store[cls],re.M), (app,signature)

def method(source,name):
 found=[m[2] for m in re.finditer(r'^\.method ([^\n]+)\n(.*?)^\.end method',source,re.M|re.S) if m[1].split()[-1]==name]
 assert len(found)==1,name
 return found[0]

def scalar(cls,name,value):
 t=method(built[cls],name)
 assert re.search(r'const/4 v0, '+value+r'\b',t),name
 assert 'return v0' in t and 'invoke-' not in t,name

scalar('andes/oplus/documentsreader/clouddrive/a','a()Z','0x0')
scalar('andes/oplus/documentsreader/superapp/hepler/SuperAppHelper','g()Z','0x1')
scalar('zy/a','k()Z','0x0')
assert 'Boolean;->FALSE:' in method(built['andes/oplus/documentsreader/core/common/compat/FeatureCompat$sIsSupportEncryption$2'],'invoke()Ljava/lang/Boolean;')
for cls,name in [('andes/oplus/documentsreader/clouddrive/a','b(Landroid/content/Context;Ljava/util/ArrayList;)V'),('com/oplus/encrypt/f','a(Landes/oplus/documentsreader/core/common/BaseVMActivity;Lyu/a;)V')]:
 t=method(built[cls],name);assert 'return-void' in t and 'invoke-' not in t
# Compare ordinary third-party category/file search, including downloads and
# Bluetooth. Removing the entire popular-app search would fail this check.
def normalized(text):
 return '\n'.join(l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('.line '))
cls='andes/oplus/documentsreader/superapp/hepler/SuperAppHelper'
for name in ['a(Landroid/content/Context;Ljava/lang/String;)Ljava/lang/String;', 'b(Landroid/content/Context;)Ljava/util/ArrayList;']:
 assert normalized(method(raw[cls],name))==normalized(method(built[cls],name)),name
assert 'android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION' in built['andes/oplus/documentsreader/core/common/w']
# Confirm both preference APIs exist in the stock APKs; obfuscated scanner
# methods differ from the unminified IR library and must never be interchanged.
scanner=built['com/oplus/scanner/ui/settings/SettingsActivity']
assert 'Preference;->M0(Z)V' in method(scanner,'b1(Lcom/coui/appcompat/preference/h;)V')
assert 'FeedbackHelper' not in method(scanner,'r1(Ljava/lang/String;)V')
ir=built['com/oplus/consumerIRApp/navigation/fragment/SettingFragment']
assert 'Preference;->setVisible(Z)V' in method(ir,'O()V')
assert 'Lg8/c;->' not in method(built['com/oplus/consumerIRApp/navigation/fragment/SettingFragment$c'],'onPreferenceClick(Landroidx/preference/Preference;)Z')
print('PASS: final DEX gates, cloud/private entry blocks, OEM feedback hiding, ordinary app search and storage access preserved. Runtime not tested.')
