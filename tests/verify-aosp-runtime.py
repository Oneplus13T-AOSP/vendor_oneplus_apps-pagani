#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check final DEX AOSP runtime fallbacks, private-vault removal, offline IR.

Run after extraction: python3 tests/verify-aosp-runtime.py --rom-root <rom>
This inspects the final unsigned APK DEX. It is an artifact regression check,
not an ART/device execution test.
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from dex_classes import class_descriptors  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom-root', type=Path, required=True)
args = parser.parse_args()
java = args.rom_root / 'prebuilts/jdk/jdk21/linux-x86/bin/java'
bak = args.rom_root / 'prebuilts/extract-tools/common/smali/baksmali.jar'

DEX_RE = re.compile(r'classes(?:[2-9][0-9]*)?\.dex')
WANTED = {
    'OplusDocumentsReader': [
        'andes/oplus/documentsreader/core/common/z',
        'andes/oplus/documentsreader/core/common/z$a',
        'andes/oplus/documentsreader/launcher/fragment/FolderTabFragment$f',
        'andes/oplus/documentsreader/launcher/viewmodel/MainActivityViewModel',
        'andes/oplus/documentsreader/core/fileoperate/copy/m',
        'com/coui/appcompat/c',
        'com/coui/appcompat/floatingactionbutton/o',
        'com/coui/appcompat/floatingactionbutton/o$a',
        'com/coui/appcompat/COUIMaterialStateManager',
        'com/coui/appcompat/poplist/RoundFrameLayout',
        'com/coui/appcompat/toolbar/AppBarBlurHelper',
        'com/yozo/utils/AppTitleUtils',
        'com/coui/appcompat/panel/COUIBottomSheetDialog',
        'andes/oplus/documentsreader/formatconvert/FormatApi',
        'andes/oplus/documentsreader/aidepend/impl/AIInterface',
    ],
    'OcrScanner': [
        'com/oplus/scanner/common/base/view/GaussianBackgroundView',
        'com/oplus/scanner/common/base/view/OseeHeaderGradientBlur',
        'com/oplus/scanner/common/base/view/OseeBottomGradientBlur',
        'com/oplus/scanner/common/base/view/FrostedBackdropView',
        'com/oplus/scanner/common/core/widgets/RoundPreviewView',
        'com/oplus/scanner/common/utils/t',
        'com/oplus/scanner/common/utils/n',
        'com/coui/appcompat/panel/COUIBottomSheetDialog',
    ],
    'ConsumerIRApp': [
        'com/oplus/consumerIRApp/navigation/HomeActivity',
        'com/oplus/consumerIRApp/navigation/utils/g0',
        'com/oplus/consumerIRApp/sdkSeal/KuKongAbility',
        'com/oplus/consumerIRApp/navigation/utils/b',
        'com/hzy/tvmao/KookongSDK',
        'com/oplus/consumerIRApp/navigation/IrApplication',
        'com/oplus/consumerIRApp/navigation/fragment/AddFailFragment',
        'com/coui/appcompat/panel/COUIBottomSheetDialog',
    ],
}
COMPAT = 'Lorg/pixelos/pagani/compat/'
LIVE_OEM = (
    'Lcom/oplus/view/OplusViewBackgroundRenderEffect;',
    'Lcom/oplus/graphics/OplusRenderEffect;',
    'Lcom/oplus/animation/OplusViewSeamless;',
    'Lcom/oplus/animation/OplusViewSeamless$AnimationCallback;',
    'Lcom/oplus/wrapper/os/UserHandle;',
    'Lcom/oplus/util/OplusChangeTextUtil;',
)

def _collect(app, variant, apk, classes, store, work):
    with zipfile.ZipFile(apk) as archive:
        dexes = [n for n in archive.namelist() if DEX_RE.fullmatch(n)]
        index, payload = {}, {}
        for name in dexes:
            payload[name] = archive.read(name)
            for descriptor in class_descriptors(payload[name]):
                index[descriptor] = name
    grouped = {}
    for cls in classes:
        dex = index.get('L' + cls + ';')
        assert dex, f'{app}: class missing from APK: {cls}'
        grouped.setdefault(dex, []).append(cls)
    for dex, names in grouped.items():
        folder = work / variant / app / Path(dex).stem
        folder.mkdir(parents=True)
        raw = folder / 'input.dex'
        raw.write_bytes(payload[dex])
        subprocess.run([str(java), '-jar', str(bak), 'd', '--jobs', '1',
                        '--classes', ','.join('L' + c + ';' for c in names),
                        str(raw), '-o', str(folder / 'smali')], check=True)
        for cls in names:
            f = folder / 'smali' / (cls + '.smali')
            assert f.is_file(), f
            store[(app, cls)] = f.read_text()


source = {}
stock_source = {}
with tempfile.TemporaryDirectory(prefix='pagani-runtime-check-') as tmp:
    work = Path(tmp)
    for app, classes in WANTED.items():
        _collect(app, 'fixed', ROOT / 'proprietary/product/app' / app / (app + '.apk'),
                 classes, source, work)
        _collect(app, 'stock', ROOT / 'proprietary/stock' / app / (app + '.apk'),
                 classes, stock_source, work)


def methods(app, cls):
    found = {}
    for m in re.finditer(r'^\.method ([^\n]+)\n(.*?)^\.end method', source[(app, cls)],
                         re.M | re.S):
        found[m.group(1).split()[-1]] = m.group(2)
    return found


def body(app, cls, signature):
    table = methods(app, cls)
    assert signature in table, (app, cls, signature)
    return table[signature]


def assert_const(app, cls, signature, value):
    text = body(app, cls, signature)
    assert re.search(r'const/4 v0, ' + value + r'\b', text), (app, cls, signature)
    assert 'return v0' in text and 'invoke-' not in text, (app, cls, signature)
    return text


# --- Documents -----------------------------------------------------------
# Seamless callbacks must extend the app-private class, never the OEM one.
text = source[('OplusDocumentsReader', 'andes/oplus/documentsreader/core/common/z$a')]
assert '.super ' + COMPAT + 'UiCompat$AnimationCallback;' in text
assert 'Lcom/oplus/animation/OplusViewSeamless' not in text
assert '.super Lcom/oplus/animation' not in text

# Private vault entries are no longer appended to either management list.
# Compare the same method against stock: exactly one ArrayList.add disappears
# at each site, the vault label resource stays, and the method keeps working.
def stock_method(app, cls, signature):
    found = {}
    for m in re.finditer(r'^\.method ([^\n]+)\n(.*?)^\.end method', stock_source[(app, cls)],
                         re.M | re.S):
        found[m.group(1).split()[-1]] = m.group(2)
    assert signature in found, (app, cls, signature)
    return found[signature]


add = 'Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z'
for cls, signature in [
        ('andes/oplus/documentsreader/launcher/fragment/FolderTabFragment$f',
         'a(Landroid/widget/LinearLayout;)V'),
        ('andes/oplus/documentsreader/launcher/viewmodel/MainActivityViewModel',
         'A(ILjava/util/List;)Ljava/util/ArrayList;')]:
    fixed = body('OplusDocumentsReader', cls, signature)
    stock = stock_method('OplusDocumentsReader', cls, signature)
    assert stock.count(add) == fixed.count(add) + 1, (cls, 'expected exactly one vault add removed')
    assert 'nop' in fixed, cls
    assert 'string_encrypt_menu' in source[('OplusDocumentsReader', cls)], cls
    # The remaining list construction and the returned object are untouched.
    assert 'Ljava/util/ArrayList;-><init>()V' in fixed, cls

# Title render effect: both the effect and the clear path use the shim.
title = source[('OplusDocumentsReader', 'com/yozo/utils/AppTitleUtils')]
assert title.count(COMPAT + 'UiCompat;->setBackgroundRenderEffect') == 2
assert 'Lcom/oplus/view/OplusViewBackgroundRenderEffect' not in title

# Read-only detection uses public StorageVolume state, not the OEM wrapper.
readonly = body('OplusDocumentsReader', 'andes/oplus/documentsreader/core/fileoperate/copy/m',
                'a(Landroid/os/storage/StorageVolume;)I')
assert 'Landroid/os/storage/StorageVolume;->getState()Ljava/lang/String;' in readonly
assert 'Lcom/oplus/os/storage/OplusStorageVolume;' not in readonly
assert '"mounted_ro"' in readonly
# Ordinary copy path must still call the real File I/O helpers.
copy_class = source[('OplusDocumentsReader', 'andes/oplus/documentsreader/core/fileoperate/copy/m')]
assert 'Ljava/nio/channels/FileChannel;->transferTo(JJLjava/nio/channels/WritableByteChannel;)J' in copy_class

# --- Scanner -------------------------------------------------------------
gauss = source[('OcrScanner', 'com/oplus/scanner/common/base/view/GaussianBackgroundView')]
assert COMPAT + 'UiCompat;->setBackgroundRenderEffect' in gauss
assert 'Lcom/oplus/view/OplusViewBackgroundRenderEffect' not in gauss
for cls in ['com/oplus/scanner/common/base/view/OseeHeaderGradientBlur',
            'com/oplus/scanner/common/base/view/OseeBottomGradientBlur']:
    text = source[('OcrScanner', cls)]
    assert COMPAT + 'UiCompat;->createGradientBlurEffect' in text
    assert 'Lcom/oplus/graphics/OplusRenderEffect' not in text
round_preview = source[('OcrScanner', 'com/oplus/scanner/common/core/widgets/RoundPreviewView')]
assert COMPAT + 'PathCompat' in round_preview
assert 'Lcom/oplus/graphics/OplusPath;' not in round_preview
# The preview still draws its frame shape: the Path object is drawn afterwards.
assert 'Landroid/graphics/Canvas;->drawPath(Landroid/graphics/Path;Landroid/graphics/Paint;)V' in round_preview
assert COMPAT + 'PathCompat;->addSmoothRoundRect' in round_preview

# PC/Pad detection reports unsupported without touching OEM feature config.
feature = body('OcrScanner', 'com/oplus/scanner/common/utils/t', 'b()Z')
assert 'const/4 v0, 0x0' in feature and 'return v0' in feature
assert 'invoke-' not in feature
# Single-argument OEM SystemProperties.get goes through the guarded accessor.
project = body('OcrScanner', 'com/oplus/scanner/common/utils/n', 'e()Z')
assert 'Lcom/oplus/wrapper/os/SystemProperties;' not in project
assert 'Lcom/oplus/scanner/common/utils/n;->c(Ljava/lang/String;Ljava/lang/String;)' in project

# --- IR ------------------------------------------------------------------
g0 = source[('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/utils/g0')]
assert 'Lcom/oplus/coreapp/appfeature/AppFeatureProviderUtils;' not in g0
assert_const('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/utils/g0',
             'h(Landroid/content/Context;)Z', '0x0')
assert_const('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/utils/g0',
             'j(Landroid/content/Context;)Z', '0x1')
manual = body('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/HomeActivity', 'M0(I)V')
assert 'EntranceActivity' in manual
assert 'RecognizeActivity' not in manual and 'qrScan/CaptureActivity' not in manual
menu = body('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/HomeActivity',
            'onCreateOptionsMenu(Landroid/view/Menu;)Z')
assert 'add_scan_device' in menu and 'Landroid/view/Menu;->removeItem(I)V' in menu
set_offline = body('ConsumerIRApp', 'com/oplus/consumerIRApp/sdkSeal/KuKongAbility', 'i(Z)V')
assert 'SDKSwitcher$Mode;->OfflineOnly' in set_offline
assert 'OnlineFirst' not in set_offline
# Offline DB path and mode must be set before the native init call, because
# the native layer reads the DB path during init.
init_body = body('ConsumerIRApp', 'com/oplus/consumerIRApp/sdkSeal/KuKongAbility',
                 'g(Landroid/content/Context;)Z')
# KookongSDK.setOfflineDBPath -> OflIface -> com.kookong.sdk.ir.e1.a(), and e1's
# static initialiser calls KookongSDK.getContext(), which throws unless
# sContext is already set. preinit(Context) is the only API that sets sContext
# without doing the full SDK init, so it must come first.
preinit_at = init_body.index('Lcom/hzy/tvmao/KookongSDK;->preinit')
db_at = init_body.index('Lcom/hzy/tvmao/KookongSDK;->setOfflineDBPath')
mode_at = init_body.index('Lcom/hzy/tvmao/KookongSDK;->setMode')
init_call = init_body.index('Lcom/hzy/tvmao/KookongSDK;->init(')
assert preinit_at < db_at, 'preinit(Context) must precede setOfflineDBPath'
assert db_at < init_call and mode_at < init_call, 'offline setup must precede init'
assert init_body.count('setOfflineDBPath') == 1, 'duplicate offline DB path assignment'
assert init_body.count('KookongSDK;->preinit') == 1, 'duplicate preinit'
# SDK init must not be tied to the one-time notice flag any more.
oncreate = body('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/IrApplication', 'onCreate()V')
assert oncreate.count('IrApplication;->i()V') == 1
# Init must sit after the notice-flag branch merge, not inside the true branch.
true_branch = oncreate[oncreate.index('if-eqz'):oncreate.index(':cond_')]
assert 'IrApplication;->i()V' not in true_branch, 'init still gated on the notice flag'
# The remaining photo entry on the failure screen is hidden, not wired.
add_fail = source[('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/fragment/AddFailFragment')]
init_click = body('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/fragment/AddFailFragment', 'T()V')
assert 'const/16 v1, 0x8' in init_click and 'setVisibility(I)V' in init_click
assert 'navigation/fragment/f;-><init>' not in init_click, 'photo button still wired'
# Compare with stock: the photo click listener existed there.
stock_click = stock_method('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/fragment/AddFailFragment', 'T()V')
assert 'navigation/fragment/f;-><init>' in stock_click
# RecognizeActivity is no longer reachable from the failure screen, and the
# two helper methods that used to launch it are inert in the final DEX.
assert 'navigation/RecognizeActivity;' not in add_fail
for sig in ['W()V', 'S(Lcom/oplus/consumerIRApp/navigation/fragment/AddFailFragment;)V']:
    helper = body('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/fragment/AddFailFragment', sig)
    assert 'invoke-' not in helper and 'return-void' in helper, sig
    assert 'RecognizeActivity' not in helper, sig
# OEM screen-feature query must be a plain false and never reach the framework.
oos = body('ConsumerIRApp', 'com/oplus/consumerIRApp/navigation/utils/b', 'd(Ljava/lang/String;)Z')
assert 'const/4 v0, 0x0' in oos and 'return v0' in oos and 'invoke-' not in oos
# Online/offline init diagnostics are tagged and must not print secrets.
sdk = source[('ConsumerIRApp', 'com/hzy/tvmao/KookongSDK')]
assert '"PaganiIR"' in sdk
assert not re.search(r'(?i)(appkey|app_key|secret|passphrase)\s*=\s*"?[A-Za-z0-9]{8,}', sdk)

# --- COUI bottom sheet: ColorOS-only window/observer bridges --------------
# android.view.OplusBaseLayoutParams and the com.oplus.wrapper.view.
# ViewTreeObserver bridge do not exist in this framework. The constant pool
# reference throws before any null check, so both must be gone from the DEX.
for app in ('OplusDocumentsReader', 'OcrScanner', 'ConsumerIRApp'):
    key = (app, 'com/coui/appcompat/panel/COUIBottomSheetDialog')
    assert key in source, app
    sheet = source[key]
    assert 'OplusBaseLayoutParams' not in sheet.replace(
        '# AOSP: android.view.OplusBaseLayoutParams is a ColorOS-only window flag', ''
    ).replace('# AOSP: no android.view.OplusBaseLayoutParams, so there is no oplusFlags', ''), app
    assert 'const-class v' not in ''.join(
        line for line in sheet.splitlines() if 'OplusBaseLayoutParams' in line), app
    for sig in ['addOSDKViewTreeObserver()V', 'removeOSDKViewTreeObserver()V']:
        helper = body(app, 'com/coui/appcompat/panel/COUIBottomSheetDialog', sig)
        assert 'invoke-' not in helper and 'return-void' in helper, (app, sig)

# --- Documents tool tab: remote-only conversions must be unavailable ------
# All eight IFormatInterface.ConvertType values are answered from the remote
# OCS function_switch_config, and the actual conversion runs through
# IAIInterface.n(), which this port pins to a failure callback because the
# AIUnit service is absent. The card must therefore not be offered.
format_api = body('OplusDocumentsReader',
                  'andes/oplus/documentsreader/formatconvert/FormatApi', 'IL1Iii(I)Z')
assert 'const/4 v0, 0x0' in format_api and 'return v0' in format_api
assert 'invoke-' not in format_api, 'conversion availability still queries config'
# The AI gate that already hides summary/translation stays a plain false.
ai_gate = body('OplusDocumentsReader',
               'andes/oplus/documentsreader/aidepend/impl/AIInterface',
               's(Landroid/content/Context;Ljava/lang/String;)Ljava/lang/Boolean;')
assert 'Boolean;->FALSE:' in ai_gate

# --- All inspected classes ----------------------------------------------
for (app, cls), text in source.items():
    for bad in LIVE_OEM:
        assert bad not in text, (app, cls, bad)

print('PASS: final DEX seamless/effect/Path/UserHandle fallbacks, private vault removal,'
      ' scanner single-activity startup, IR offline manual entry; runtime not tested.')
