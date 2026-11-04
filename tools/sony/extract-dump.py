#!/usr/bin/env python3
"""Offline partition extraction using dumpyara's fsck.erofs / 7z sequence.
Avoids upstream directory-input guard bug, network pull/push and image deletion.
"""
from pathlib import Path
import subprocess,json,hashlib,time
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('images', type=Path)
parser.add_argument('--dumpyara', type=Path, required=True)
parser.add_argument('--output', type=Path)
parser.add_argument('--partitions', nargs='+', choices=['system','system_ext','product','vendor','odm'], default=['product'], help='Only extract required partitions; Music is in product')
args=parser.parse_args()
SRC=args.images.resolve()
DUMPY=args.dumpyara.resolve()
DEST=args.output.resolve() if args.output else DUMPY/'working'/SRC.name
REC=DEST/'extraction-records'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''): h.update(b)
 return h.hexdigest()
if DEST.exists(): raise SystemExit('Refusing existing dump: '+str(DEST))
DEST.mkdir(parents=True)
REC.mkdir()
record={'source':str(SRC),'destination':str(DEST),'dumpyara_sha256':sha(DUMPY/'dumpyara.sh'),'method':'dumpyara partition extraction sequence; normalize _a names; no network or image deletion','partitions':{}}
for part in args.partitions:
 image=SRC/(part+'_a.img')
 if not image.is_file(): image=SRC/(part+'.img')
 target=DEST/part
 print('Extracting',part,flush=True)
 with (REC/(part+'-extract.log')).open('w') as log:
  result=subprocess.run([str(DUMPY/'external/Firmware_extractor/tools/fsck.erofs'),'--extract='+str(target),str(image)],stdout=log,stderr=subprocess.STDOUT)
  if result.returncode:
   result=subprocess.run(['7z','-snld','x',str(image),'-y','-o'+str(target)],stdout=log,stderr=subprocess.STDOUT)
  if result.returncode: raise SystemExit('Extraction failed: '+part)
 record['partitions'][part]={'source_image':str(image),'bytes':image.stat().st_size,'sha256':sha(image),'files':sum(1 for p in target.rglob('*') if p.is_file())}
 (REC/'extraction.json').write_text(json.dumps(record,indent=2))
# Normalize system-as-root once, before extract-utils can mutate the dump.
if (DEST/'system/system').is_dir():
 (DEST/'system').rename(DEST/'system_root')
 (DEST/'system_root/system').rename(DEST/'system')
print('EXTRACTION COMPLETE',DEST,flush=True)
