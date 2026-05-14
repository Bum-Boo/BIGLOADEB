# BIGLOADEB

> Account-first Instagram post collection and local media management for Windows.

[Overview](../../README.md) | [English](README.en.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md)

BIGLOADEB는 여러 비즈니스/클라이언트 Instagram 공개 계정의 게시물을 수집하고 로컬에서 관리하는 Windows 전용 데스크톱 앱입니다.

비개발자도 계정 목록에서 시작해 피드를 확인하고, 다운로드된 게시물을 로컬 폴더 구조로 관리할 수 있도록 단순한 흐름에 맞춰져 있습니다.

### 주요 기능

- Instagram 공개 프로필 URL 직접 등록
- 계정별 피드 확인과 통합 피드 확인
- 이미지/동영상 게시물 필터링
- 게시물 상세 화면에서 캐러셀, 캡션 복사, 미디어 미리보기 확인
- 계정별 로컬 폴더로 게시물 다운로드
- SQLite로 다운로드 기록 관리
- 다운로드된 게시물의 재다운로드/삭제 관리
- 설정에서 언어와 테마 전환

### 실행

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ig_post_controller
```

### 데모 흐름

1. `dist\IGPostController.exe`를 실행합니다.
2. 왼쪽 메뉴에서 `계정`을 선택합니다.
3. 등록된 계정 행의 `피드` 버튼을 누릅니다.
4. 왼쪽 메뉴에서 `다운로드된 게시물`을 선택합니다.
5. 저장된 게시물 카드에서 썸네일, 캡션, 다시 다운로드, 삭제 동작을 확인합니다.

데모 스크린샷은 위 English 섹션의 같은 화면 흐름을 참고하면 됩니다.
