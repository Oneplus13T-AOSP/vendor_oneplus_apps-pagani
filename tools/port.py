#!/usr/bin/env python3
"""Build/verify pinned unsigned ROM inputs and optionally sign test APKs."""
import argparse
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from dex_classes import class_descriptors

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(command, **kwargs):
    command = list(map(str, command))
    print('+', ' '.join(command)[:260], flush=True)
    subprocess.run(command, check=True, **kwargs)


def stock(name):
    return ROOT / 'proprietary/stock' / name / (name + '.apk')


def output(name):
    return ROOT / 'proprietary/product/app' / name / (name + '.apk')


def signed_output(name):
    return ROOT / 'proprietary/signed' / name / (name + '.apk')


def inputs(name):
    config = json.loads((ROOT / 'sources.json').read_text())[name]
    return [*sorted((ROOT / 'tools').glob('*.py')),
            *sorted((ROOT / 'patches' / name).glob('*.patch')),
            *[ROOT / 'compat/src' / s for s in config['compat_sources']]]


class Tools:
    def __init__(self, rom):
        self.rom = rom.resolve()
        self.java = self.rom / 'prebuilts/jdk/jdk21/linux-x86/bin/java'
        self.javac = self.java.with_name('javac')
        self.smali = self.rom / 'prebuilts/extract-tools/common/smali/smali.jar'
        self.baksmali = self.smali.with_name('baksmali.jar')
        self.android = self.rom / 'prebuilts/sdk/current/public/android.jar'
        self.sdk = self.rom / 'prebuilts/sdk/tools'
        self.zipalign = self.sdk / 'linux/bin/zipalign'
        self.aapt = self.sdk / 'linux/bin/aapt2'
        self.signer = self.sdk / 'linux/lib/apksigner.jar'
        self.r8 = self.sdk / 'linux/lib/d8.jar'
        self.key = self.rom / 'vendor/lineage-priv/keys'
        for p in [self.java, self.javac, self.smali, self.baksmali, self.android,
                  self.zipalign, self.aapt, self.signer, self.r8]:
            if not p.is_file():
                raise ValueError('Missing tool/key: ' + str(p))

    def signing(self, *args):
        return [self.java, '-jar', self.signer, *args]


def stage_stock(name, config, source):
    if digest(source) != config['sha256']:
        raise ValueError('Stock hash mismatch: ' + str(source))
    target = stock(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and digest(target) != config['sha256']:
        raise ValueError('Refusing to replace a different stock APK: ' + str(target))
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    print('Imported:', name, flush=True)


def build(name, config, tools):
    source = stock(name)
    if digest(source) != config['sha256']:
        raise ValueError('Wrong stock input: ' + str(source))
    with tempfile.TemporaryDirectory(prefix='pagani-apps-') as temp:
        work = Path(temp)
        smali = work / 'smali'
        smali.mkdir()
        with zipfile.ZipFile(source) as z:
            for dex in config['patched_dex']:
                raw = work / dex
                raw.write_bytes(z.read(dex))
        def decode(dex):
            raw = work / dex
            run([tools.java, '-Xmx2g', '-jar', tools.baksmali, 'd', raw,
                 '-o', smali / raw.stem])
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(decode, config['patched_dex']))
        for relative, expected in config['smali_sha256'].items():
            if digest(smali / relative) != expected:
                raise ValueError('Smali tool/input drift: ' + relative)
        for patch in sorted((ROOT / 'patches' / name).glob('*.patch')):
            run(['patch', '--batch', '--fuzz=0', '-p1', '-i', patch], cwd=smali)
        def assemble(dex):
            built = work / ('built-' + dex)
            # Parallel interning in smali changes annotation-pool placement and
            # therefore fixed-up hashes. Parallelize independent DEXs only.
            run([tools.java, '-Xmx2g', '-jar', tools.smali, 'a', '--api', '37', '--jobs', '1',
                 smali / Path(dex).stem, '-o', built])
            if not built.is_file():
                raise ValueError('smali did not produce DEX: ' + dex)
            return dex, built
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            replacements = dict(pool.map(assemble, config['patched_dex']))
        if config['compat_sources']:
            classes = work / 'compat-classes'
            classes.mkdir()
            sources = [ROOT / 'compat/src' / s for s in config['compat_sources']]
            run([tools.javac, '-source', '17', '-target', '17', '-Xlint:-options',
                 '-classpath', tools.android, '-d', classes, *sources])
            dexdir = work / 'compat-dex'
            dexdir.mkdir()
            run([tools.java, '-cp', tools.r8, 'com.android.tools.r8.D8',
                 '--min-api', str(config['min_sdk']), '--lib', tools.android, '--output', dexdir,
                 *sorted(classes.rglob('*.class'))])
            added_dex = f"classes{len(config['stock_dex']) + 1}.dex"
            replacements[added_dex] = dexdir / 'classes.dex'
        unsigned = work / 'unsigned.apk'
        with zipfile.ZipFile(source) as a, zipfile.ZipFile(unsigned, 'w') as b:
            for entry in a.infolist():
                n = entry.filename
                if n in replacements:
                    continue
                if n.startswith('META-INF/') and n.upper().endswith(
                        ('.RSA', '.DSA', '.EC', '.SF', 'MANIFEST.MF')):
                    continue
                b.writestr(entry, a.read(n))
            for n, path in replacements.items():
                # Fixed-up pins must not depend on the current time or signing key.
                entry = zipfile.ZipInfo(n, date_time=(2009, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o600 << 16
                b.writestr(entry, path.read_bytes())
        aligned = work / 'aligned.apk'
        run([tools.zipalign, '-f', '-P', '16', '4', unsigned, aligned])
        target = output(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(aligned, target)
    prepare_native(name, config)
    record = {'schema': 'pagani-apps-v2-unsigned', 'stock_sha256': config['sha256'],
              'config': config,
              'apk_sha256': digest(target),
              'inputs': {str(p.relative_to(ROOT)): digest(p) for p in inputs(name)},
              'tools': {str(p.relative_to(tools.rom)): digest(p) for p in
                        [tools.baksmali, tools.smali, tools.r8, tools.android,
                         tools.signer, tools.zipalign, tools.java, tools.javac]},
              'runtime_tested': False}
    target.with_suffix('.build.json').write_text(json.dumps(record, indent=2) + '\n')
    verify(name, config, tools)


def prepare_native(name, config):
    native_dir = ROOT / 'proprietary/native' / name
    native_dir.mkdir(parents=True, exist_ok=True)
    if {p.name for p in native_dir.glob('*.so')} - set(config['jni']):
        raise ValueError('Unexpected stale JNI files: ' + name)
    with zipfile.ZipFile(output(name)) as z:
        for lib in config['jni']:
            (native_dir / lib).write_bytes(z.read('lib/arm64-v8a/' + lib))


def verify_pins(name, config):
    from extract_utils.file import File
    entries = [File(s.strip()) for s in (ROOT / 'proprietary-files.txt').read_text().splitlines()
               if s.strip() and not s.lstrip().startswith('#')]
    entry, = [f for f in entries if f.dst == config['destination']]
    assert entry.src == config['dump_path']
    assert hashlib.sha1(stock(name).read_bytes()).hexdigest() == entry.hash
    assert entry.fixup_hash, 'Missing fixed-up pin: ' + name
    assert hashlib.sha1(output(name).read_bytes()).hexdigest() == entry.fixup_hash, 'Fixed-up pin mismatch: ' + name
    sums = {}
    for line in (ROOT / 'proprietary-files.sha256sum').read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            expected, relative = line.split(None, 1)
            sums[relative.strip()] = expected
    for path in [stock(name), output(name)]:
        relative = path.relative_to(ROOT / 'proprietary').as_posix()
        assert sums.get(relative) == digest(path), 'SHA-256 pin mismatch: ' + relative


def sign(name, config, tools):
    verify(name, config, tools)
    target = signed_output(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    run(tools.signing('sign', '--alignment-preserved', 'true',
                     '--key', tools.key / 'platform.pk8', '--cert', tools.key / 'platform.x509.pem',
                     '--out', target, output(name)))
    verify_signature(name, tools)


def verify_signature(name, tools):
    target = signed_output(name)
    run(tools.signing('verify', target))
    run([tools.zipalign, '-c', '-P', '16', '4', target])
    with zipfile.ZipFile(output(name)) as a, zipfile.ZipFile(target) as b:
        for n in a.namelist():
            assert a.read(n) == b.read(n), 'Signer changed ROM payload: ' + n
        assert all(n.startswith('META-INF/') for n in set(b.namelist()) - set(a.namelist()))
    cert = subprocess.check_output(['openssl', 'x509', '-in', str(tools.key / 'platform.x509.pem'),
                                    '-noout', '-fingerprint', '-sha256'], text=True)
    fingerprint = cert.split('=', 1)[1].strip().replace(':', '').lower()
    signature = subprocess.check_output(list(map(str, tools.signing('verify', '--print-certs', target))), text=True)
    assert 'SHA-256 digest: ' + fingerprint in signature


def verify(name, config, tools):
    target = output(name)
    if digest(stock(name)) != config['sha256']:
        raise ValueError('Stock hash mismatch')
    record = json.loads(target.with_suffix('.build.json').read_text())
    assert record['schema'] == 'pagani-apps-v2-unsigned'
    assert record['config'] == config
    assert record['apk_sha256'] == digest(target)
    assert record['stock_sha256'] == config['sha256']
    assert record['inputs'] == {str(p.relative_to(ROOT)): digest(p) for p in inputs(name)}
    for relative, expected in record['tools'].items():
        assert digest(tools.rom / relative) == expected, relative
    added = f"classes{len(config['stock_dex']) + 1}.dex" if config['compat_sources'] else None
    changed = set(config['patched_dex'])
    with zipfile.ZipFile(stock(name)) as a, zipfile.ZipFile(target) as b:
        assert len(b.namelist()) == len(set(b.namelist())), 'Duplicate ZIP entry'
        for n in a.namelist():
            if n.startswith('META-INF/') or n in changed:
                continue
            assert a.read(n) == b.read(n), 'Unexpected payload modification: ' + n
        assert set(b.namelist()) - set(a.namelist()) - ({added} if added else set()) <= {
            n for n in b.namelist() if n.startswith('META-INF/')}
        dexes = {n for n in b.namelist() if re.fullmatch(r'classes(?:[2-9][0-9]*)?\.dex', n)}
        assert dexes == set(config['stock_dex']) | ({added} if added else set())
        seen = set()
        for n in sorted(dexes):
            classes = class_descriptors(b.read(n))
            assert len(classes) == len(set(classes)), n
            assert not seen.intersection(classes), 'Duplicate class in ' + n
            if n != added:
                assert set(classes) == set(class_descriptors(a.read(n))), 'Lost/added stock classes: ' + n
            seen.update(classes)
        if added:
            assert set(class_descriptors(b.read(added))) == set(config['compat_descriptors'])
        native_dir = ROOT / 'proprietary/native' / name
        assert {p.name for p in native_dir.glob('*.so')} == set(config['jni'])
        native_report = {}
        public = {'libc.so', 'libdl.so', 'libm.so', 'liblog.so', 'libz.so',
                  'libandroid.so', 'libjnigraphics.so', 'libEGL.so', 'libGLESv2.so',
                  'libGLESv3.so', 'libOpenSLES.so', 'libmediandk.so',
                  'libstdc++.so', 'libvulkan.so', 'libaaudio.so', 'libnativewindow.so'}
        for lib in config['jni']:
            data = b.read('lib/arm64-v8a/' + lib)
            assert (native_dir / lib).read_bytes() == data
            # Alibaba SecurityGuard stores a signed plugin APK as libsgmain.so.
            # Keep the container intact for its original loader, not as an ELF.
            if data[:4] != b'\x7fELF':
                assert lib == 'libsgmain.so' and zipfile.is_zipfile(io.BytesIO(data)), lib
                native_report[lib] = {'kind': 'embedded-plugin-zip', 'needed': [],
                                      'external_nonpublic': [], 'load_alignments': []}
                continue
            assert data[:5] == b'\x7fELF\x02' and int.from_bytes(data[18:20], 'little') == 183
            dynamic = subprocess.run(['readelf', '-d', str(native_dir / lib)],
                                     capture_output=True, text=True, check=True)
            needed = set(re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic.stdout))
            headers = subprocess.run(['readelf', '-lW', str(native_dir / lib)],
                                     capture_output=True, text=True, check=True)
            aligns = [int(line.split()[-1], 16) for line in headers.stdout.splitlines()
                      if line.strip().startswith('LOAD ')]
            native_report[lib] = {'kind': 'aarch64-elf', 'needed': sorted(needed),
                                  'readelf_diagnostics': dynamic.stderr + headers.stderr,
                                  'external_nonpublic': sorted(needed - set(config['jni']) - public),
                                  'load_alignments': aligns}
    run([tools.zipalign, '-c', '-P', '16', '4', target])
    badging = subprocess.check_output([str(tools.aapt), 'dump', 'badging', str(target)], text=True)
    assert f"package: name='{config['package']}' versionCode='{config['version_code']}' versionName='{config['version_name']}'" in badging
    assert 'application-label-ko:' in badging
    checker = [sys.executable, tools.rom / 'build/soong/scripts/manifest_check.py',
               '--enforce-uses-libraries', '--aapt', tools.aapt]
    for lib in config['optional_uses_libs']:
        checker.extend(['--optional-uses-library', lib])
    run([*checker, target])
    target.with_suffix('.native.json').write_text(json.dumps(native_report, indent=2) + '\n')
    unresolved = {lib: data['external_nonpublic'] for lib, data in native_report.items()
                  if data['external_nonpublic']}
    print('PASS:', name, 'unsigned ROM input, alignment, original payload, unique DEX, private JNI, manifest;'
          ' external nonpublic native dependencies:', unresolved, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'verify', 'sign'])
    parser.add_argument('--rom-root', type=Path, required=True)
    parser.add_argument('--signed', action='store_true', help='also verify signed test APKs')
    parser.add_argument('--app', default='all')
    args = parser.parse_args()
    configs = json.loads((ROOT / 'sources.json').read_text())
    if args.app != 'all' and args.app not in configs:
        parser.error('Unknown app: ' + args.app)
    tools = Tools(args.rom_root)
    sys.path.insert(0, str(tools.rom / 'tools/extract-utils'))
    for name, config in configs.items():
        if args.app not in ('all', name):
            continue
        if args.action == 'build':
            build(name, config, tools)
        elif args.action == 'sign':
            verify_pins(name, config)
            sign(name, config, tools)
        else:
            verify(name, config, tools)
            verify_pins(name, config)
            if args.signed:
                verify_signature(name, tools)


if __name__ == '__main__':
    main()
