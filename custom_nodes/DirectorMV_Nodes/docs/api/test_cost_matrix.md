# DirectorMV API 测试与成本矩阵

> 📌 **本文档说明各 Provider 的测试模式可用性、计费规则和最低成本冒烟测试配置。**

---

## 测试模式说明

| 模式 | 说明 | 是否计费 |
|------|------|----------|
| `prod_full` | 完整生成视频（生产模式） | ✅ 计费 |
| `test_connect` | 调用非计费接口验证连通性 | ❌ 免费 |
| `test_create` | 创建任务获取 task_id 后返回 | ⚠️ 可能计费 |
| `test_poll` | 创建任务后轮询 N 秒查看状态 | ⚠️ 可能计费 |
| `test_download` | 验证下载权限 | ❌ 免费 |

---

## Provider 测试能力矩阵

| Provider | Model | test_connect | test_create 计费 | 支持 Cancel | 最低成本配置 | 预估成本 (USD) |
|----------|-------|--------------|------------------|-------------|--------------|----------------|
| **MiniMax** | I2V-01 | ✅ `/files/list` | ⚠️ 是 | ❌ 不支持 | 6s, 720P | $0.48 |
| **MiniMax** | I2V-01-Director | ✅ | ⚠️ 是 | ❌ | 6s, 720P | $0.60 |
| **MiniMax** | I2V-01-live | ✅ | ⚠️ 是 | ❌ | 6s, 720P | $0.60 |
| **MiniMax** | S2V-01 | ✅ | ⚠️ 是 | ❌ | 6s, 720P | $0.60 |
| **Kling** | kling-v1 | ✅ Auth验证 | ⚠️ 是 | ❌ | 5s, std, 720p | $0.14 |
| **Kling** | kling-v1-5 | ✅ | ⚠️ 是 | ❌ | 5s, std, 720p | $0.14 |
| **Kling** | kling-v2 | ✅ | ⚠️ 是 | ❌ | 5s, std, 720p | $0.175 |
| **Runway** | gen3a_turbo | ✅ `/account` | ⚠️ 是 | ✅ DELETE | 5s, 720p | $0.25 |
| **Runway** | gen4_turbo | ✅ | ⚠️ 是 | ✅ | 5s, 720p | $0.50 |
| **Vidu** | vidu-1.0 | ✅ `/user/info` | ⚠️ 是 | ❌ | 4s, 720p | $0.20 |
| **Vidu** | vidu-1.5 | ✅ | ⚠️ 是 | ❌ | 4s, 720p | $0.25 |
| **Vidu** | vidu-2.0 | ✅ | ⚠️ 是 | ❌ | 4s, 720p | $0.30 |
| **Local** | hunyuan/cogvideo | ✅ | ❌ 否 | ✅ | - | $0.00 |

---

## Provider 详细说明

### MiniMax (海螺 AI)

**官方文档**: https://platform.minimaxi.com/document/video-generation

**支持模型**:
- `I2V-01`: 图生视频基础版
- `I2V-01-Director`: 支持镜头控制
- `I2V-01-live`: 支持参考主体
- `S2V-01`: 主体到视频

**参数约束**:
- 时长: 6秒 (固定)
- 分辨率: 720P, 1080P
- 帧率: 24fps

**计费规则**:
- 按次计费，每次生成约 $0.48 - $0.60
- **无法取消任务，test_create 会产生费用**

**test_connect 实现**:
```
GET /v1/files/list?purpose=video_generation
```
验证 API Key 有效性，不产生费用。

---

### Kling (快手可灵)

**官方文档**: https://docs.qingque.cn/d/home/eZQB6yUzJXEA6PxI4z2CMbB4F

**支持模型**:
- `kling-v1`: 基础版
- `kling-v1-5`: 增强版
- `kling-v2`: Master 版本

**参数约束**:
- 模式: std (标准), pro (专业), master (大师, 仅 v2)
- 时长: 5秒, 10秒
- 分辨率: 720p, 1080p
- 支持尾帧图 (tail_image)

**计费规则**:
| 模型 | 5s std | 5s pro | 5s master | 10s std | 10s pro | 10s master |
|------|--------|--------|-----------|---------|---------|------------|
| kling-v1 | $0.14 | $0.28 | - | $0.28 | $0.56 | - |
| kling-v1-5 | $0.14 | $0.28 | - | $0.28 | $0.56 | - |
| kling-v2 | $0.175 | $0.35 | $0.70 | $0.35 | $0.70 | $1.40 |

**⚠️ 无官方取消 API，test_create 会产生费用**

**test_connect 实现**:
发送 GET 请求到 `/v1/videos/image2video` 验证 Auth（返回 405 但鉴权通过）。

---

### Runway

**官方文档**: https://docs.runwayml.com/

**支持模型**:
- `gen3a_turbo`: Gen-3 Alpha Turbo
- `gen4_turbo`: Gen-4 Turbo

**参数约束**:
- 时长: 5-10秒
- 分辨率: 720p, 1080p
- 比例: 16:9

**计费规则**:
- gen3a_turbo: ~$0.05/秒
- gen4_turbo: ~$0.10/秒

**✅ 支持取消任务**: `DELETE /v1/tasks/{task_id}`

**test_connect 实现**:
```
GET /v1/account
```

---

### Vidu (清华 Vidu)

**官方文档**: https://www.vidu.cn/

**支持模型**:
- `vidu-1.0`: 基础版
- `vidu-1.5`: 增强版
- `vidu-2.0`: 最新版（支持参考图）

**参数约束**:
- 时长: 4秒, 8秒
- 分辨率: 360p, 720p, 1080p

**计费规则**:
| 模型 | 4秒 | 8秒 |
|------|-----|-----|
| vidu-1.0 | $0.20 | $0.40 |
| vidu-1.5 | $0.25 | $0.50 |
| vidu-2.0 | $0.30 | $0.60 |

**⚠️ 无官方取消 API**

**test_connect 实现**:
```
GET /v1/user/info
```

---

### Local (本地模型 - Legacy)

**支持模型**:
- HunyuanVideo
- CogVideoX

**费用**: 完全免费，仅消耗本地 GPU 资源

---

## 🎬 Draft Providers（草稿引擎）

> ⚠️ **重要**：草稿 provider 仅用于预览/迭代，**不是终稿质量**。
> 
> 最终成片请使用 MiniMax / Kling / Runway / Vidu 等商业 API。

### Provider 角色分类

| 角色 | Provider 列表 | 用途 | 费用 |
|------|--------------|------|------|
| **Production** | kling, minimax, runway, vidu | 最终成片 | 💰 按次计费 |
| **Draft** | local_turbodiffusion, local_wan_i2v, local_cogvideo_fast | 预览/草稿 | 🆓 免费 |

### Draft Provider 详细对比

| Provider | 模型 | 最低 VRAM | 推荐 VRAM | 速度 | 质量 | 适用场景 |
|----------|------|-----------|-----------|------|------|----------|
| `local_turbodiffusion` | TurboDiffusion | 16 GB | 24 GB | ⚡ 最快 | ⭐⭐ | 快速迭代、镜头测试 |
| `local_wan_i2v` | Wan I2V | 20 GB | 24 GB | 🚀 中等 | ⭐⭐⭐ | 运动验证、动作调整 |
| `local_cogvideo_fast` | CogVideoX Fast | 18 GB | 24 GB | 🚀 中等 | ⭐⭐⭐ | 节奏测试、场景预览 |

### Draft Provider 测试能力

| Provider | test_connect | test_create 计费 | 支持 Cancel | 预估成本 |
|----------|--------------|------------------|-------------|----------|
| `local_turbodiffusion` | ✅ 环境自检 | ❌ 否 | ✅ | $0.00 |
| `local_wan_i2v` | ✅ 环境自检 | ❌ 否 | ✅ | $0.00 |
| `local_cogvideo_fast` | ✅ 环境自检 | ❌ 否 | ✅ | $0.00 |

### test_connect 环境自检内容

草稿 provider 的 `test_connect` 会检查：

1. **CUDA 可用性** - GPU 是否就绪
2. **PyTorch 版本** - torch / CUDA 版本
3. **显存检查** - 是否满足最低 VRAM 要求
4. **权重文件** - 模型是否已下载

**示例输出**：
```
TEST_CONNECT_OK | local_turbodiffusion ready | GPU: NVIDIA RTX 5090 | VRAM: 28.5/32.0GB
```

### 权重文件位置

```
ComfyUI/models/video_generation/
├── turbodiffusion/
├── wan_i2v/
│   └── Wan2.1-I2V-14B-480P-Diffusers/
└── cogvideo/
    └── CogVideoX-5b-I2V/
```

### 草稿 → 成片 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│  阶段一：草稿迭代 (Draft)                                     │
│                                                             │
│  provider: local_turbodiffusion                             │
│  cost: $0                                                   │
│                                                             │
│  → 测试镜头角度                                              │
│  → 验证运动方向                                              │
│  → 调整节奏时长                                              │
│  → 满意后进入阶段二                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  阶段二：正式成片 (Production)                                │
│                                                             │
│  provider: kling / minimax / runway / vidu                  │
│  cost: $0.14 - $1.40                                        │
│                                                             │
│  → 生成最终交付视频                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 推荐测试策略

### 零成本验证 API 配置
```
run_mode: test_connect
```
所有 Provider 都支持，验证 API Key 有效性。

### 最低成本冒烟测试

**如果必须验证完整流程**:

1. **Kling** (推荐): $0.14
   ```
   provider: kling
   model: kling-v1
   mode: std
   duration: 5
   run_mode: test_create
   ```

2. **Vidu**: $0.20
   ```
   provider: vidu
   model: vidu-1.0
   duration: 4
   run_mode: test_create
   ```

3. **Runway** (支持取消): $0.25
   ```
   provider: runway
   model: gen3a_turbo
   duration: 5
   run_mode: test_create
   ```
   注: Runway 支持 DELETE 取消，但可能仍计费部分费用。

4. **MiniMax**: $0.48
   ```
   provider: minimax
   model: I2V-01
   run_mode: test_create
   ```

---

## 相关文档

- [节点参数参考 →](./node_reference.md)
- [状态码说明 →](./status_codes.md)
- [日志系统 →](../operations/logging.md)
- [← 返回文档首页](../README.md)

