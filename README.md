# Pagani manufacturer apps / PixelOS Android 17

OnePlus 13T에서 사용할 제조사 앱을 원본·패치 후 해시로 고정하고 재현한다.
현재 포함한 앱은 **OnePlus 13T PKX110_17.0.0.104(CN01)** 스톡 펌웨어에서
추출한 ColorOS 17 문서, OSee 스캐너, IR 리모컨이다.
앱 모듈·패치 폴더·APK 파일명은 공여 원본의 이름을 유지한다.
**APK 빌드와 정적 검증 단계이며, 13T 실기기 동작과 전체 ROM 빌드는 미검증이다.**

| 모듈 | 패키지 | 원본 버전 |
| --- | --- | --- |
| OplusDocumentsReader | andes.oplus.documentsreader | 17.1.28 / 17001028 |
| OcrScanner | com.coloros.ocrscanner | 17.1.13 / 170113 |
| ConsumerIRApp | com.oplus.consumerIRApp | 17.0.30 / 170000030 |

## 추출과 핀

ROM 체크아웃의 `tools/extract-utils`를 실제로 사용한다.
저장소 위치는 `vendor/oneplus/apps-pagani`이며 ROM 루트에서 다음을 실행한다.

```sh
python3 vendor/oneplus/apps-pagani/extract-files.py --section 'Apps - Extracted from OnePlus 13T PKX110_17.0.0.104(CN01)' /path/to/cos-dump
python3 vendor/oneplus/apps-pagani/setup-makefiles.py
python3 vendor/oneplus/apps-pagani/tools/port.py verify --rom-root .
```

현재 공여 덤프는 `/home/ccc/dumpyara/working/cos`다.
추출은 `--no-cleanup`을 기본으로 사용하여 이 저장소의 소스와 다른 제조사 입력을
보존한다. ADB 추출은 비활성화되어 있으며 원본 덤프는 읽기만 한다.
외부 작업 폴더에서 실행하면 `--rom-root /path/to/pixelos`를 명시한다.

`proprietary-files.txt`는 표준 문법을 사용한다.

```text
source/path.apk:product/app/Module/Module.apk;EXTRACT_ONLY|STOCK_SHA1|FIXED_UP_SHA1
```

- 원본 SHA-1과 서명 전 패치 APK의 SHA-1을 `extract-utils`가 검사한다.
- `sources.json`의 원본 SHA-256, 패키지·버전, 수정 전 smali 해시도 검사한다.
- `proprietary-files.sha256sum`으로 원본과 서명 전 결과의 SHA-256도 고정한다.
- 새로 추가한 DEX의 ZIP 시간은 고정한다. 패치 결과 핀은 플랫폼 서명 키에 의존하지 않는다.
- smali 조립은 DEX별 단일 스레드로 실행해 병렬 intern 순서에 따른 해시 변동을 막는다.
- `.build.json`에는 앱별 설정, 패치/호환 소스/도구 해시와 결과 해시를 기록한다.
- JNI는 APK에서 원본 바이트 그대로 앱별 디렉터리에 준비한다.
- `EXTRACT_ONLY`는 자동 android_app_import 생성을 막는다. JNI 전용 설치와 선택
  스위치는 `build/apps-prebuilt.mk`의 단일 모듈 정의가 담당한다.
- `setup-makefiles.py`는 Android.bp, Android.mk, apps-pagani-vendor.mk,
  BoardConfigVendor.mk를 재생성한다. 추출·패치·서명은 수행하지 않는다.

원본 버전 변경 시 설정·패치를 검토한 뒤 TXT와 SHA-256 목록의 핀을 명시적으로 갱신해야 한다.
검토 후 해당 앱 섹션에 `--update-pins`를 명시하면 표준 `--kang` 처리와
SHA-256 목록 갱신을 함께 수행한다. 원본 SHA-256과 수정 전 smali 검사는 유지한다.
단독 `--kang`은 SHA-1만 바뀌어 SHA-256과 불일치하는 상황을 막기 위해 거부한다.
공여 버전을 바꿀 때는 기존 `proprietary/stock/<모듈>`을 먼저 백업·이동한다.
다른 버전의 원본 캐시는 자동으로 덮어쓰지 않는다.
출처가 다른 APK를 자동으로 받아들이거나 핀을 자동 갱신하지 않는다.

## APK 출력과 테스트용 서명

ROM 입력은 `proprietary/product/app/<모듈>/<모듈>.apk`의 **서명 전 APK**다.
이는 직접 설치하는 파일이 아니며, ROM 빌드에서 platform 키로 서명된다.
설치 테스트용 APK는 별도로 생성한다.

```sh
python3 vendor/oneplus/apps-pagani/tools/port.py sign --rom-root .
python3 vendor/oneplus/apps-pagani/tools/port.py verify --rom-root . --signed
```

서명본은 `proprietary/signed/<모듈>/<모듈>.apk`다.
현재 서명 도구는 PixelOS의 `vendor/lineage-priv/keys/platform.*`를 사용한다.
추출과 서명 전 APK 재현에는 개인 키가 필요하지 않으며, 키는 저장소에 포함하지 않는다.
`tools/port.py build --rom-root . --app OplusDocumentsReader`처럼 추출한 원본 캐시에서
앱 하나만 다시 빌드할 수 있다. `--app`은 build/sign/verify에 모두 적용된다.

## ROM 내장

사용자가 기기 트리의 `device.mk`에 추가하고 직접 ROM을 빌드한다.

```make
$(call inherit-product, vendor/oneplus/apps-pagani/apps.mk)
```

개별 제외 변수는 위 inherit 구문 앞에서 `false`로 지정한다.

```make
TARGET_ENABLE_PAGANI_DOCUMENTS := false
TARGET_ENABLE_PAGANI_SCANNER := false
TARGET_ENABLE_PAGANI_IRREMOTE := false
# 전체 제외: TARGET_ENABLE_PAGANI_APPS := false
```

일반 `product/app`에 설치하며 앱 전용 JNI는
`product/app/<모듈>/lib/arm64`에 설치한다. 전역 lib64, 새 init 서비스,
SELinux 정책, priv-app 허용 목록은 추가하지 않는다.
카메라·마이크 등 런타임 권한과 모든 파일 액세스 AppOps는 별도 확인 대상이다.

## 현재 호환 패치

- 세 OPlus 앱의 OplusBuild 참조를 앱 전용 호환 클래스로 연결한다.
  기존 oplus-fwk 부트 클래스와의 충돌을 피하고 OEM SDK 버전은 0으로 응답한다.
- 문서의 OEM MultiWindowTrigger 생성은 기존 미지원 콜백으로 대체한다.
  Android 자체 분할 화면은 변경하지 않는다.
- 문서 17.1.28의 STInputConnectionNew(`emo.simpletext.control.t`)에
  한글 조합/확정 중 Editable 재초기화 재진입을 막는 깊이 카운터를 적용한다.
  기존 nabu 17.1.32의 `u` 클래스 패치를 이 버전의 `t`에 맞춰 이식했다.
- 문서의 속성·저장소·기능 조회는 앱 전용 어댑터를 사용한다.
  실제 공유 저장소와 마운트된 USB 볼륨을 조회한다.
- 세 앱의 ColorOS 합성 효과(`OplusViewBackgroundRenderEffect`,
  `OplusRenderEffect`, `OplusViewSeamless`, `OplusPath`, `OplusOutline`,
  `OplusChangeTextUtil`, `oplus.wrapper.os.UserHandle`)를 앱 전용
  `UiCompat`/`PathCompat`으로 대체한다. 효과는 기존 평면 배경을 유지하고,
  Path는 AOSP `addRoundRect`로 같은 형상을 만든다. 렌더 효과를 위조해 성공을
  가장하지 않는다.
- 문서 관리 탭의 개인 금고 항목 두 곳(`MainActivityViewModel`, `FolderTabFragment`)을
  목록에 추가하지 않는다. 사용자 금고 데이터는 삭제하지 않는다.
- 스캐너 단독 실행 경로의 배경 효과와 촬영 프레임 Path를 위 대체 구현으로 바꾼다.
- IR은 앱에 번들된 `kkoffline16.db`를 사용한다. 오프라인 DB 경로와 `OfflineOnly`를
  `KookongSDK.init` **이전**에 설정하고, SDK 초기화를 최초 실행 플래그와 분리한다.
  `setOfflineDBPath`는 내부적으로 `com.kookong.sdk.ir.e1`을 로드하는데, 이 클래스의
  정적 초기화가 `KookongSDK.getContext()`를 호출하고 `sContext`가 비어 있으면
  `IllegalStateException`을 던진다. 따라서 그보다 먼저 `KookongSDK.preinit(Context)`를
  호출해 `sContext`만 채운다. `preinit`은 `init`과 달리 앱키/DB/native 초기화를 하지 않는다.
  홈 메뉴의 QR 추가 항목과 매치 실패 화면의 사진 인식 진입을 숨긴다. 수동 추가가
  기본 경로이며 인증 성공을 위조하지 않는다.
- 문서 도구 탭의 파일 변환 8종(PDF→Word/Excel/PPT, Office→PDF, iWork→PDF,
  Pages→Word, Numbers→Excel, Keynote→PPT)은 노출하지 않는다. 변환 실행 경로가
  `ConvertProxyTask` → `IAIInterface.n()`이고, 이 포트는 AIUnit 서비스가 없어
  `n()`을 실패 콜백으로 고정했다. 즉 카드만 보이고 결과 파일을 만들 수 없으므로
  `FormatApi.IL1Iii`가 false를 반환한다. AI 요약·번역은 같은 이유로 이미 숨겨져 있다.
  사용자 문서 삭제나 성공 위조는 하지 않는다.
- 원본 manifest, 리소스, assets, JNI 바이트를 유지한다.
  IR 송신은 원본 ConsumerIrManager 경로를 유지한다.

## 프레임워크 측 보완 (hardware/oplus/oplus-fwk)

세 앱은 부트 클래스패스의 `oplus-fwk`도 사용한다. 여기에 없던 COUI 그래픽·머티리얼
클래스를 채웠다. 이 클래스들은 전역이므로 카메라·갤러리도 같은 심볼을 쓴다.
`OppoGallery2.apk`, `OplusCamera.apk`의 실제 method table을 읽어 참조되는 시그니처를
전부 대조했고, 갤러리가 추가로 요구하는 `setAlpha(RenderNode,F)`,
`setRotationX/Y`, `setOutlineRoundRect`, `createRenderValueAnimator`,
`getFrameNumber`, `setMetaBallChain(View,Set)`도 포함했다.
`tests/check-fwk-api.py`로 이 13개 클래스에 대한 APK별 참조 멤버를 다시 대조할 수 있다
(현재 169개 참조 전부 해석됨).
`--selftest`는 전달한 APK 전체를 사용하므로 입력 순서에 의존하지 않는다.
갤러리를 포함해야 네 가지 변이의 대상 시그니처를 모두 검사할 수 있다. 각 변이는
컴파일에 성공한 뒤 예상한 descriptor 누락으로 검출되어야 하며, 컴파일 오류를
시그니처 검사 성공으로 취급하지 않는다.

- `com.oplus.graphics.OplusCanvas`: AOSP `Canvas.drawRoundRect`로 같은 도형을 그린다.
  부드러운 모서리 연속성만 빠진다.
- `com.oplus.view.material.OplusMaterialUtil`과 `OplusMaterial*Params`: 파라미터
  객체는 값을 그대로 보관하고, util의 setter는 **false**를 반환한다. 이 ROM에는
  SurfaceFlinger 머티리얼 효과 경로가 없어서, true를 반환하면 위젯이 효과가 걸린
  것으로 착각해 일반 배경/아웃라인/그림자 그리기를 건너뛴다.
- `com.oplus.animation.OplusAsyncAnimatorUtils`: 같은 View 속성 변경을 UI 스레드에서
  수행하고 true를 반환한다. `setOutlineRoundRect`는 `View.setClipBounds` 대신
  `ViewOutlineProvider` + `setClipToOutline(true)`로 구현한다. 갤러리의
  `resetOutlineToNone()`이 `setOutlineProvider(null)` + `setClipToOutline(false)`만
  하므로, `setClipBounds`를 쓰면 전환 후 사진이 잘린 채 남는다. 전달된 radius는
  `Outline.setRoundRect`에 반영하고, smoothing weight는 AOSP 대응이 없어 무시한다.
- `com.oplus.view.OplusRenderNodeAnimator`: `createRtAnimator`는 null,
  `getFrameNumber`는 -1을 반환한다. `createRenderValueAnimator`는 호출자가 설정한
  duration·interpolator·listener를 유지하도록 전달된 Animator를 그대로 반환한다.
  null을 검사하는 COUI 경로와 원본 Animator를 실행하는 Gallery 경로를 구분하며,
  실제 애니메이션 완료와 상태 복구는 실기기 확인이 필요하다.
- `com.oplus.util.OplusLog`, `com.oplus.util.OplusDarkModeUtil`,
  `com.oplus.view.OplusWindowAttributesManager`: AOSP 동등 구현.
  `com.oplus.util.OplusTypeCastingHelper`는 `framework.jar`에 이미 동일 구현이 있어
  `oplus-fwk`에 두지 않는다.
- `android.view.OplusBaseLayoutParams`는 이 ROM의 `framework.jar`에도 소스에도 없어
  프레임워크가 아니라 앱 패치에서 처리한다. `COUIBottomSheetDialog`의 두 네비게이션 바
  메서드에서 해당 클래스 참조와 `oplusFlags` 갱신을 제거하고, ColorOS 전용
  `wrapper.view.ViewTreeObserver` 브리지 메서드는 no-op으로 만든다. 표준 Window flag와
  WindowInsetsController 처리는 그대로 남는다.

## 로컬 기능에 맞춘 OEM 연동 정리

문서 앱의 클라우드 드라이브·OShare·개인 금고를 비활성화했다.
인기 앱의 로컬 문서 검색, 다운로드·블루투스, 일반 공유와 저장소 권한 설정은 유지한다.
스캐너·IR 설정의 제조사 피드백 항목은 숨겼다.
문서 앱의 번역·요약 등 AI 기능과 Office/PDF AI 도우미는 비활성화했다.
별도 번역기는 포함하지 않는다. [AI 제거 범위와 검사](docs/no-ai-2026-11-03.md)를 참고한다.
[앱별 처리·재현 검사·13T 점검표](docs/local-features-2026-11-03.md)를 참고한다.

## 검증 범위

[의존성·ABI·권한·SELinux·블롭 중복 감사](docs/audit-2026-11-02.md)를 참고한다.
APK ZIP 정렬은 ELF의 16KB 페이지 호환성과 별개다. 이번 덤프에는 ELF LOAD 정렬이
4096인 라이브러리가 있다. 스캐너의 보호된 보안 플러그인도 완전한 정적 분석 대상에서
제외되어 있다. 실기기 검증을 대신하는 검사로 해석하지 않는다.

OnePlus 13T에서 문서 한글 입력/저장, 스캐너 촬영/보정/PDF/OCR,
IR 코드 다운로드/실제 송신을 확인해야 한다. BaseOcrScanner/AIUnit 등 별도
서비스는 포함하지 않았으며 ColorOS 계정·AI·클라우드·OEM 권한 연동은 미검증이다.
연결된 OnePlus 11에는 설치하지 않았다.

## 삼성·소니 등 다른 제조사 앱 추가

Sony Xperia Music을 추가했다. Sony 입력·패치는 `sony-sources.json`과 `tools/sony/`에서 독립적으로 관리한다. 앱마다 다음을 독립적으로 관리한다.

1. 원본 덤프와 배포 버전을 고정하고 manufacturer, package, version, SHA-256,
   ABI/minSdk, 수정할 DEX와 smali 해시를 sources.json에 등록한다.
2. proprietary-files.txt에 제조사·펌웨어 출처별 섹션과 원본/패치 후 SHA-1을 추가한다.
3. patches/<모듈>과 필요한 호환 소스·추가 DEX 클래스 목록을 명시한다.
   OPlus 호환 코드를 타 제조사 앱에 자동 주입하지 않는다.
4. 모듈과 선택 스위치를 apps.mk 및 build/apps-prebuilt.mk에 추가한다.
5. 원본 덤프에서 재추출해 고정 결과를 재현하고 ABI/권한/정책/실기기를 검증한다.

다른 덤프를 사용하는 앱은 해당 섹션만 선택하여 추출한다.

```sh
python3 vendor/oneplus/apps-pagani/extract-files.py --section 'Apps - Extracted from OnePlus 13T PKX110_17.0.0.104(CN01)' /path/to/cos-dump
# 설정/패치를 먼저 검토하고 핀을 의도적으로 갱신할 때:
python3 vendor/oneplus/apps-pagani/extract-files.py --update-pins --section 'Apps - Extracted from OnePlus 13T PKX110_17.0.0.104(CN01)' /path/to/cos-dump
```

삼성 Knox/소니 프레임워크, 서비스와 서명 종속성은 원본 핀과 별개의 호환성 문제다.
핀 일치만으로 포팅 성공으로 간주하지 않는다.

## Git 관리

`*.apk`로 모든 APK를 위치·용량과 관계없이 제외하고 `proprietary/` 전체도 제외한다.
소스·패치·고정 해시·추출/빌드 설정·문서를 커밋한다. 다른 PC에서는 공여 덤프에서
재추출한다. 원본 APK, 생성 APK, JNI와 개인 키는 업로드하지 않는다.

## Sony Xperia Music

Sony **XQ-GE44 Customized JP 73.1.A.2.74**의 **product 파티션만** 사용한다.
원본 `product/deletable-app/SemcMusicApp/SemcMusicApp.apk`,
패키지 `com.sonyericsson.music`, 버전 **9.4.17.A.0.11 / 19537931**, minSdk 30 / targetSdk 37.
기존 XQ-FS44 / 9.4.16.A.0.9 입력을 대체했으며 모듈/파일명은 원본 `SemcMusicApp`을 유지한다.
`TARGET_ENABLE_SONY_MUSIC := false`로 제외할 수 있다. 기존 apps.mk 상속으로 ROM에 포함된다.

```sh
# 필요한 product만 추출한다. 원본 이미지와 기존 덤프는 보존한다.
python3 vendor/oneplus/apps-pagani/tools/sony/extract-dump.py /path/to/XQ-GE44-images --dumpyara /path/to/dumpyara --partitions product
# --partitions를 생략해도 기본값은 product. 다른 파티션은 필요할 때만 명시한다.
python3 vendor/oneplus/apps-pagani/extract-files.py --section 'Apps - Extracted from Sony Xperia XQ-GE44 Customized JP 73.1.A.2.74' /path/to/xperia-dump
python3 vendor/oneplus/apps-pagani/tools/sony/port.py build --rom-root . --app SemcMusicApp
python3 vendor/oneplus/apps-pagani/tools/sony/port.py verify --rom-root . --app SemcMusicApp
python3 vendor/oneplus/apps-pagani/tests/verify-sony-music.py --rom-root .
```

`tools/port.py`는 기존 OPlus 세 앱 전용이다. Sony 입력·메서드 해시·선택 DEX는
`sony-sources.json`, Sony 전용 도구는 `tools/sony`에서 관리한다.
현재 패치는 classes2.dex의 3개 클래스/4개 메서드에서 Sony 오디오 API 지원·DLNA·
두 player factory를 비활성화한다. 삭제된 이전 버전의 조명/IDD 클래스 패치는 적용하지 않는다.
OEM uses-library 14개와 Sony DLNA provider service만 원본 바이너리 manifest에서 제거한다.
원본 리소스/재생 코드/권한/기본 EQ 호출을 유지하고 OPlus 호환 DEX는 주입하지 않는다.

JNI `libandroidx.graphics.path.so`, `libdatastore_shared_counter.so`는 원본 ARM64 바이트 그대로
앱 전용 lib/arm64에 설치한다. 두 ELF 모두 16KB LOAD 정렬이며 DT_NEEDED는 libc/libm/libdl뿐이다.
다른 ABI의 APK 내부 라이브러리도 원본 바이트로 보존하지만 설치 모듈은 ARM64로 제한한다.
추가 vendor/system 전역 블롭·sepolicy·priv-app 허용 목록은 추가하지 않는다.
원본/수정 APK SHA-1 및 SHA-256을 공통 proprietary 목록에 고정하고 APK는 모두 Git에서 제외한다.
ROM 빌드에서 platform 키로 서명되며 별도 설치용 서명 APK는 생성하지 않았다.

표준 DISPLAY_AUDIO_EFFECT_CONTROL_PANEL 호출은 유지한다. 현재 ORealityControl은 이 인텐트의
처리기로 등록되지 않아 OReality 설정 화면으로 강제 연결하지 않는다. 시스템 음향 효과 적용과
EQ 설정 화면 호출은 별개다. 실제 재생/권한/SELinux 동작은 13T에서 확인해야 한다.
[분석·검증·점검 목록](docs/sony-music-2026-11-03.md)을 참고한다.
