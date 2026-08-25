# 자율 세션 자가 재시작 워치독 (2026-08-24 사용자 지시로 구축)
#
# 동작: 2시간마다 작업 스케줄러가 이 스크립트를 실행한다.
#  1) claude 프로세스가 이미 떠 있으면 (= 세션 살아있음) 아무것도 안 함.
#  2) 없으면 (= 토큰 소진/크래시로 정지) 헤드리스로 세션을 재개한다.
#     토큰 한도가 아직 안 풀렸으면 claude 가 에러로 끝나고, 다음 주기에 재시도된다.
#     → 한도 리셋 시점에 자동 부활.
# 로그: C:\Users\a3162\thesis\tools\auto_resume.log
# 해제: schtasks /delete /tn thesis_auto_resume /f

$log = "C:\Users\a3162\thesis\tools\auto_resume.log"
function Log($m) { "$(Get-Date -Format 'MM-dd HH:mm:ss') $m" | Add-Content -Encoding utf8 $log }

# 1) 살아있는 claude 세션이 있으면 개입 금지 (이중 작업 방지)
$alive = Get-Process | Where-Object { $_.ProcessName -match '^claude' } | Measure-Object
if ($alive.Count -gt 0) { Log "세션 살아있음($($alive.Count)) — 개입 안 함"; exit 0 }

# 2) claude CLI 경로 탐색
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($null -eq $claude) {
    $cand = Get-ChildItem "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -eq $cand) { Log "claude CLI 를 찾지 못함"; exit 1 }
    $claude = $cand.FullName
} else { $claude = $claude.Source }

# 3) 헤드리스 재개 — 최근 대화 이어서, STATUS 기반으로 자율 계속
Log "세션 없음 → 재개 시도 ($claude)"
Set-Location "C:\Users\a3162\thesis"
$prompt = "세션이 중단됐다가 워치독으로 재시작됐다. git pull 후 STATUS.md 전체(특히 '자율 운행 재개 지침')와 최근 커밋 로그를 읽고, 진행 중이던 자율 개선 작업을 이어가라. 완료 게이트(대량 생성=사용자 육안 합격)는 그대로 지켜라."
& $claude --continue --permission-mode auto -p $prompt >> $log 2>&1
Log "재개 프로세스 종료 (exit=$LASTEXITCODE)"
