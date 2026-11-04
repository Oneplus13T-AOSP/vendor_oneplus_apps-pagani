#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Standard extract-utils front end with app-local DEX/JNI fixups.

The proprietary list has stock and fixed-up SHA-1 pins. Fixed-up APKs are
unsigned, so pins remain valid for builders using a different ROM signing key.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
bootstrap = argparse.ArgumentParser(add_help=False)
bootstrap.add_argument('--rom-root', type=Path, default=ROOT.parents[2])
bootstrap.add_argument('--update-pins', action='store_true',
                       help='explicitly refresh stock/fixed-up pins after reviewing source config')
bootstrap_args, remaining = bootstrap.parse_known_args()
ROM = bootstrap_args.rom_root.resolve()
if not (ROM / 'tools/extract-utils/extract_utils').is_dir():
    raise SystemExit('Use --rom-root /path/to/android/source (missing tools/extract-utils)')
sys.path[:0] = [str(ROM / 'tools/extract-utils'), str(ROOT / 'tools')]
sys.argv = [sys.argv[0], *remaining]

from extract_utils.file import FileArgs
from extract_utils.args import parser as extract_parser
from extract_utils.fixups_blob import blob_fixup
from extract_utils.main import ExtractUtils, ExtractUtilsModule
from extract_utils.module import ProprietaryFileType
from sony import port

CONFIGS = json.loads((ROOT / 'sony-sources.json').read_text())


def fixup_app(ctx, file, file_path, name, **kwargs):
    config = CONFIGS[name]
    port.stage_stock(name, config, Path(file_path))
    port.build(name, config, port.Tools(ROM))
    assert Path(file_path).resolve() == port.output(name).resolve()


class AppsModule(ExtractUtilsModule):
    def cleanup(self):
        raise RuntimeError('Self-hosted vendor repository requires --no-cleanup')

    def parse(self, regenerate, section):
        super().parse(regenerate, section)
        listed = self.get_files(ProprietaryFileType.BLOBS)
        if not listed:
            raise ValueError('No proprietary entries selected')
        by_destination = {c['destination']: (n, c) for n, c in CONFIGS.items()}
        for file in listed:
            if file.dst not in by_destination:
                raise ValueError('Unconfigured proprietary entry: ' + file.dst)
            name, config = by_destination[file.dst]
            if file.src != config['dump_path'] or not file.hash or not file.fixup_hash:
                raise ValueError('Missing/wrong stock/fixed-up pin: ' + name)
            if FileArgs.EXTRACT_ONLY not in file.args:
                raise ValueError('JNI app must use custom app installer: ' + name)

    def write_makefiles(self, legacy, extract_factory):
        super().write_makefiles(legacy, extract_factory)
        # extract-utils cannot express app-private prebuilt JNI installation.
        # EXTRACT_ONLY suppresses duplicate android_app_import modules; this
        # maintained fragment supplies exactly one APK/JNI module per app.
        mk = ROOT / 'Android.mk'
        mk.write_text(mk.read_text() + '\ninclude $(LOCAL_PATH)/build/apps-prebuilt.mk\n')
        pin_list = ROOT / 'proprietary-files.txt'
        pin_list.write_text(pin_list.read_text().rstrip() + '\n')


module = AppsModule(
    'apps-pagani', 'oneplus',
    device_rel_path=str(ROOT),
    blob_fixups={c['destination']: blob_fixup().call(fixup_app, n, need_tmp_dir=False)
                 for n, c in CONFIGS.items()},
)
# Resolve to this checkout, which also permits isolated extraction tests outside
# the ROM tree. The generated ROM-relative install paths remain unchanged.
module.device_path = str(ROOT)
module.vendor_path = str(ROOT)


def postprocess(ctx):
    for file in module.get_files(ProprietaryFileType.BLOBS):
        name, config = next((n, c) for n, c in CONFIGS.items() if c['destination'] == file.dst)
        port.prepare_native(name, config)
        if bootstrap_args.update_pins:
            port.verify(name, config, port.Tools(ROM))
        else:
            port.verify_pins(name, config)


module.add_postprocess_fn(postprocess)

if __name__ == '__main__':
    # Preserve other manufacturers' sections when extracting a single donor.
    # No-cleanup also preserves verified raw inputs and provenance sidecars.
    if '-n' not in sys.argv and '--no-cleanup' not in sys.argv:
        sys.argv.insert(1, '--no-cleanup')
    if bootstrap_args.update_pins:
        sys.argv.insert(1, '--kang')
    parsed = extract_parser.parse_args()
    if parsed.kang and not bootstrap_args.update_pins:
        extract_parser.error('Use --update-pins to explicitly update SHA-1 and SHA-256 together')
    if parsed.regenerate_makefiles and bootstrap_args.update_pins:
        extract_parser.error('--update-pins requires extraction, not setup-makefiles')
    if not parsed.regenerate_makefiles and (
            not parsed.source or parsed.source == 'adb' or 'adb' in parsed.source):
        extract_parser.error('Supply a dump path explicitly; ADB extraction is disabled')
    utils = ExtractUtils.device(module)
    utils.run()
    if bootstrap_args.update_pins:
        pin_file = ROOT / 'proprietary-files.sha256sum'
        sums = {}
        if pin_file.exists():
            for line in pin_file.read_text().splitlines():
                if line.strip() and not line.lstrip().startswith('#'):
                    digest, relative = line.split(None, 1)
                    sums[relative.strip()] = digest
        for file in module.get_files(ProprietaryFileType.BLOBS):
            name, config = next((n, c) for n, c in CONFIGS.items() if c['destination'] == file.dst)
            port.verify(name, config, port.Tools(ROM))
            for path in [port.stock(name), port.output(name)]:
                sums[path.relative_to(ROOT / 'proprietary').as_posix()] = port.digest(path)
        pin_file.write_text('# SHA-256 pins for raw inputs and deterministic unsigned ROM inputs.\n'
                            + ''.join(f'{digest}  {relative}\n' for relative, digest in sorted(sums.items())))
    # Upstream run() reports extraction failure without a nonzero return code.
    # Pins and JNI checks make our CLI fail on incomplete/mismatched extraction.
    if not parsed.regenerate_makefiles:
        for file in module.get_files(ProprietaryFileType.BLOBS):
            name, config = next((n, c) for n, c in CONFIGS.items() if c['destination'] == file.dst)
            port.verify_pins(name, config)
