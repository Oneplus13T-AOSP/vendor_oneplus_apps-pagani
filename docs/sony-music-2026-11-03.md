# Sony Xperia Music — XQ-GE44 73.1.A.2.74

공여: Sony XQ-GE44 Customized JP 73.1.A.2.74, product incremental 073001A002007400986449180, Android 17.
앱: SemcMusicApp / com.sonyericsson.music / 9.4.17.A.0.11 / 19537931, minSdk 30, targetSdk 37.
이전 XQ-FS44 9.4.16.A.0.9 포팅을 대체했다. 단순 핀 변경이 아니라 새 DEX 구조에 맞춰 재작성했다.

## 필요한 입력만 추출

새 덤프에는 product와 extraction-records만 남긴다. 사용자가 파티션 범위를 지정한 시점에
이미 생성된 system/system_ext는 정리했고 vendor/odm은 추출하지 않았다.
원본 이미지와 이전 덤프는 변경하지 않았다. extract-dump.py의 기본 파티션은 product다.
추가 파티션은 --partitions로 필요할 때만 지정한다.

## 이번 버전의 처리

- 구버전 Sony 코드는 classes.dex, 신버전은 classes2.dex에 위치한다.
- classes2의 ApiAvailabilityManager, MediaRouterUtils, PlayerServiceCompat 3개 클래스에서
  총 4개 메서드만 패치했다. Sony 전용 오디오 API/저전력 API 판정 false, DLNA 지원 false,
  두 Sony player factory null. 현재 버전에서 제거된 IlluminationController/IDD Reporter 패치는 이식하지 않았다.
- 필수 com.sony.device 포함 OEM uses-library 14개와 Sony DLNA provider service만 AXML에서 제거한다.
- classes.dex/클래스 정의/리소스/assets/원래 JNI 및 기타 페이로드는 보존한다.
- SettingsFragment, LocalPlayer, AudioEffectsControl의 원본 smali 해시를 유지해 기본 재생/EQ 경로를 보존했다.
- 두 DEX를 압축하지 않고 정렬한다.

## ABI·의존성·중복·정책

ARM64 JNI: libandroidx.graphics.path.so, libdatastore_shared_counter.so.
둘 다 AArch64 ELF이며 모든 LOAD p_align=16384. 외부 DT_NEEDED는 libc.so/libm.so/libdl.so뿐이다.
이 세 시스템 라이브러리는 Sony에서 복사하지 않는다. ROM의 기존 Bionic 공용 라이브러리를 참조한다.
APK의 다른 ABI JNI도 원본 바이트로 보존하며, 모듈/별도 JNI 설치는 ARM64로 한정한다.
product/app/SemcMusicApp/lib/arm64에만 설치하고 전역 lib64 모듈/블롭은 추가하지 않는다.

중복 검사 경로: vendor/oneplus/oreality-pagani, vendor/oneplus/pagani,
vendor/oneplus/sm8750-common, vendor/oplus/camera.
이 네 폴더에서 신규 JNI 두 이름과 일치하는 파일 및 빌드/블롭 목록 참조는 없었다.
빌드 모듈은 기존 SemcMusicApp을 갱신하며 별도 동명 .so 모듈은 만들지 않는다.

product/app 일반 앱 설치. 신규 sepolicy/priv-app allowlist 없음.
READ_MEDIA_AUDIO, POST_NOTIFICATIONS, FGS mediaPlayback 권한 및 playback service는 원본 유지.
Android 17 ACCESS_LOCAL_NETWORK 등 추가 권한도 원본 유지하며 실제 허용 동작은 기기 검증 대상이다.
Sony 관련 권한 이름이 남아 있어도 SDK/서비스 자체를 포팅하는 것은 아니다.

## 수행한 검사

- 원본 APK CRC, 패키지/버전 확인, 현재 Sony 외부 타입 및 참조 경로 재조사.
- 변경 전 메서드 파일 해시 검사 및 fuzz=0 패치/DEX 조립.
- 중복/유실 DEX 클래스 없음, 변경하지 않은 DEX/페이로드 동일.
- uses-library 검사/ZIP 16KB 정렬, 실제 ELF ABI/DT_NEEDED/LOAD 정렬 통과.
- 재생·EQ 클래스 동일 및 4개 안전 게이트를 최종 DEX에서 검사.
- 생성 APK를 제거하고 실제 extract-utils로 새 product 덤프에서 재추출·재패치하여 같은 해시 재현.

| 입력 | SHA-256 |
| --- | --- |
| stock | 352c04ed4056b6e3664707c8dcae16f1d870357360f2a714b498ce1e64b8e3c4 |
| unsigned port | 6a361c034045ff8e765744ea82c0c4d1513fac36b72a9031261879968bf35466 |

원본/결과 SHA-1과 SHA-256은 proprietary 목록에 고정한다. APK/블롭/대용량 파일은 Git에서 제외한다.

## 남은 실기기 확인

초기 포팅 당시 ROM 빌드·실기기 검증은 수행하지 않았다. 이후 사용자가 13T에서
Xperia Music 작동을 확인했다. 아래 항목은 기능별 추가 확인 목록이며, 모든
외부 연동이나 권한·SELinux 경로의 완전 검증을 의미하지 않는다.
Google Drive/Mora/Cast/보호 음원 등 외부 계정·서명·기기 연동도 동작을 보장하지 않는다.

1. 첫 실행, 음원/알림 권한, MP3/FLAC 스캔·재생·탐색·재생목록.
2. 화면 끄기/백그라운드/잠금화면 알림·블루투스 미디어 버튼.
3. EQ 메뉴, UI/Jetpack 네이티브 로드, 크래시 로그.
4. logcat의 NoClassDefFoundError/NoSuchMethodError/UnsatisfiedLinkError/SecurityException 및 AVC 거부.

표준 DISPLAY_AUDIO_EFFECT_CONTROL_PANEL 인텐트와 AudioEffect session 처리는 원본 그대로다.
ORealityControl은 현재 이 인텐트 처리기로 등록되지 않아 자동/강제 OReality 설정 연결은 하지 않았다.
시스템 출력에 적용되는 음향 효과와 앱에서 설정 화면을 여는 동작은 별개다.
