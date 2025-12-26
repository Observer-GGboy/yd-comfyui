# 草稿引擎 vs 成片引擎使用指南

> 📌 **核心理念**：本地模型是"导演的草稿纸"，不是"替代商业 API"。
> 
> 草稿用于快速试错、验证镜头感觉；成片用于最终交付。

---

## 概念说明

### 🎬 Draft Engine（草稿引擎）

| 特性 | 说明 |
|------|------|
| **用途** | 镜头感觉、人物大体动作、场景运动、节奏验证 |
| **费用** | $0（使用本地 GPU） |
| **质量** | 预览级别，非终稿质量 |
| **速度** | 快速（取决于 GPU 算力） |
| **适合** | 初期创意验证、动作调整、节奏测试 |
| **不适合** | 人脸极致稳定、商业级一致性、可交付质量 |

**草稿 Provider 列表**：
- `local_turbodiffusion` - ⚡ 最快，~16GB VRAM
- `local_wan_i2v` - 🎬 更好的运动质量，~20GB VRAM
- `local_cogvideo_fast` - 🎯 CogVideoX 快速模式，~18GB VRAM

### 🎥 Production Engine（成片引擎）

| 特性 | 说明 |
|------|------|
| **用途** | 最终成片、可交付视频 |
| **费用** | 按 API 计费（$0.14 - $1.40/次） |
| **质量** | 商业级，适合最终交付 |
| **速度** | 较慢（云端排队 + 生成） |
| **适合** | 最终渲染、正式交付、高质量要求 |

**成片 Provider 列表**：
- `kling` - 可灵 AI，性价比高
- `minimax` - 海螺 AI，质量稳定
- `runway` - Runway Gen-3/4，高质量
- `vidu` - 清华 Vidu，国产优选

---

## 推荐工作流程

### 阶段一：创意验证（草稿阶段）

```
1. 设置 provider = local_turbodiffusion
2. 快速生成草稿视频
3. 验证：
   - 镜头角度是否合适？
   - 人物动作方向对吗？
   - 场景运动节奏如何？
   - 时长是否合理？
4. 调整 prompt/参数，重复 2-3
```

**此阶段成本：$0**

### 阶段二：正式生成（成片阶段）

```
1. 确认草稿效果满意
2. 切换 provider = kling（或其他成片 provider）
3. 设置 run_mode = prod_full
4. 生成最终成片
```

**此阶段成本：根据 provider 计费**

---

## 参数配置示例

### 草稿测试（推荐初始配置）

```python
# DMV_API_Image2Video 节点参数
provider: local_turbodiffusion   # 草稿 provider
model: auto
duration: 5                       # 5秒草稿
resolution: 720p
run_mode: prod_full              # 对草稿 provider 也是生成完整视频
cfg_scale: 0.7
enable_fallback: True            # 草稿 provider 之间可互相 fallback
```

### 环境检测

```python
# 验证本地环境是否就绪
provider: local_turbodiffusion
run_mode: test_connect           # 检查 CUDA、权重、显存
```

### 成片生成

```python
# 确认草稿满意后切换
provider: kling                  # 成片 provider
model: kling-v1-5
duration: 5
mode: pro                        # 专业模式
run_mode: prod_full
enable_fallback: False           # 成片不自动 fallback（避免意外换 provider）
```

---

## 重要设计原则

### ✅ 草稿失败不会烧钱

- 草稿 provider 失败时，**不会自动切换到商业 API**
- 避免"本地失败 → 自动调用 MiniMax → 意外扣费"的情况
- 草稿只会在其他草稿 provider 之间 fallback

### ✅ 成片稳定性不受影响

- 商业 API 的实现代码**完全不变**
- 草稿功能是**纯新增**，不修改任何现有逻辑
- MiniMax / Kling / Runway / Vidu 行为保持原样

### ✅ 成本明确可见

- 草稿 provider：`cost_usd = 0.0`
- 成片 provider：显示预估成本
- UI 中有明显提示区分草稿/成片

---

## 环境要求

### 草稿引擎 GPU 要求

| Provider | 最低 VRAM | 推荐 VRAM | 说明 |
|----------|-----------|-----------|------|
| `local_turbodiffusion` | 16 GB | 24 GB | 最快，适合快速迭代 |
| `local_wan_i2v` | 20 GB | 24 GB | 更好的运动质量 |
| `local_cogvideo_fast` | 18 GB | 24 GB | CogVideoX 快速模式 |

**推荐配置**：RTX 5090 (32GB) 或 RTX 4090 (24GB)

### 权重文件位置

将模型权重放置在：

```
ComfyUI/models/video_generation/
├── turbodiffusion/          # TurboDiffusion 权重
├── wan_i2v/                 # Wan I2V 权重
│   └── Wan2.1-I2V-14B-480P-Diffusers/
└── cogvideo/                # CogVideoX 权重
    └── CogVideoX-5b-I2V/
```

---

## test_connect 环境自检

草稿 provider 的 `test_connect` 模式会检查：

1. **CUDA 可用性**
   - CUDA 是否安装
   - GPU 是否被识别

2. **PyTorch 版本**
   - torch 版本号
   - CUDA 版本号

3. **显存检查**
   - 总显存是否满足最低要求
   - 当前可用显存

4. **权重文件**
   - 模型权重是否存在
   - 路径是否正确

**示例输出**：

```
TEST_CONNECT_OK | local_turbodiffusion ready | GPU: NVIDIA RTX 5090 | VRAM: 28.5/32.0GB
```

或失败时：

```
TEST_CONNECT_FAIL | Environment check failed: Insufficient VRAM: 12.0GB < 16GB minimum
```

---

## 草稿生成日志示例

```
[DRAFT] TurboDiffusion starting | task_id=turbo_a1b2c3d4e5f6
[DRAFT] Config: duration=5s, seed=123456789, cfg=0.7
[DRAFT] Loading model from: ComfyUI/models/video_generation/turbodiffusion
[DRAFT] TurboDiffusion complete | task_id=turbo_a1b2c3d4e5f6
[DRAFT] Performance: time=23.5s, vram_peak=18.2GB
[DRAFT] Output: ComfyUI/output/directormv_videos/draft_turbo_turbo_a1b2c3d4_20251226_143052.mp4
```

---

## 常见问题

### Q: 为什么草稿质量不如商业 API？

草稿引擎的设计目标是**速度和免费**，不是质量。它用于：
- 快速验证创意想法
- 测试镜头和运动方向
- 调整时长和节奏

最终成片请使用 MiniMax / Kling 等商业 API。

### Q: 草稿失败会自动调用商业 API 吗？

**不会**。草稿 provider 失败只会：
1. 返回明确的失败状态
2. （如果启用 fallback）尝试其他草稿 provider
3. **绝不自动切换到商业 API**

这是为了防止"本地失败 → 意外烧钱"。

### Q: 什么时候应该切换到成片 provider？

当你：
- ✅ 对草稿的镜头角度满意
- ✅ 对人物运动方向满意
- ✅ 对时长和节奏满意
- ✅ 准备好生成最终交付版本

此时切换到 `kling` / `minimax` 等成片 provider。

---

## 相关文档

- [API 测试与成本矩阵 →](../api/test_cost_matrix.md)
- [节点参数参考 →](../api/node_reference.md)
- [状态码说明 →](../api/status_codes.md)
- [← 返回文档首页](../README.md)

