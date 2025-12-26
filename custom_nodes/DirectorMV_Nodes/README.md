# DirectorMV_Nodes

MV Director System - ComfyUI custom nodes for realistic MV generation with identity preservation.

> 📖 **[文档中心 →](docs/README.md)** | 📋 **[API 测试矩阵 →](docs/api/test_cost_matrix.md)** | 🔧 **[实现总结 →](docs/implementation/summary.md)**

## Features

- **Identity Preservation**: ArcFace-based identity validation and caching
- **Storyboard Parsing**: JSON/YAML storyboard script parsing and shot scheduling
- **Video Routing**: Intelligent routing between local and API video generation
- **Voice Clone & TTS**: Integration with Fish Audio and ElevenLabs
- **Quality Control**: Automatic quality gates and retry mechanisms
- **Unified API Layer**: Multi-provider support with test modes

## Architecture

This package is designed as an **independent extension** that works alongside existing ComfyUI nodes:

- **Read-only dependencies**: AIX, PuLID, LivePortrait, etc. are used via workflow composition
- **Adapter pattern**: Bridges to existing nodes without modification
- **No monkey patching**: All new code lives in this package only

## Node Naming Convention

All nodes use the `DMV_` prefix (DirectorMV):

| Category | Node | Description |
|----------|------|-------------|
| Identity | `DMV_IdentityValidator` | ArcFace identity validation |
| Identity | `DMV_IdentityCache` | Identity token caching |
| Storyboard | `DMV_StoryboardParser` | Storyboard script parsing |
| Storyboard | `DMV_ShotScheduler` | Shot scheduling |
| Video | `DMV_VideoRouter` | Video generation routing |
| Quality | `DMV_QualityGate` | Quality gate control |
| Voice | `DMV_VoiceClone` | Voice cloning API |
| Voice | `DMV_TTS` | Text-to-speech synthesis |
| **API** | `DMV_API_Image2Video` | **Unified Image-to-Video (multi-provider)** |
| API | `DMV_API_LipSync` | Unified Lip Sync API |
| API | `DMV_TaskTracker` | API task tracking & cost analysis |

---

## DMV_API_Image2Video - Unified Video Generation

### Provider 分类

| 角色 | Provider | 用途 | 费用 |
|------|----------|------|------|
| **Production** | kling, minimax, runway, vidu | 最终成片 | 💰 按次计费 |
| **Draft** | local_turbodiffusion, local_wan_i2v, local_cogvideo_fast | 预览/草稿 | 🆓 免费 |

> ⚠️ **Draft providers 仅用于预览/迭代，不是终稿质量。** 最终成片请用商业 API。
>
> 📖 详细说明：[草稿 vs 成片流程指南 →](docs/workflows/draft_vs_production.md)

### Production Providers（成片引擎）

| Provider | Models | Duration | Resolution | Est. Cost (5s) |
|----------|--------|----------|------------|----------------|
| **MiniMax** | I2V-01, I2V-01-Director, I2V-01-live, S2V-01 | 6s | 720P, 1080P | $0.48 |
| **Kling** | kling-v1, kling-v1-5, kling-v2 | 5s, 10s | 720p, 1080p | $0.14-$1.40 |
| **Runway** | gen3a_turbo, gen4_turbo | 5-10s | 720p, 1080p | $0.25-$0.50 |
| **Vidu** | vidu-1.0, vidu-1.5, vidu-2.0 | 4s, 8s | 720p, 1080p | $0.20-$0.60 |

### Draft Providers（草稿引擎）

| Provider | Model | Min VRAM | Speed | Quality | Cost |
|----------|-------|----------|-------|---------|------|
| **local_turbodiffusion** | TurboDiffusion | 16 GB | ⚡ 最快 | ⭐⭐ 草稿级 | $0.00 |
| **local_wan_i2v** | Wan I2V | 20 GB | 🚀 中等 | ⭐⭐⭐ 草稿级 | $0.00 |
| **local_cogvideo_fast** | CogVideoX Fast | 18 GB | 🚀 中等 | ⭐⭐⭐ 草稿级 | $0.00 |
| **Local** (legacy) | hunyuan, cogvideo | - | - | - | Free |

### Test Modes (核心功能)

支持多种测试模式，**验证 API 而不产生完整生成费用**：

| Mode | Description | Cost |
|------|-------------|------|
| `prod_full` | 完整视频生成（生产模式） | 正常计费 |
| `test_connect` | 验证 API 连通性和鉴权 | **免费** |
| `test_create` | 创建任务获取 task_id 后返回 | ⚠️ 可能计费 |
| `test_poll` | 创建后轮询 N 秒查看状态 | ⚠️ 可能计费 |
| `test_download` | 验证下载权限 | 免费 |

### Node Parameters

```
Required:
  - image (IMAGE): 输入图片
  - prompt (STRING): 提示词

Optional:
  Provider Selection:
  - provider: 
      Production: kling/minimax/runway/vidu (商业 API，计费)
      Draft: local_turbodiffusion/local_wan_i2v/local_cogvideo_fast (本地 GPU，免费)
      Default: local_turbodiffusion (草稿优先，避免初始烧钱)
  
  - model: auto 或具体模型名称
  - duration: 5/6/8/10 秒
  - resolution: 720p/1080p
  - mode: std/pro/master (Kling 专用)
  - negative_prompt: 负面提示词
  - cfg_scale: 0.0-1.0
  - seed: -1 为随机
  - end_image: 尾帧图 (部分模型支持)
  
Test Mode Parameters:
  - run_mode: prod_full/test_connect/test_create/test_poll/test_download
  - poll_seconds: test_poll 轮询秒数 (默认 10)
  - test_task_id: test_download 使用的 task_id
  - return_debug: 是否返回详细调试信息

Returns:
  - video_path (STRING): 生成视频路径
  - task_id (STRING): 任务 ID
  - cost_usd (FLOAT): 预估成本 (草稿 provider = 0.0)
  - status (STRING): 状态信息 (从不返回 "unknown error")
  - success (BOOLEAN): 是否成功
```

### Draft Provider 特殊行为

1. **test_connect** = 环境自检（CUDA、显存、权重）
2. **fallback** = 仅在草稿 provider 之间 fallback，**不会自动切换到商业 API**
3. **cost_usd** = 永远返回 0.0

### Status Codes

测试模式使用专用状态码，**不会伪装成生产成功**：

- `TEST_CONNECT_OK` / `TEST_CONNECT_FAIL`
- `TEST_CREATE_OK` / `TEST_CREATE_FAIL`
- `TEST_POLL_OK` / `TEST_POLL_FAIL`
- `TEST_DOWNLOAD_OK` / `TEST_DOWNLOAD_FAIL`
- `PROD_SUCCESS` / `PROD_FAIL`

---

## Test & Cost Matrix

**详细测试矩阵见**: [docs/api/test_cost_matrix.md](docs/api/test_cost_matrix.md)

### 零成本测试策略

```python
# 验证 API 配置（免费）
run_mode: test_connect
provider: minimax  # 或任何 provider
```

### 最低成本冒烟测试

| Provider | 配置 | 成本 |
|----------|------|------|
| Kling | `kling-v1, std, 5s` | $0.14 |
| Vidu | `vidu-1.0, 4s` | $0.20 |
| Runway | `gen3a_turbo, 5s` (支持取消) | $0.25 |
| MiniMax | `I2V-01, 6s` | $0.48 |

---

## API Logging

所有 HTTP 请求/响应记录到:
```
ComfyUI/temp/directormv/api_logs/*.jsonl
```

日志字段:
- provider / model / run_mode
- request_url / http_status
- response_body (截断 ≤ 2KB, API Key 打码)
- task_id / file_id / download_url
- error (如有)

---

## Requirements

### Required ComfyUI Nodes (read-only dependencies)

- `PuLID_ComfyUI` - Identity preservation
- `ComfyUI-AdvancedLivePortrait` - Expression driving
- `ComfyUI_FaceAnalysis` - Face detection
- `ComfyUI-VideoHelperSuite` - Video processing

### API Keys

通过环境变量或节点参数配置:

```bash
export MINIMAX_API_KEY="your_key"
export KLING_API_KEY="your_key"
export RUNWAY_API_KEY="your_key"
export VIDU_API_KEY="your_key"
```

或使用节点的 `api_key_override` 参数。

---

## Installation

Place this folder in `ComfyUI/custom_nodes/DirectorMV_Nodes/`

## License

MIT License
