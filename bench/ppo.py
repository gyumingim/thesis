"""CleanRL ppo_continuous_action.py 의 최소 수정판 — 두 시뮬에 동일 적용.

원본: vwxyzjn/cleanrl@fe8d8a03c41a7ef5b523e2e354bd01c363e786bb (cleanrl_ppo_commit.txt)
알고리즘 본체(GAE·업데이트 루프·네트워크)는 원본 그대로다. 수정은 3곳뿐:

1. env 생성: gym.make 기반 SyncVectorEnv → make_vector_env(sim=...) 로 교체.
   - sim="custom":   IntersectionVectorEnv (사전 벡터화, in-kernel NEXT_STEP 리셋)
   - sim="metadrive": AsyncVectorEnv(MetaDriveGT) — 기본 NEXT_STEP
   두 갈래 모두 **동일한 벡터 래퍼 스택** (원본의 per-env 래퍼와 동일 구성):
   RecordEpisodeStatistics → ClipAction → NormalizeObservation → clip(obs,±10)
   → NormalizeReward(gamma) → clip(r,±10)
2. 에피소드 로깅: 원본의 "final_info"(구 gymnasium) → 1.2.3 벡터 API 의
   infos["episode"] + infos["_episode"] 마스크로 교체.
3. Args 에 sim / n_vehicles / density 추가. 하이퍼파라미터는 원본 기본값 그대로.
4. wall-clock 실험 지원: --time-budget-s (경과 시 학습 중단), --checkpoint-every-s
   (주기적으로 agent 가중치 + NormalizeObservation 통계(obs_rms)를 저장 — 교차 평가 시
   이 통계를 동결 적용해야 정책이 학습 때와 같은 입력 분포를 받는다).
   알고리즘 로직(GAE·업데이트)은 여전히 무수정.

리셋 의미론: 양쪽 모두 gymnasium 표준 NEXT_STEP (stateful 벡터 래퍼가 SAME_STEP 미지원).
truncation 부트스트랩은 원본 CleanRL 과 동일하게 생략 — 두 시뮬에 같은 처리라 비교는 공정.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# docs and experiment results can be found at https://docs.cleanrl.dev/rl-algorithms/ppo/#ppo_continuous_actionpy
import os
import random
import time
from dataclasses import dataclass

import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import tyro
from torch.distributions.normal import Normal
from torch.utils.tensorboard import SummaryWriter


@dataclass
class Args:
    exp_name: str = os.path.basename(__file__)[: -len(".py")]
    """the name of this experiment"""
    seed: int = 1
    """seed of the experiment"""
    torch_deterministic: bool = True
    """if toggled, `torch.backends.cudnn.deterministic=False`"""
    cuda: bool = True
    """if toggled, cuda will be enabled by default"""
    track: bool = False
    """if toggled, this experiment will be tracked with Weights and Biases"""
    wandb_project_name: str = "cleanRL"
    """the wandb's project name"""
    wandb_entity: str = None
    """the entity (team) of wandb's project"""
    capture_video: bool = False
    """whether to capture videos of the agent performances (check out `videos` folder)"""
    save_model: bool = False
    """whether to save model into the `runs/{run_name}` folder"""
    upload_model: bool = False
    """whether to upload the saved model to huggingface"""
    hf_entity: str = ""
    """the user or org name of the model repository from the Hugging Face Hub"""

    # Algorithm specific arguments
    env_id: str = "Intersection"
    """the id of the environment (로깅용 라벨)"""
    sim: str = "custom"
    """어느 시뮬레이터로 학습할지: "custom" | "metadrive" (수정 3)"""
    n_vehicles: int = 16
    """custom 시뮬의 NPC 수"""
    density: float = 0.1
    """metadrive 의 traffic_density"""
    time_budget_s: float = 0.0
    """0 보다 크면 wall-clock 이 이 값(초)을 넘는 순간 학습 종료 (수정 4)"""
    checkpoint_every_s: float = 0.0
    """0 보다 크면 이 주기(초)로 체크포인트 저장 (수정 4)"""
    total_timesteps: int = 1000000
    """total timesteps of the experiments"""
    learning_rate: float = 3e-4
    """the learning rate of the optimizer"""
    num_envs: int = 1
    """the number of parallel game environments"""
    num_steps: int = 2048
    """the number of steps to run in each environment per policy rollout"""
    anneal_lr: bool = True
    """Toggle learning rate annealing for policy and value networks"""
    gamma: float = 0.99
    """the discount factor gamma"""
    gae_lambda: float = 0.95
    """the lambda for the general advantage estimation"""
    num_minibatches: int = 32
    """the number of mini-batches"""
    update_epochs: int = 10
    """the K epochs to update the policy"""
    norm_adv: bool = True
    """Toggles advantages normalization"""
    clip_coef: float = 0.2
    """the surrogate clipping coefficient"""
    clip_vloss: bool = True
    """Toggles whether or not to use a clipped loss for the value function, as per the paper."""
    ent_coef: float = 0.0
    """coefficient of the entropy"""
    vf_coef: float = 0.5
    """coefficient of the value function"""
    max_grad_norm: float = 0.5
    """the maximum norm for the gradient clipping"""
    target_kl: float = None
    """the target KL divergence threshold"""

    # to be filled in runtime
    batch_size: int = 0
    """the batch size (computed in runtime)"""
    minibatch_size: int = 0
    """the mini-batch size (computed in runtime)"""
    num_iterations: int = 0
    """the number of iterations (computed in runtime)"""


def make_vector_env(sim, num_envs, seed, gamma, n_vehicles, density):
    """수정 1: 두 시뮬 공용 벡터 환경 팩토리. 래퍼 스택은 원본 make_env 와 동일 구성."""
    import gymnasium.wrappers.vector as wv
    from gymnasium.vector import AsyncVectorEnv

    if sim == "custom":
        from gym_env import IntersectionVectorEnv
        envs = IntersectionVectorEnv(num_envs, n_vehicles=n_vehicles, seed=seed)
    elif sim == "metadrive":
        from md_env import MetaDriveGT
        def mk(i):
            return lambda: MetaDriveGT(seed=seed + i, density=density)
        envs = AsyncVectorEnv([mk(i) for i in range(num_envs)])  # 기본 NEXT_STEP
    else:
        raise ValueError(sim)

    envs = wv.RecordEpisodeStatistics(envs)
    envs = wv.ClipAction(envs)
    envs = wv.NormalizeObservation(envs)
    envs = wv.TransformObservation(envs, lambda obs: np.clip(obs, -10, 10))
    envs = wv.NormalizeReward(envs, gamma=gamma)
    envs = wv.TransformReward(envs, lambda reward: np.clip(reward, -10, 10))
    return envs


def find_obs_rms(envs):
    """래퍼 체인에서 NormalizeObservation 의 running 통계를 찾는다 (수정 4)."""
    import gymnasium.wrappers.vector as wv
    e = envs
    while e is not None:
        if isinstance(e, wv.NormalizeObservation):
            return e.obs_rms
        e = getattr(e, "env", None)
    return None


def save_checkpoint(path, agent, envs, global_step, elapsed_s):
    """agent 가중치 + obs 정규화 통계. 교차 평가는 이 통계를 동결 적용해야 한다 (수정 4)."""
    rms = find_obs_rms(envs)
    torch.save(
        dict(model=agent.state_dict(), global_step=global_step, elapsed_s=elapsed_s,
             obs_mean=None if rms is None else rms.mean.copy(),
             obs_var=None if rms is None else rms.var.copy(),
             obs_count=None if rms is None else float(rms.count)),
        path,
    )


def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    torch.nn.init.orthogonal_(layer.weight, std)
    torch.nn.init.constant_(layer.bias, bias_const)
    return layer


class Agent(nn.Module):
    def __init__(self, envs):
        super().__init__()
        self.critic = nn.Sequential(
            layer_init(nn.Linear(np.array(envs.single_observation_space.shape).prod(), 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, 1), std=1.0),
        )
        self.actor_mean = nn.Sequential(
            layer_init(nn.Linear(np.array(envs.single_observation_space.shape).prod(), 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, np.prod(envs.single_action_space.shape)), std=0.01),
        )
        self.actor_logstd = nn.Parameter(torch.zeros(1, np.prod(envs.single_action_space.shape)))

    def get_value(self, x):
        return self.critic(x)

    def get_action_and_value(self, x, action=None):
        action_mean = self.actor_mean(x)
        action_logstd = self.actor_logstd.expand_as(action_mean)
        action_std = torch.exp(action_logstd)
        probs = Normal(action_mean, action_std)
        if action is None:
            action = probs.sample()
        return action, probs.log_prob(action).sum(1), probs.entropy().sum(1), self.critic(x)


if __name__ == "__main__":
    args = tyro.cli(Args)
    args.batch_size = int(args.num_envs * args.num_steps)
    args.minibatch_size = int(args.batch_size // args.num_minibatches)
    args.num_iterations = args.total_timesteps // args.batch_size
    run_name = f"{args.env_id}__{args.exp_name}__{args.seed}__{int(time.time())}"
    if args.track:
        import wandb

        wandb.init(
            project=args.wandb_project_name,
            entity=args.wandb_entity,
            sync_tensorboard=True,
            config=vars(args),
            name=run_name,
            monitor_gym=True,
            save_code=True,
        )
    writer = SummaryWriter(f"runs/{run_name}")
    writer.add_text(
        "hyperparameters",
        "|param|value|\n|-|-|\n%s" % ("\n".join([f"|{key}|{value}|" for key, value in vars(args).items()])),
    )

    # TRY NOT TO MODIFY: seeding
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = args.torch_deterministic

    device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    # env setup
    envs = make_vector_env(args.sim, args.num_envs, args.seed, args.gamma,
                           args.n_vehicles, args.density)
    assert isinstance(envs.single_action_space, gym.spaces.Box), "only continuous action space is supported"

    agent = Agent(envs).to(device)
    optimizer = optim.Adam(agent.parameters(), lr=args.learning_rate, eps=1e-5)

    # ALGO Logic: Storage setup
    obs = torch.zeros((args.num_steps, args.num_envs) + envs.single_observation_space.shape).to(device)
    actions = torch.zeros((args.num_steps, args.num_envs) + envs.single_action_space.shape).to(device)
    logprobs = torch.zeros((args.num_steps, args.num_envs)).to(device)
    rewards = torch.zeros((args.num_steps, args.num_envs)).to(device)
    dones = torch.zeros((args.num_steps, args.num_envs)).to(device)
    values = torch.zeros((args.num_steps, args.num_envs)).to(device)

    # TRY NOT TO MODIFY: start the game
    global_step = 0
    start_time = time.time()
    next_obs, _ = envs.reset(seed=args.seed)
    next_obs = torch.Tensor(next_obs).to(device)
    next_done = torch.zeros(args.num_envs).to(device)

    ckpt_dir = f"runs/{run_name}/ckpt"
    os.makedirs(ckpt_dir, exist_ok=True)
    next_ckpt_at = args.checkpoint_every_s if args.checkpoint_every_s > 0 else float("inf")

    for iteration in range(1, args.num_iterations + 1):
        elapsed = time.time() - start_time                       # 수정 4
        if args.time_budget_s > 0 and elapsed > args.time_budget_s:
            print(f"time budget reached: {elapsed:.0f}s @ global_step={global_step}")
            break
        if elapsed >= next_ckpt_at:
            save_checkpoint(f"{ckpt_dir}/t{int(elapsed):06d}.pt", agent, envs, global_step, elapsed)
            next_ckpt_at += args.checkpoint_every_s

        # Annealing the rate if instructed to do so.
        if args.anneal_lr:
            frac = 1.0 - (iteration - 1.0) / args.num_iterations
            lrnow = frac * args.learning_rate
            optimizer.param_groups[0]["lr"] = lrnow

        for step in range(0, args.num_steps):
            global_step += args.num_envs
            obs[step] = next_obs
            dones[step] = next_done

            # ALGO LOGIC: action logic
            with torch.no_grad():
                action, logprob, _, value = agent.get_action_and_value(next_obs)
                values[step] = value.flatten()
            actions[step] = action
            logprobs[step] = logprob

            # TRY NOT TO MODIFY: execute the game and log data.
            next_obs, reward, terminations, truncations, infos = envs.step(action.cpu().numpy())
            next_done = np.logical_or(terminations, truncations)
            rewards[step] = torch.tensor(reward).to(device).view(-1)
            next_obs, next_done = torch.Tensor(next_obs).to(device), torch.Tensor(next_done).to(device)

            if "episode" in infos:  # 수정 2: gymnasium 1.x 벡터 API
                m = infos["_episode"]
                if m.any():
                    r_mean = float(infos["episode"]["r"][m].mean())
                    l_mean = float(infos["episode"]["l"][m].mean())
                    writer.add_scalar("charts/episodic_return", r_mean, global_step)
                    writer.add_scalar("charts/episodic_length", l_mean, global_step)

        # bootstrap value if not done
        with torch.no_grad():
            next_value = agent.get_value(next_obs).reshape(1, -1)
            advantages = torch.zeros_like(rewards).to(device)
            lastgaelam = 0
            for t in reversed(range(args.num_steps)):
                if t == args.num_steps - 1:
                    nextnonterminal = 1.0 - next_done
                    nextvalues = next_value
                else:
                    nextnonterminal = 1.0 - dones[t + 1]
                    nextvalues = values[t + 1]
                delta = rewards[t] + args.gamma * nextvalues * nextnonterminal - values[t]
                advantages[t] = lastgaelam = delta + args.gamma * args.gae_lambda * nextnonterminal * lastgaelam
            returns = advantages + values

        # flatten the batch
        b_obs = obs.reshape((-1,) + envs.single_observation_space.shape)
        b_logprobs = logprobs.reshape(-1)
        b_actions = actions.reshape((-1,) + envs.single_action_space.shape)
        b_advantages = advantages.reshape(-1)
        b_returns = returns.reshape(-1)
        b_values = values.reshape(-1)

        # Optimizing the policy and value network
        b_inds = np.arange(args.batch_size)
        clipfracs = []
        for epoch in range(args.update_epochs):
            np.random.shuffle(b_inds)
            for start in range(0, args.batch_size, args.minibatch_size):
                end = start + args.minibatch_size
                mb_inds = b_inds[start:end]

                _, newlogprob, entropy, newvalue = agent.get_action_and_value(b_obs[mb_inds], b_actions[mb_inds])
                logratio = newlogprob - b_logprobs[mb_inds]
                ratio = logratio.exp()

                with torch.no_grad():
                    # calculate approx_kl http://joschu.net/blog/kl-approx.html
                    old_approx_kl = (-logratio).mean()
                    approx_kl = ((ratio - 1) - logratio).mean()
                    clipfracs += [((ratio - 1.0).abs() > args.clip_coef).float().mean().item()]

                mb_advantages = b_advantages[mb_inds]
                if args.norm_adv:
                    mb_advantages = (mb_advantages - mb_advantages.mean()) / (mb_advantages.std() + 1e-8)

                # Policy loss
                pg_loss1 = -mb_advantages * ratio
                pg_loss2 = -mb_advantages * torch.clamp(ratio, 1 - args.clip_coef, 1 + args.clip_coef)
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()

                # Value loss
                newvalue = newvalue.view(-1)
                if args.clip_vloss:
                    v_loss_unclipped = (newvalue - b_returns[mb_inds]) ** 2
                    v_clipped = b_values[mb_inds] + torch.clamp(
                        newvalue - b_values[mb_inds],
                        -args.clip_coef,
                        args.clip_coef,
                    )
                    v_loss_clipped = (v_clipped - b_returns[mb_inds]) ** 2
                    v_loss_max = torch.max(v_loss_unclipped, v_loss_clipped)
                    v_loss = 0.5 * v_loss_max.mean()
                else:
                    v_loss = 0.5 * ((newvalue - b_returns[mb_inds]) ** 2).mean()

                entropy_loss = entropy.mean()
                loss = pg_loss - args.ent_coef * entropy_loss + v_loss * args.vf_coef

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
                optimizer.step()

            if args.target_kl is not None and approx_kl > args.target_kl:
                break

        y_pred, y_true = b_values.cpu().numpy(), b_returns.cpu().numpy()
        var_y = np.var(y_true)
        explained_var = np.nan if var_y == 0 else 1 - np.var(y_true - y_pred) / var_y

        # TRY NOT TO MODIFY: record rewards for plotting purposes
        writer.add_scalar("charts/learning_rate", optimizer.param_groups[0]["lr"], global_step)
        writer.add_scalar("losses/value_loss", v_loss.item(), global_step)
        writer.add_scalar("losses/policy_loss", pg_loss.item(), global_step)
        writer.add_scalar("losses/entropy", entropy_loss.item(), global_step)
        writer.add_scalar("losses/old_approx_kl", old_approx_kl.item(), global_step)
        writer.add_scalar("losses/approx_kl", approx_kl.item(), global_step)
        writer.add_scalar("losses/clipfrac", np.mean(clipfracs), global_step)
        writer.add_scalar("losses/explained_variance", explained_var, global_step)
        print("SPS:", int(global_step / (time.time() - start_time)))
        writer.add_scalar("charts/SPS", int(global_step / (time.time() - start_time)), global_step)

    if args.save_model:
        model_path = f"runs/{run_name}/{args.exp_name}.cleanrl_model"
        torch.save(agent.state_dict(), model_path)
        print(f"model saved to {model_path}")
        from cleanrl_utils.evals.ppo_eval import evaluate

        episodic_returns = evaluate(
            model_path,
            make_env,
            args.env_id,
            eval_episodes=10,
            run_name=f"{run_name}-eval",
            Model=Agent,
            device=device,
            gamma=args.gamma,
        )
        for idx, episodic_return in enumerate(episodic_returns):
            writer.add_scalar("eval/episodic_return", episodic_return, idx)

        if args.upload_model:
            from cleanrl_utils.huggingface import push_to_hub

            repo_name = f"{args.env_id}-{args.exp_name}-seed{args.seed}"
            repo_id = f"{args.hf_entity}/{repo_name}" if args.hf_entity else repo_name
            push_to_hub(args, episodic_returns, repo_id, "PPO", f"runs/{run_name}", f"videos/{run_name}-eval")

    save_checkpoint(f"{ckpt_dir}/final.pt", agent, envs, global_step, time.time() - start_time)
    envs.close()
    writer.close()
