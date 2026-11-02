#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify oplus-fwk compatibility classes against real APK call sites.

The classes under hardware/oplus/oplus-fwk/src/com/oplus/{animation,graphics,
util,view} are on the boot classpath, so Gallery, Camera and the ported apps
all resolve them at runtime. A missing or wrong member is a
NoClassDefFoundError / NoSuchMethodError on device rather than a build error,
so it has to be checked here.

Comparison is by exact JVM descriptor, not by method name: the sources are
compiled with javac and read back with javap -s, so argument types, argument
order, return type and constructor shape all have to match the call site.
Overloads are therefore distinguished correctly.

Usage:
  python3 tests/check-fwk-api.py \
      --rom-root /path/to/android/source \
      --apk app.apk [--apk another.apk ...]

Add --selftest to prove the checker itself fails when a required overload is
removed, has its argument types changed, or loses a constructor.
"""
from pathlib import Path
import argparse
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

# Classes owned by this module. Extend when adding a new compatibility class.
OWNED = {
    'Lcom/oplus/graphics/OplusCanvas;',
    'Lcom/oplus/animation/OplusAsyncAnimatorUtils;',
    'Lcom/oplus/view/OplusRenderNodeAnimator;',
    'Lcom/oplus/view/IRtAnimationTarget;',
    'Lcom/oplus/view/OplusWindowAttributesManager;',
    'Lcom/oplus/util/OplusLog;',
    'Lcom/oplus/util/OplusDarkModeUtil;',
    'Lcom/oplus/view/material/OplusMaterialUtil;',
    'Lcom/oplus/view/material/OplusMaterialBaseParams;',
    'Lcom/oplus/view/material/OplusMaterialCornerParams;',
    'Lcom/oplus/view/material/OplusMaterialEdgeParams;',
    'Lcom/oplus/view/material/OplusMaterialMetaBallParams;',
    'Lcom/oplus/view/material/OplusMaterialShadowParams;',
}


def uleb(data, i):
    value = 0
    shift = 0
    while True:
        byte = data[i]
        i += 1
        value |= (byte & 0x7f) << shift
        if not byte & 0x80:
            return value, i
        shift += 7


def dex_tables(data):
    string_count, string_off = struct.unpack_from('<II', data, 0x38)
    type_count, type_off = struct.unpack_from('<II', data, 0x40)
    proto_off = struct.unpack_from('<I', data, 0x4c)[0]
    strings = []
    for i in range(string_count):
        offset = struct.unpack_from('<I', data, string_off + 4 * i)[0]
        _, cursor = uleb(data, offset)
        end = data.index(b'\x00', cursor)
        strings.append(data[cursor:end].decode('utf-8', 'replace'))
    types = [strings[struct.unpack_from('<I', data, type_off + 4 * i)[0]]
             for i in range(type_count)]
    return strings, types, proto_off


def referenced_members(apk):
    """class -> set of ('name', '(params)return') referenced by the APK."""
    found = {}
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.namelist():
            if not re.fullmatch(r'classes(?:[2-9][0-9]*)?\.dex', entry):
                continue
            data = archive.read(entry)
            strings, types, proto_off = dex_tables(data)
            method_count, method_off = struct.unpack_from('<II', data, 0x58)
            for i in range(method_count):
                class_idx = struct.unpack_from('<H', data, method_off + 8 * i)[0]
                proto_idx = struct.unpack_from('<H', data, method_off + 8 * i + 2)[0]
                name_idx = struct.unpack_from('<I', data, method_off + 8 * i + 4)[0]
                cls = types[class_idx] if class_idx < len(types) else '?'
                if cls not in OWNED:
                    continue
                base = proto_off + 12 * proto_idx
                ret = types[struct.unpack_from('<I', data, base + 4)[0]]
                params_off = struct.unpack_from('<I', data, base + 8)[0]
                if params_off:
                    count = struct.unpack_from('<I', data, params_off)[0]
                    idxs = struct.unpack_from('<%dH' % count, data, params_off + 4)
                    params = ''.join(types[x] for x in idxs)
                else:
                    params = ''
                found.setdefault(cls, set()).add((strings[name_idx], '(%s)%s' % (params, ret)))
    return found


def javac(java_home, classpath, sources, out):
    subprocess.run([str(java_home / 'javac'), '-source', '17', '-target', '17',
                    '-Xlint:-options', '-nowarn', '-classpath', str(classpath),
                    '-d', str(out), *map(str, sources)], check=True)


def declared_members(java_home, classes_dir, class_name):
    """JVM class name -> set of ('name', '(params)return') declared members.

    javap -p -s prints each member as a declaration line ending in ';'
    followed by a "descriptor: (...)... " line. Only those pairs are used, so
    overloads, argument types and return types are compared exactly.
    """
    result = subprocess.run([str(java_home / 'javap'), '-p', '-s',
                             '-classpath', str(classes_dir), class_name],
                            capture_output=True, text=True, check=True)
    members = set()
    simple_name = class_name.rsplit('.', 1)[-1]
    declaration = None
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if line.startswith('descriptor:') and declaration is not None:
            members.add((declaration, line.split(':', 1)[1].strip()))
            declaration = None
            continue
        if not line.endswith(';') or '(' not in line:
            declaration = None
            continue
        header = line[:-1]
        token = header.split('(', 1)[0].split()[-1]
        # javap prints constructors fully qualified, e.g.
        #   public com.oplus.view.material.OplusMaterialCornerParams(float, float);
        # and methods either bare or fully qualified.
        short = token.rsplit('.', 1)[-1]
        declaration = '<init>' if short == simple_name else short
    return members


def owned_sources(fwk_src, owned):
    """Only the sources for OWNED classes.

    The full oplus-fwk tree needs the AOSP build's internal APIs and does not
    compile with plain javac + public android.jar. The owned classes only use
    public APIs, so they can be compiled standalone, which is all this check
    needs.
    """
    wanted = set()
    for path in fwk_src.rglob('*.java'):
        text = path.read_text(errors='replace')
        package = re.search(r'^package\s+([\w.]+);', text, re.M)
        if not package:
            continue
        for match in re.finditer(r'\b(?:public\s+)?(?:final\s+)?(?:class|interface)\s+(\w+)', text):
            if 'L%s/%s;' % (package.group(1).replace('.', '/'), match.group(1)) in owned:
                wanted.add(path)
                break
    return sorted(wanted)


def compiled_members(rom, fwk_src, owned):
    java_home = rom / 'prebuilts/jdk/jdk21/linux-x86/bin'
    android_jar = rom / 'prebuilts/sdk/current/public/android.jar'
    out = Path(tempfile.mkdtemp(prefix='fwk-api-'))
    try:
        javac(java_home, android_jar, owned_sources(fwk_src, owned), out)
        members = {}
        for descriptor in owned:
            binary = descriptor[1:-1].replace('/', '.')
            if '$' in binary:
                continue
            try:
                members[descriptor] = declared_members(java_home, out, binary)
            except subprocess.CalledProcessError:
                members[descriptor] = set()
        return members
    finally:
        shutil.rmtree(out, ignore_errors=True)


def compare(rom, fwk_src, apks, owned):
    declared = compiled_members(rom, fwk_src, owned)
    missing = []
    checked = 0
    for apk in apks:
        for cls, members in sorted(referenced_members(apk).items()):
            if cls not in declared:
                missing.append((apk.name, cls, '<class not provided>'))
                continue
            available = declared[cls]
            for name, descriptor in sorted(members):
                checked += 1
                if (name, descriptor) not in available:
                    missing.append((apk.name, cls, '%s%s' % (name, descriptor)))
    return missing, checked


def selftest(rom, fwk_src, apk):
    """Negative tests: removing/changing a required member must be detected.

    Each case gets a fresh copy of the sources, because some mutations would
    otherwise collide with an earlier one (for example turning the RenderNode
    overload into a duplicate View overload does not compile).
    """
    canvas_rel = Path('com/oplus/graphics/OplusCanvas.java')
    utils_rel = Path('com/oplus/animation/OplusAsyncAnimatorUtils.java')

    def drop_render_node_overload(root):
        target = root / utils_rel
        text = target.read_text()
        stripped = re.sub(
            r'\n\s*public static boolean setAlpha\(RenderNode node, float alpha\) \{.*?\n    \}\n',
            '\n', text, flags=re.S)
        assert stripped != text, 'selftest: RenderNode overload not found'
        target.write_text(stripped)

    def change_argument_type(root):
        target = root / utils_rel
        text = target.read_text()
        # Drop the View overload first so the replacement does not duplicate it,
        # then retype the RenderNode one. The APK still asks for
        # setAlpha(RenderNode,float), which is now gone.
        text = re.sub(
            r'\n\s*public static boolean setAlpha\(View view, float alpha\) \{.*?\n    \}\n',
            '\n', text, flags=re.S)
        text = text.replace('setAlpha(RenderNode node, float alpha)',
                            'setAlpha(Object node, float alpha)')
        target.write_text(text)

    def change_return_type(root):
        target = root / utils_rel
        text = target.read_text()
        assert 'public static boolean setOutlineRoundRect(' in text
        target.write_text(text.replace(
            'public static boolean setOutlineRoundRect(View view, Rect rect, float radius,\n            float weight)',
            'public static void setOutlineRoundRect(View view, Rect rect, float radius,\n            float weight)'))

    def drop_constructor(root):
        target = root / canvas_rel
        text = target.read_text()
        stripped = re.sub(r'\n\s*public OplusCanvas\(Canvas canvas\) \{.*?\n    \}\n',
                          '\n', text, flags=re.S)
        assert stripped != text, 'selftest: OplusCanvas constructor not found'
        target.write_text(stripped)

    cases = [
        ('removed overload', drop_render_node_overload),
        ('changed argument type', change_argument_type),
        ('changed return type', change_return_type),
        ('removed constructor', drop_constructor),
    ]

    ok = True
    for label, mutate in cases:
        with tempfile.TemporaryDirectory(prefix='fwk-api-selftest-') as tmp:
            root = Path(tmp) / 'src'
            shutil.copytree(fwk_src, root)
            mutate(root)
            try:
                missing, _checked = compare(rom, root, [apk], OWNED)
            except subprocess.CalledProcessError:
                # A mutation that will not compile is still a detected change.
                print('selftest ok: %s -> compile error' % label)
                continue
            if missing:
                print('selftest ok: %s -> %d missing' % (label, len(missing)))
            else:
                print('SELFTEST FAIL: %s was not detected' % label)
                ok = False
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom-root', type=Path, required=True)
    parser.add_argument('--apk', type=Path, action='append', required=True)
    parser.add_argument('--fwk-src', type=Path,
                        help='oplus-fwk/src; defaults to ROM_ROOT/hardware/oplus/oplus-fwk/src')
    parser.add_argument('--selftest', action='store_true',
                        help='prove the checker rejects removed/changed members')
    args = parser.parse_args()

    fwk_src = args.fwk_src or args.rom_root / 'hardware/oplus/oplus-fwk/src'
    if not fwk_src.is_dir():
        parser.error('missing oplus-fwk sources: %s' % fwk_src)

    if args.selftest:
        if not selftest(args.rom_root, fwk_src, args.apk[0]):
            print('FAIL: checker selftest did not detect a regression')
            return 1
        print('PASS: checker selftest detected every injected regression')

    missing, checked = compare(args.rom_root, fwk_src, args.apk, OWNED)
    for apk_name, cls, member in missing:
        print('MISSING %s: %s -> %s' % (apk_name, cls, member))
    if missing:
        print('FAIL: %d missing signature(s) across %d reference(s)' % (len(missing), checked))
        return 1
    print('PASS: %d referenced signature(s) matched exactly against oplus-fwk' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
