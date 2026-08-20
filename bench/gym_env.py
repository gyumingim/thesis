"""IntersectionEnv 의 Gymnasium VectorEnv 어댑터 — CleanRL 연결용.

주의(자동 리셋 의미론): 커널이 same-step 리셋을 한다. 즉 done 이 True 인 스텝의
obs 는 이미 '다음 에피소드의 첫 관측'이다. gymnasium 1.x 표준(NextStep)과 다르므로
CleanRL 의 GAE 부트스트랩 연결 시 이 차이를 명시적으로 처리해야 한다 (STATUS.md 참조).
"""
import gymnasium as gym
import numpy as np
from gymnasium.vector.utils import batch_space

import spec
from env_numba import IntersectionEnv


class IntersectionVectorEnv(gym.vector.VectorEnv):
    metadata = {}

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
