#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check final home/editor AI gates, negative callbacks and retained SDK types."""
from pathlib import Path
import argparse,subprocess,tempfile,zipfile,re
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom-root',type=Path,required=True);args=p.parse_args()
java=args.rom_root/'prebuilts/jdk/jdk21/linux-x86/bin/java';bak=args.rom_root/'prebuilts/extract-tools/common/smali/baksmali.jar'
classes={'classes.dex':['andes/oplus/documentsreader/aidepend/impl/AIInterface'],
'classes4.dex':['com/yozo/impl/AigcToOfficeModuleImpl','com/yozo/aigc/aikit/AiKitHelper'],
'classes5.dex':['com/yozo/pdf/impl/AigcToPdfModuleImpl','com/yozo/oplus/SDK$Aigc']}
source={}
with tempfile.TemporaryDirectory(prefix='pagani-no-ai-') as temp:
 work=Path(temp)
 with zipfile.ZipFile(ROOT/'proprietary/product/app/OplusDocumentsReader/OplusDocumentsReader.apk') as z:
  for dex,names in classes.items():
   raw=work/dex;raw.write_bytes(z.read(dex));out=work/Path(dex).stem
   subprocess.run([str(java),'-jar',str(bak),'d','--jobs','1','--classes',','.join('L'+s+';' for s in names),str(raw),'-o',str(out)],check=True)
   for s in names:source[s]=(out/(s+'.smali')).read_text()
def methods(cls):
 return {m[1].split()[-1]:m[2] for m in re.finditer(r'^\.method ([^\n]+)\n(.*?)^\.end method',source[cls],re.M|re.S)}
def zero(body):
 assert 'const/4 v0, 0x0' in body and 'return v0' in body
 assert 'invoke-' not in body
ai=methods('andes/oplus/documentsreader/aidepend/impl/AIInterface')
for name,body in ai.items():
 if name.split('(')[0] in ['c','d','e','k','l','o','p','r']:zero(body)
assert 'Boolean;->FALSE:' in ai['s(Landroid/content/Context;Ljava/lang/String;)Ljava/lang/Boolean;']
# No service query/download from startup/config refresh. No success callback.
for sig in ['m(Landes/oplus/documentsreader/BaseDocApplication;)V','q(Landes/oplus/documentsreader/launcher/activity/MainActivity;Lyu/a;)V']:
 assert 'invoke-' not in ai[sig] and 'return-void' in ai[sig]
convert=ai['n(Landroid/content/Context;Ljava/lang/String;Ljava/lang/String;Lyu/l;)V']
assert 'const/4 v1, -0x1' in convert and 'Lyu/l;->invoke' in convert and 'Lcom/oplus/aiunit/' not in convert
assert 'Boolean;->FALSE:' in ai['u(Landroid/content/Context;Lyu/l;)V']
sdk=methods('com/yozo/oplus/SDK$Aigc')
for sig,body in sdk.items():
 name=sig.split('(')[0]
 if name in ['isAiKitSupport','isAigcEnabled','isSupportSummary','isSupportTranslate','isSupportWisAnswer','isWisAnswerEnabled']:zero(body)
 if name in ['getAigcEnabled','getIsEnabled']:assert 'Boolean;->FALSE:' in body
 if name in ['isEnabled','needDownloadApi','downloadAiDocument']:
  assert 'Boolean;->FALSE:' in body and 'Observable;->just(' in body
  assert 'Lcom/oplus/' not in body
assert 'AIDownload' not in sdk['doAigcDownload(Landroid/content/Context;Ljava/lang/String;Lcom/yozo/oplus/SDK$AiSDkDownloadListener;)Lcom/oplus/aiunit/download/api/DownloadRequest;']
for cls in ['com/yozo/impl/AigcToOfficeModuleImpl','com/yozo/pdf/impl/AigcToPdfModuleImpl']:
 mm=methods(cls)
 for sig,body in mm.items():
  name=sig.split('(')[0]
  if name in ['onAskAndAnswerWhenCall','onChartConstructionWhenCall','onFormulaExtractWhenCall','onMindMapWhenCall','onRewriteWhenCall','onSmartSummaryWhenCall','onTranslateWhenCall','isSupportSummary'] and sig.endswith(')Z'):zero(body)
  if name in ['onAiShowDialog','showAiDialog','showAiPanel','changeAiPanel','chartDetector','onRewriteWhenCall'] and sig.endswith(')V'):
   assert 'invoke-' not in body and 'return-void' in body
 # Local editor bookkeeping/cleanup remains present.
 assert any(sig.startswith('<init>(') for sig in mm)
 assert 'onCheckSpaceEnough()Z' in mm and 'hideAiPanel(Landroidx/fragment/app/Fragment;)V' in mm
kit=methods('com/yozo/aigc/aikit/AiKitHelper')
for sig,body in kit.items():
 if sig.split('(')[0] in ['bindService','initHelper','startKitMethod']:assert 'invoke-' not in body
 if sig.split('(')[0]=='showAigcDialog':zero(body)
print('PASS: final home/Office/PDF AI gates, no AI startup/model download/launcher, negative conversion callbacks; runtime UI not tested.')
