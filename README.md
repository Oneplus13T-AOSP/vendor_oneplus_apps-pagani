# Sony Xperia Music for Pagani / PixelOS Android 17

OnePlus 13T용 Sony Xperia Music만 포함한다. 사용자가 13T에서 작동을 확인했다.
문서·스캐너·IR 포팅은 종료했으며 빌드 항목, APK 캐시, 패치, 전용 호환 코드와 검사를 제거했다.
Sony 원본·패치 APK와 재생/EQ 처리 및 해시 핀은 변경하지 않는다.

| 모듈 | 패키지 | 버전 | 공여 펌웨어 |
| --- | --- | --- | --- |
| SemcMusicApp | com.sonyericsson.music | 9.4.17.A.0.11 / 19537931 | Xperia XQ-GE44 Customized JP 73.1.A.2.74 |

## 추출과 검증

ROM 루트에서 실행한다. 표준 extract-utils의 `extract-files.py` / `proprietary-files.txt`
방식을 유지하며 원본 SHA-1, 수정 후 서명 전 SHA-1, SHA-256을 함께 검사한다.

```sh
python3 vendor/oneplus/apps-pagani/extract-files.py /path/to/xperia-dump
python3 vendor/oneplus/apps-pagani/setup-makefiles.py
python3 vendor/oneplus/apps-pagani/tools/sony/port.py verify --rom-root . --app SemcMusicApp
python3 vendor/oneplus/apps-pagani/tests/verify-sony-music.py --rom-root .
```

외부 작업 폴더에서는 추출/설정 스크립트에 `--rom-root /path/to/pixelos`를 지정한다.
추출은 `--no-cleanup`을 강제하며 원본 덤프를 변경하지 않는다. ADB 추출은 비활성화다.
공여 버전 갱신은 `sony-sources.json`과 패치를 먼저 검토하고 `--update-pins`를 명시한다.
단독 `--kang`은 SHA-256과 불일치하는 갱신을 막기 위해 거부한다.

필요한 product 파티션만 추출하는 도구:

```sh
python3 vendor/oneplus/apps-pagani/tools/sony/extract-dump.py /path/to/xperia-images --dumpyara /path/to/dumpyara --partitions product
```

## APK 재빌드와 서명

```sh
python3 vendor/oneplus/apps-pagani/tools/sony/port.py build --rom-root . --app SemcMusicApp
python3 vendor/oneplus/apps-pagani/tools/sony/port.py sign --rom-root . --app SemcMusicApp
```

ROM 입력은 `proprietary/product/app/SemcMusicApp/SemcMusicApp.apk`이며 서명 전 상태다.
ROM 빌드에서 platform 키로 서명한다. 테스트 서명본은 `proprietary/signed/SemcMusicApp/`에
생성한다. 모든 APK, proprietary 블롭·JNI·빌드 기록과 개인 키는 Git에 포함하지 않는다.
추출과 서명 전 결과 재현에는 개인 키가 필요하지 않다.

## ROM 포함

기존 device.mk 연결을 유지한다.

```make
$(call inherit-product, vendor/oneplus/apps-pagani/apps.mk)
```

`TARGET_ENABLE_SONY_MUSIC := false` 또는 `TARGET_ENABLE_PAGANI_APPS := false`를
inherit 앞에 지정하면 제외한다. 문서·스캐너·IR을 다시 활성화하는 스위치는 없다.
일반 product/app에 ARM64 JNI를 앱 전용 lib/arm64 경로로 설치한다.
외부 의존성 libc/libm/libdl은 ROM의 Bionic을 사용하며 Sony에서 복사하지 않는다.
새 전역 라이브러리, sepolicy, privileged allowlist는 추가하지 않는다.

[포팅·의존성 기록](docs/sony-music-2026-11-03.md)을 참고한다.
이번 정리는 ROM 빌드·플래싱이나 연결된 기기 앱 삭제를 수행하지 않는다.
