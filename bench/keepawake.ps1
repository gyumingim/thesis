# 배치 무인 실행 중 절전 진입 방지. run_all.sh 가 수명 관리(trap EXIT kill).
$sig = '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
$k = Add-Type -MemberDefinition $sig -Name KA -Namespace W -PassThru
# 0x80000001 = ES_CONTINUOUS | ES_SYSTEM_REQUIRED (모니터는 꺼져도 됨)
while ($true) { [void]$k::SetThreadExecutionState(2147483649); Start-Sleep 50 }
