# 기존 보관함과 CLI 연결

Obsidian CLI나 내부 링크를 사용할 때 읽는다. [공식 CLI](https://obsidian.md/help/cli)를 기준으로 설치된 `obsidian help`의 명령을 확인한다. 실행 중 앱에 연결할 수 없거나 CLI가 꺼져 있으면 파일 검증으로 진행하고 앱 내부 링크 해석은 미확인으로 남긴다. 기록 요청만으로 CLI 활성화·관리자 등록·플러그인/MCP 서버·API 키를 추가하지 않는다.

- CLI 대상은 `obsidian vault="보관함 이름 또는 ID" read path="프로젝트/정확한 노트.md"`처럼 vault를 첫 인수에, 보관함 기준 경로를 `path=`에 둔다. `file=`이나 활성 노트 기본값은 동명 파일에 모호할 수 있다. 프로젝트 이름만으로 대상을 고르지 말고 기존 노트와 실제 저장소 경로를 대조한다.
- help에 있는 `read`, `backlinks`, `unresolved`부터 읽기 전용으로 사용한다. 앱 reload/restart, eval, 플러그인 설치는 일반 기록 검증에 필요하지 않다. 파일 존재 검사는 앱 metadata cache의 실제 링크 해석을 증명하지 않는다.
- 내부 위키 링크는 `[[폴더/노트#절|표시 이름]]`, 블록은 `[[폴더/노트#^block-id]]`로 구분한다. 동명 파일은 폴더 경로를 쓰고 절·블록의 실제 존재를 확인한다. 기존 frontmatter·사용자 문장·내부/외부 링크 형식을 일괄 재작성하지 않는다.
- 일부 절을 갱신할 때 읽은 원문과 유일한 예상 절을 기준으로 변경안을 만든다. 쓰기 직전 파일을 다시 읽고 원문과 다르면 재검토한다. 중복 marker나 예상 본문 불일치에는 쓰지 않는다. 저장 후 재읽어 변경 절·주변 사용자 문장·링크를 확인한다. 같은 변경 재실행은 중복 추가 없이 같은 결과를 유지한다. 동시 편집과 파일 교체 사이의 짧은 race를 완전히 막았다고 주장하지 않는다.

[kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)의 CLI·Markdown 지침에서 필요한 문법만 참고했다. 전체 스킬/실행 스크립트를 설치하지 않는다. [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api)의 MCP는 별도 서버·인증 구성이므로 기존 파일/CLI 기록과 구분한다.
