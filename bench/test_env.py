"""완성 환경 행동 검증 (재현 가능한 형태로 보존).

실행: env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/test_env.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from env_numba import IntersectionEnv

def t1_expert_arrives():
    env = IntersectionEnv(32, 1, seed=1)
    outcome = np.zeros(5, int); ep_ret = []; ret = np.zeros(32)
    for _ in range(400):
        o, r, tm, tr, fl = env.step(env.expert_action())
        ret += r
        for e in np.nonzero(tm | tr)[0]:
            outcome[fl[e]] += 1; ep_ret.append(ret[e]); ret[e] = 0
    assert outcome[3] > 0 and outcome[2] == 0, outcome
    assert 100 < np.mean(ep_ret) < 160, np.mean(ep_ret)
    print(f"T1 ✓ 전문가 도달 {outcome[3]}회, 이탈 0, 평균 리턴 {np.mean(ep_ret):.1f}")

def t2_out_of_road():
    env = IntersectionEnv(16, 1, seed=2)
    # 라운드2 도로폭 21m: 풀조향(선회지름 ~6.7m)은 도로 안에서 맴돌아 이탈하지 않는다.
    # 완만한 조향(0.2 → 선회지름 ~40m)이라야 코리도를 벗어난다.
    bad = np.tile(np.float32([0.2, 1]), (16, 1))
    seen = np.zeros(5, int)
    for _ in range(400):
        _, _, tm, tr, fl = env.step(bad)
        for e in np.nonzero(tm | tr)[0]: seen[fl[e]] += 1
    assert seen[2] > 0, seen
    print(f"T2 ✓ 풀조향 → 이탈 {seen[2]}회")

def t3_crash():
    env = IntersectionEnv(64, 16, seed=3)
    fwd = np.tile(np.float32([0, 1]), (64, 1))
    crash = 0
    for _ in range(500):
        _, _, _, _, fl = env.step(fwd)
        crash += int((fl == 1).sum())
    assert crash > 0
    print(f"T3 ✓ 직진 강행 → 충돌 {crash}회")

def t4_bounds():
    env = IntersectionEnv(128, 16, seed=4)
    rng = np.random.default_rng(0)
    for _ in range(500):
        o, r, *_ = env.step(rng.uniform(-1, 1, (128, 2)).astype(np.float32))
        assert not np.isnan(o).any() and o.min() >= 0 and o.max() <= 1
    print("T4 ✓ 무작위 500스텝 obs ∈ [0,1], NaN 없음")

def t5_sps():
    env = IntersectionEnv(1024, 16, seed=5)
    a = np.random.default_rng(0).uniform(-1, 1, (1024, 2)).astype(np.float32)
    for _ in range(30): env.step(a)
    t0 = time.perf_counter(); n = 0
    while time.perf_counter() - t0 < 2.0:
        for _ in range(10): env.step(a)
        n += 10
    sps = 1024 * n / (time.perf_counter() - t0)
    print(f"T5 완성 환경 SPS (E=1024,V=16): {sps:,.0f}")
    return sps

if __name__ == "__main__":
    t1_expert_arrives(); t2_out_of_road(); t3_crash(); t4_bounds(); t5_sps()
    print("전체 통과")
