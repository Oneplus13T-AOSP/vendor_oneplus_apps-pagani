# ColorOS 연동 정리 — 2026-11-03

## 기준과 범위

수정 대상은 OnePlus 13T PKX110_17.0.0.104(CN01)에서 추출한 다음 APK다.

| 앱 | 패키지 | 버전 |
| --- | --- | --- |
| OplusDocumentsReader | andes.oplus.documentsreader | 17.1.28 |
| OcrScanner | com.coloros.ocrscanner | 17.1.13 |
| ConsumerIRApp | com.oplus.consumerIRApp | 17.0.30 |

사용자가 제공한 OnePlus 11 ColorOS 16 화면은 문서 앱 16.8.32다.
샤오미 패드 5의 기존 포트는 17.1.32다. 버전 및 휴대폰/태블릿 구성 차이가 있으므로
화면이 다르다는 이유만으로 버그나 메뉴 누락을 확정하지 않았다. 패치는 현재 17.1.28
APK 코드에 맞췄으며, 16.8.32의 화면 구성과 일치한다고 주장하지 않는다.

## 문서 앱

| 항목 | 처리 | 근거/보존 범위 |
| --- | --- | --- |
| 클라우드 드라이브 | 미지원 고정, 업로드/패키지 조회 진입 차단 | clouddrive/a의 지원 조회 false, 업로드 진입 no-op, 대상 패키지 빈 문자열. 일반 로컬 저장과 일반 공유는 유지 |
| OnePlus/OPPO/realme Share | 기존 OShare 미지원 경로 사용 | SuperAppHelper.g()가 disabled=true 반환. 없는 OplusDevicepolicyManager 직접 호출도 제거 |
| 개인 금고 | 기능 표시 판정과 인증 진입 차단 | FeatureCompat 암호화 판정, zy/a.k() false. com/oplus/encrypt/f.a()에서 OEM 인증을 시작하지 않음. 성공 콜백 위조 없음 |
| 인기 앱에서 문서 검색 | 유지, OShare 항목만 제외 | LINE/Telegram/WhatsApp/QQ/WeChat 등 일반 앱의 기존 로컬 폴더 분류/설치 여부 처리 유지. 중국 앱이라는 이유로 일괄 제거하지 않음 |
| 다운로드/블루투스 | 유지 | SuperAppHelper의 일반 카테고리 구성 메서드를 원본과 비교 |
| 시스템 파일 액세스 | 유지 | 실제 android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION 및 package: 경로. 사용자 권한 승인 흐름 유지 |
| 저장 공간 정리 | 기존 지원 여부 검사 유지 | zy/a가 실제 ColorOS 휴대폰 관리자 Activity 존재 여부를 조회. 부재한 서비스를 지원한다고 위조하지 않음 |
| 문서 요약/번역 등 AI | 후속 사용자 요청으로 전체 비활성화 | [AI 제거 기록](no-ai-2026-11-03.md) 참고. 별도 번역기 추가 안 함 |
| 글꼴 다운로드 | 유지 | 클라우드 드라이브와 별도 기능 |
| 파일 변환(8종) | 미지원 처리 | 변환은 `ConvertProxyTask` → `IAIInterface.n()` 경로이며, 이 포트는 AIUnit 서비스 부재로 `n()`을 실패 콜백으로 고정했다. 실제 변환·저장이 불가능하므로 `FormatApi.IL1Iii`가 false를 반환해 카드를 노출하지 않는다. 성공을 위조하지 않으며 사용자 문서는 삭제하지 않는다 |

지원 판정과 실행 경로를 수정했다. 불필요한 미사용 SDK 클래스나 리소스/문구 전체를
삭제하는 방식은 사용하지 않았다. 앱의 전체 네트워크/통계 트래픽을 제거한 것도 아니다.
사용자 문서·다운로드·기존 개인 금고 데이터는 삭제하거나 변환하지 않는다.

개인 금고의 encryption_not_support처럼 이름이 부정형인 플래그는 모든 OEM 플래그를
false로 대체한다고 기능이 꺼지는 것이 아니다. 이번에는 실제 암호화 지원 판정 자체를
false로 고정하여 provider 응답이나 기기 구성에 따라 다시 켜지지 않도록 했다.

## 스캐너와 IR

두 앱의 설정 및 OEM SDK 진입 경로를 함께 검토했다.

- 스캐너: 설정의 key_setting_help_feedback을 숨기고 FeedbackHelper 실행 메서드를
  차단했다. 이 APK의 Preference.setVisible에 해당하는 실제 메서드는 M0(Z)V다.
  문서 앱/IR에 있는 비난독화 AndroidX API 이름을 그대로 주입하지 않았다.
- IR: setting_feedback을 숨기고 SDK 제목/리스너 초기화 경로를 제외했다.
  해당 클릭 리스너도 OEM 피드백을 열지 않도록 처리했다.
- 두 앱의 개인 정보·권한·앱 정보·버전 표시를 유지한다.
- IR의 코드 데이터 다운로드, KuKong 온라인 제어 설정, ConsumerIrManager 송신 경로를
  제거하지 않았다. 클라우드 드라이브 제거를 이유로 인터넷 권한을 일괄 삭제하지 않았다.
- 스캐너의 촬영·OCR·문서 스캔·필기 제거·문서 앱 결과 반환 및 설치된 일반 앱의 QR/
  결제 선택 경로를 이번 패치에서 변경하지 않았다. 이 기능들의 실기기 성공을 보장하지 않는다.
- 문서 앱은 OseeSdk에서 설치된 com.coloros.ocrscanner를 조회하여
  coloros.intent.action.SCANNER_MAIN_PAGE로 실행한다. 대상 스캐너 Manifest의
  SCANNER_MAIN_PAGE/HQ_DOC_SCANNER/PAPER_RESTORE_SCANNER를 확인했다.
  BaseOcrScanner를 추가로 포팅해야 한다는 결론은 내리지 않았다.

## 검증과 재현

모든 원본 stock SHA-1/SHA-256, 원본 Manifest/리소스/assets/JNI, DEX 클래스 집합을
유지한다. 새로 수정한 smali 파일은 sources.json의 원본 SHA-256 검사에 포함한다.
기능 변경에 따라 unsigned fixed SHA-1과 SHA-256을 갱신하고 원본 덤프에서 다시
추출하여 첫 빌드와 같은 고정 결과가 나오는지 검사한다.

```sh
python3 vendor/oneplus/apps-pagani/extract-files.py /path/to/cos-dump
python3 vendor/oneplus/apps-pagani/tools/port.py verify --rom-root .
python3 vendor/oneplus/apps-pagani/tests/verify-local-features.py --rom-root .
python3 vendor/oneplus/apps-pagani/tests/verify-aosp-runtime.py --rom-root .

# boot classpath 호환 클래스가 실제 APK 호출과 맞는지 (Gallery/Camera 포함)
python3 vendor/oneplus/apps-pagani/tests/check-fwk-api.py --rom-root . \
  --apk <gallery.apk> --apk <camera.apk> \
  --apk proprietary/product/app/OcrScanner/OcrScanner.apk
```

최종 DEX 검사에서는 지원 플래그/진입 차단 외에도 일반 앱 분류 메서드 보존,
Android 표준 파일 접근 설정 경로, 스캐너/IR의 실제 Preference API 정의를 확인한다.
`verify-aosp-runtime.py`는 seamless/배경 효과/gradient/Path/UserHandle 대체가 원본
DEX에 남지 않았는지, 관리 탭의 개인 금고 add가 stock 대비 정확히 한 번씩 줄었는지,
IR의 오프라인 DB 경로·모드 설정이 `init`보다 앞서는지, QR/사진 인식 진입이 제거됐는지를
검사한다. 이 검사는 ART 실행이나 실기기 UI 검증을 대신하지 않는다. JNI/Manifest/정렬/클래스
중복 검사는 기존 port.py 검증을 함께 사용한다.

변경 전 서명 테스트 APK는 새 unsigned payload와 일치하지 않으므로 최신 결과로
전달하지 않는다. 기존 테스트 산출물은 .work/ 아래에 보관하며, ROM 입력은 계속
proprietary/product/app의 unsigned APK다. 전체 ROM 빌드는 사용자가 수행한다.

## 13T 실기기 점검

1. 최초 권한 미승인/승인 후 모두 앱 시작, 최근·도구·관리·설정 화면을 연다.
2. 클라우드 드라이브·OShare·개인 금고 메뉴가 홈/관리/파일 길게 누르기 메뉴에
   남지 않는지 확인한다. 기존 설정/앱 데이터가 있는 업그레이드 상태도 점검한다.
3. 일반 앱 검색 설정과 실제 설치된 앱의 로컬 문서, 다운로드·블루투스 문서를 확인한다.
   저장소 접근 권한은 사용자 승인 후에만 기대한다.
4. Word/Excel/PPT/TXT 새 파일 생성·한글 조합·저장·재열기, PDF 열기/내보내기,
   다른 앱의 content:// 문서 열기와 자동 저장, 이름 변경·삭제·복원을 확인한다.
5. 문서 앱에서 문서 스캔/필기 제거를 실행하고 촬영·취소·결과 반환·저장·재열기를 확인한다.
   스캐너 앱 단독 실행 성공만으로 이 왕복 검증을 대신하지 않는다.
6. 스캐너/IR의 OEM 피드백 항목이 사라지고 앱 정보·권한·버전 화면은 유지되는지 확인한다.
7. IR 리모컨 추가·코드 다운로드·전송, 앱 재실행 후 설정과 리모컨 데이터 보존을 확인한다.
8. AOSP 기본 분할 화면과 키보드 입력, 앱 백그라운드 복귀를 확인한다.
9. 실패 시 발생 시각과 동작을 기록하고 AndroidRuntime, NoClassDefFoundError,
   NoSuchMethodError, SecurityException, ActivityNotFoundException, UnsatisfiedLinkError,
   avc: denied 및 ScanDocTool/OseeSdkHandler_/SettingsActivity_ 로그를 확인한다.
   계정 토큰·문서 내용·개인 파일 경로는 공유 전 가린다.

이번 작업에서는 기기 설치·전체 ROM 빌드·13T 실기기 실행을 수행하지 않았다.
후속 검토 이후 사용자 결정으로 AI 기능을 비활성화했으며 별도 번역기는 추가하지 않는다.
