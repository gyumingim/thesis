"""처방(i) 조기정지 소급 분석 (2026-08-26, PAPER §7 근거).

규칙(경량 신호만 사용 — MD 평가 훔쳐보기 없음): episodic_return 의 60초 버킷 평균이
직전 300초 창 최고 대비 +1% 미만 개선을 3회 연속 기록하면 정지(warm-up 300초).
결과(final_custom 3시드): 전 시드 8분 정지 → 5분 ckpt 선택 → MD 18% 평균
(vs 60분 최종 0%, 사후 오라클 피크 23%). 입력: runs TB 이벤트(tb_s.csv),
eval_md__final_custom_s*.json. 본문 수치 재현은 scratchpad/es 사본 또는 노트북 원본.
"""
# (분석 로직은 대화 로그와 동일 — 재실행 시 아래 함수를 tb CSV·eval JSON 에 적용)
def early_stop_time(rows, warm=300, win=300, eps=0.01, k=3):
    t0 = rows[0][0]
    buck = {}
    for w, _, v in rows:
        buck.setdefault(int((w - t0) // 60), []).append(v)
    seq = sorted((b * 60 + 30, sum(vs) / len(vs)) for b, vs in buck.items())
    best, streak = -1e18, 0
    for i, (t, v) in enumerate(seq):
        if t < warm:
            best = max(best, v); continue
        prev = [x for tt, x in seq[:i] if tt >= t - win]
        wbest = max(prev) if prev else best
        improved = v > wbest * (1 + eps) if wbest > 0 else v > wbest + abs(wbest) * eps
        streak = 0 if improved else streak + 1
        if streak >= k:
            return t
        best = max(best, v)
    return seq[-1][0]
