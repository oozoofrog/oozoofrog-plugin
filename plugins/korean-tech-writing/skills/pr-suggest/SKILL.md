---
name: pr-suggest
description: Use when reviewing someone else's GitHub pull request and an improvement is best shown as code. Edit copies of the files outside the repository, turn the edits into suggestion comments that are checked to reproduce them exactly, and post one COMMENT review with a Korean body that leads with the reason. 남의 PR에 개선안을 suggestion 묶음 리뷰로 올릴 때 사용한다. "suggestion으로 제안해줘", "제안 리뷰 올려줘", "개선안을 코드로 남겨줘"에 쓴다. 내 PR을 직접 고치는 작업과 의견만 필요한 리뷰에는 쓰지 않는다.
---

# PR 개선안을 suggestion으로 올리기

결과는 PR 리뷰 1건이다. 리뷰 종류는 comment이고, 본문 1개와 suggestion 코멘트 여러 개로 이루어진다. PR 작성자는 Files changed 탭에서 suggestion을 batch에 담아 한 커밋으로 반영한다.

## 지킬 것

- 저장소 작업 트리, 현재 브랜치, PR 브랜치를 바꾸지 않는다. 작업 파일은 저장소 밖 임시 폴더(세션 scratchpad 등)에 둔다. 아래에서는 이 폴더를 `<work>`라고 부른다.
- 리뷰 종류는 comment만 쓴다. approve와 request-changes는 쓰지 않는다. 승인 여부는 사람이 정한다.
- GitHub에 무언가 쓰기 전에는 사용자의 동의를 받는다. 새 리뷰와 기존 리뷰 수정이 모두 해당한다. 이번 요청에 "올려줘"가 들어 있었다면 다시 묻지 않는다.
- 사용자에게 고를 것을 물을 때는 객관식으로 묻고, 권장안을 첫 번째에 둔다.
- @멘션은 실제 GitHub 로그인에만 쓴다. 누구를 멘션할지는 올리기 전 확인 질문에 넣는다.
- 본문의 확인 수준에는 실행한 것과 실행하지 않은 것을 모두 적는다.

## 준비물

- PR이 열린 저장소의 로컬 clone. `suggest.py`가 원본과 PR diff를 git 객체에서 읽는다.
- PR 도구. T3 Code에서는 `pull_request_read`와 `pull_request_review`를 쓴다. 이 도구가 없으면 GitHub CLI(`gh`)를 쓴다. PR이 GitHub Enterprise에 있으면 모든 `gh` 명령에 `GH_HOST=<호스트>`를 붙인다.
- 아래 `<remote>`는 PR이 열린 저장소를 가리키는 remote다. 보통 `origin`이고, 포크를 clone했다면 `upstream`이다.

## 순서

1. **PR의 두 끝을 고정한다.** base 커밋, head 커밋, 바뀐 파일 목록을 읽는다.
   - T3: `pull_request_read`에 `repository`와 `number`를 넘긴다.
   - gh: `gh pr view <N> -R <owner>/<repo> --json title,body,state,baseRefName,baseRefOid,headRefOid,files`
   - `baseRefOid`를 `<BASE>`로, `headRefOid`를 `<SHA>`로 적어 둔다. 지금 base 브랜치 끝을 `<BASE>`로 쓰면 안 된다. 이미 머지된 PR에서는 diff가 비어서 모든 suggestion이 거부된다.
   - 두 커밋을 로컬로 받는다. 포크에서 온 PR도 `pull/<N>/head`로 받는다.
     ```bash
     git fetch <remote> <baseRefName> pull/<N>/head
     git cat-file -e <BASE>^{commit} && git cat-file -e <SHA>^{commit}
     ```
   - PR이 이미 머지되었거나 닫혔으면 suggestion을 PR에서 커밋할 수 없다. 사용자에게 알리고, 계속하면 본문에 후속 PR이 필요하다고 적는다.
2. **읽는다.**
   - 바뀐 코드를 `git show <SHA>:<path>`로 읽는다. 사람이 직접 쓰지 않은 생성 파일(문자열 카탈로그, lock 파일 등)은 제안 대상에서 뺀다. 바뀐 코드의 호출자와 피호출자도 읽는다.
   - 이미 달린 리뷰와 코멘트를 읽는다. T3에서는 `pull_request_read`의 `include`에 `threads`와 `comments`를, `includeResolved`에 `true`를 넘긴다. gh에서는 다음 명령을 쓴다.
     ```bash
     gh api repos/<owner>/<repo>/pulls/<N>/reviews --paginate
     gh api repos/<owner>/<repo>/pulls/<N>/comments --paginate
     gh api repos/<owner>/<repo>/issues/<N>/comments --paginate
     ```
   - 이미 나온 의견과 겹치는 제안은 빼고, 그 의견이 head에서 해결됐는지 표시한다.
   - 승인 리뷰의 시각과 그 뒤 커밋을 비교한다. 승인 뒤에 동작을 바꾸는 커밋이 있으면, 그 승인자를 본문 끝 재확인 문장의 대상으로 삼는다.
3. **제안할 것을 고른다.** 제안마다 근거가 되는 구체적인 입력이나 상황을 코드에서 찾는다. 그런 상황을 찾지 못한 제안은 버린다. 남은 제안과 기존 리뷰 상태를 사용자에게 보여 주고, 코드로 만들지 묻는다.
4. **수정본을 만든다.**
   1. 고칠 파일을 head에서 복사한다: `mkdir -p <work>/proposed/<dir> && git show <SHA>:<path> > <work>/proposed/<path>`.
   2. `<work>/proposed/` 안의 사본만 고친다.
   3. 바꾼 심볼이 쓰이는 곳을 찾는다: `git grep -n <symbol> <SHA>`. 테스트도 포함한다.
   4. suggestion은 PR diff에 보이는 줄에만 달 수 있다. PR이 건드리지 않은 파일이나 줄까지 바꿔야 하면, 그 부분은 본문에 글로 적는다. 새 파일 추가와 파일 삭제도 본문에 적는다.
5. **suggestion을 만들고 검사한다.**
   ```bash
   python3 -I <이 스킬 폴더>/scripts/suggest.py --repo <clone> --base <BASE> --head <SHA> \
     --proposed <work>/proposed --body <work>/body.md --diff-out <work>/change.diff \
     --format t3 --repository <owner>/<repo> --number <N> > <work>/review.json
   ```
   - gh로 올릴 때는 `--format t3 --repository … --number …` 대신 `--format gh`를 쓴다. 두 형식은 필드 이름이 달라서 섞어 쓸 수 없다.
   - 스크립트는 `<SHA>`의 원본에 suggestion을 다시 적용해 보고, 결과가 수정본과 다르면 멈춘다.
   - 다음 경우에도 멈춘다: 범위가 PR diff의 한 덩어리 안에 들어가지 않는 경우, 범위가 서로 겹치는 경우, CR 줄바꿈이 있는 경우, 마지막 줄바꿈만 바뀐 경우, 새 파일인 경우. GitHub는 코멘트 하나만 잘못돼도 리뷰 전체를 거부한다.
   - 범위 오류가 나면 `--gap`을 1로 낮추거나 그 변경을 본문으로 옮긴다.
   - T3 형식은 코멘트를 50개까지만 받는다.
   - stderr에는 코멘트마다 `path:start-end`가 나오고, 마지막 줄에 파일 수, suggestion 수, 추가·삭제 줄 수가 나온다.
   - 특정 줄에만 해당하는 근거는 `notes.json`에 `{"<path>:<start>-<end>": "1~2문장"}`으로 적고 `--notes`로 넘긴다.
   - `change.diff`와 변경 범위를 사용자에게 보여 준다.
6. **본문을 쓴다.** [references/review-body.md](references/review-body.md)의 틀을 쓴다. 초안을 사용자에게 보여 준다.
7. **올린다.**
   1. head SHA를 다시 읽는다. 1단계 값과 다르면 4단계로 돌아간다.
   2. T3: `review.json`의 필드를 `pull_request_review`에 그대로 넘긴다. 이 파일에는 `repository`, `number`, `verdict`, `expectedHeadSha`, `body`, `comments`가 들어 있다.
   3. gh:
      ```bash
      gh api -X POST repos/<owner>/<repo>/pulls/<N>/reviews --input <work>/review.json --jq '{id, html_url}'
      ```
8. **붙은 위치를 대조한다.** 올라간 코멘트의 위치를 5단계 stderr 목록과 비교한다.
   - T3: `pull_request_read`로 `threads`를 읽는다.
   - gh:
     ```bash
     gh api repos/<owner>/<repo>/pulls/<N>/comments --paginate \
       --jq '.[] | select(.pull_request_review_id==<review id>) | "\(.path):\(.original_start_line // .original_line)-\(.original_line)"'
     ```

## 올린 리뷰를 고칠 때

- 리뷰 본문: `gh api -X PUT repos/<owner>/<repo>/pulls/<N>/reviews/<review id> -F body=@<file>`
- 인라인 코멘트: `gh api -X PATCH repos/<owner>/<repo>/pulls/comments/<comment id> -F body=@<file>`

인라인 코멘트를 고칠 때는 새 본문에 suggestion 코드 블록을 다시 넣는다. GitHub는 코멘트 본문 안의 블록으로 suggestion을 만들기 때문이다.
