"""IntersectionEnv 의 Gymnasium VectorEnv 어댑터 — CleanRL 연결용.

리셋 의미론 = gymnasium 표준 NEXT_STEP: done 스텝은 마지막 관측을 반환하고,
그 다음 step() 호출이 행동을 무시하며 새 에피소드의 첫 관측(보상 0)을 반환한다.
gymnasium 1.2.3 의 stateful 벡터 래퍼(NormalizeObservation 등)가 SAME_STEP 을
지원하지 않아(vector_env.py:542 assert) 커널을 NEXT_STEP 으로 맞췄다.
MetaDrive 쪽 AsyncVectorEnv 기본값과도 동일 → 양쪽 의미론 일치.
"""
import gymnasium as gym
import numpy as np
from gymnasium.vector import AutoresetMode
from gymnasium.vector.utils import batch_space

import spec
from env_numba import IntersectionEnv


class IntersectionVectorEnv(gym.vector.VectorEnv):
    # 벡터 래퍼(RecordEpisodeStatistics 등)가 이 태그로 리셋 의미론을 판별한다.
    metadata = {"autoreset_mode": AutoresetMode.NEXT_STEP}

    def __init__(self, num_envs, n_vehicles=16, seed=0):
        self._env = IntersectionEnv(num_envs, n_vehicles, seed)
        self.num_envs = num_envs
        self.single_observation_space = gym.spaces.Box(0.0, 1.0, (spec.OBS_DIM,), np.float32)
        self.single_action_space = gym.spaces.Box(-1.0, 1.0, (2,), np.float32)
        self.observation_space = batch_space(self.single_observation_space, num_envs)
        self.action_space = batch_space(self.single_action_space, num_envs)

    def reset(self, *, seed=None, options=None):
        return self._env.reset(), {}

    def step(self, actions):
        obs, r, term, trunc, flags = self._env.step(actions)
        return obs, r, term, trunc, {"outcome": flags.copy()}

    def close(self):
        pass
