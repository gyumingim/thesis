"""MetaDrive를 GT 관측 + Gymnasium VectorEnv 로 쓰기 위한 최소 래퍼.

두 가지 문제를 해결한다.

1. **광선 제거.** MetaDrive의 `LidarStateObservation.lidar_observe()` 는 GT 주변차 정보를
   `num_lasers > 0` 조건 안에 넣어두었다. 따라서 `num_lasers=0` 으로 두면 광선과 GT가 함께 꺼진다.
   `GTStateObservation` 이 그 게이트를 우회해, 광선을 한 개도 쏘지 않고 GT만 얻는다.
   주변차 탐지는 원래도 broad-phase `contactTest`(`Lidar.get_surrounding_objects`)라 광선과 무관하다.

2. **reset(options=) 흡수.** MetaDrive 0.4.3 의 `BaseEnv.reset(self, seed=None)` 은 `options` 를
   받지 않는데 gymnasium 1.2.3 의 `AsyncVectorEnv` 가 이를 넘겨 TypeError 가 난다.

관측 = ego 9 + navi 10 + 주변차 num_others x 4 = 51 (num_others=8 기준)
"""
import gymnasium as gym
import numpy as np
from metadrive.envs.metadrive_env import MetaDriveEnv
from metadrive.obs.state_obs import LidarStateObservation

NUM_OTHERS = 8      # 사용자 결정 2026-08-18


class GTStateObservation(LidarStateObservation):
    """광선 없이 GT 주변차 정보만 사용하는 관측."""

    @property
    def observation_space(self):
        shape = list(self.state_obs.observation_space.shape)
        lidar_cfg = self.config["vehicle_config"]["lidar"]
        shape[0] += lidar_cfg["num_others"] * 4
        if lidar_cfg["add_others_navi"]:
            shape[0] += lidar_cfg["num_others"] * 4
        return gym.spaces.Box(-0.0, 1.0, shape=tuple(shape), dtype=np.float32)

    def lidar_observe(self, vehicle):
        cfg = vehicle.config["lidar"]
        if cfg["num_others"] <= 0:
            return []
        lidar = self.engine.get_sensor("lidar")
        # 광선을 쏘지 않고 broad-phase 로만 주변 객체를 얻는다.
        objs = lidar.get_surrounding_objects(vehicle, radius=cfg["distance"])
        self.detected_objects = objs
        self.cloud_points = None
        return lidar.get_surrounding_vehicles_info(
            vehicle, objs, cfg["distance"], cfg["num_others"], cfg["add_others_navi"]
        )


def base_config(seed=0, num_others=NUM_OTHERS, density=0.1):
    return dict(
        use_render=False, image_observation=False,
        map="X", traffic_density=density, horizon=1000,
        num_scenarios=1, start_seed=seed, log_level=50,
        agent_observation=GTStateObservation,
        vehicle_config=dict(lidar=dict(num_lasers=0, distance=50, num_others=num_others)),
    )


class MetaDriveGT(gym.Env):
    """GT 관측 MetaDrive. gymnasium VectorEnv 호환."""

    def __init__(self, seed=0, num_others=NUM_OTHERS, density=0.1):
        self._env = MetaDriveEnv(base_config(seed, num_others, density))
        self.observation_space = self._env.observation_space
        self.action_space = self._env.action_space

    def reset(self, *, seed=None, options=None):
        return self._env.reset(seed=seed)

    def step(self, action):
        return self._env.step(action)

    def close(self):
        self._env.close()
