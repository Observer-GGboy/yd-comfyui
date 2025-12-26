# DMV_API_Image2Video 节点参数参考

> 📌 **统一图生视频 API 节点，支持多 Provider 自动切换。**

---

## 支持的 Provider 和模型

| Provider | Models | Duration | Resolution | Est. Cost (5s) |
|----------|--------|----------|------------|----------------|
| **MiniMax** | I2V-01, I2V-01-Director, I2V-01-live, S2V-01 | 6s | 720P, 1080P | $0.48 |
| **Kling** | kling-v1, kling-v1-5, kling-v2 | 5s, 10s | 720p, 1080p | $0.14-$1.40 |
| **Runway** | gen3a_turbo, gen4_turbo | 5-10s | 720p, 1080p | $0.25-$0.50 |
| **Vidu** | vidu-1.0, vidu-1.5, vidu-2.0 | 4s, 8s | 720p, 1080p | $0.20-$0.60 |
| **Local** | hunyuan, cogvideo | - | - | Free |

---

## 节点参数

### 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | IMAGE | 输入图片 |
| `prompt` | STRING | 提示词 |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | ENUM | auto | auto/kling/minimax/runway/vidu/local |
| `model` | STRING | auto | auto 或具体模型名称 |
| `duration` | INT | 5 | 5/6/8/10 秒 |
| `resolution` | ENUM | 720p | 720p/1080p |
| `mode` | ENUM | std | std/pro/master (Kling 专用) |
| `negative_prompt` | STRING | "" | 负面提示词 |
| `cfg_scale` | FLOAT | 0.7 | 0.0-1.0 |
| `seed` | INT | -1 | -1 为随机 |
| `end_image` | IMAGE | None | 尾帧图 (部分模型支持) |
| `api_key_override` | STRING | "" | 覆盖环境变量中的 API Key |

### 测试模式参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `run_mode` | ENUM | prod_full | prod_full/test_connect/test_create/test_poll/test_download |
| `poll_seconds` | INT | 10 | test_poll 轮询秒数 |
| `test_task_id` | STRING | "" | test_download 使用的 task_id |
| `return_debug` | BOOL | False | 是否返回详细调试信息 |

---

## 输出

| 输出 | 类型 | 说明 |
|------|------|------|
| `video_path` | STRING | 生成视频路径 |
| `task_id` | STRING | 任务 ID |
| `cost_usd` | FLOAT | 预估成本 |
| `status` | STRING | 状态信息 (从不返回 "unknown error") |
| `success` | BOOLEAN | 是否成功 |

---

## 测试模式

支持多种测试模式，**验证 API 而不产生完整生成费用**：

| Mode | Description | Cost |
|------|-------------|------|
| `prod_full` | 完整视频生成（生产模式） | 正常计费 |
| `test_connect` | 验证 API 连通性和鉴权 | **免费** |
| `test_create` | 创建任务获取 task_id 后返回 | ⚠️ 可能计费 |
| `test_poll` | 创建后轮询 N 秒查看状态 | ⚠️ 可能计费 |
| `test_download` | 验证下载权限 | 免费 |

---

## 使用示例

### 零成本测试 API 配置

```python
# 验证 API 配置（免费）
run_mode: test_connect
provider: minimax  # 或任何 provider
```

### 生产模式

```python
# 完整视频生成
run_mode: prod_full
provider: auto  # 自动选择最优 provider
duration: 5
resolution: 720p
```

---

## 相关文档

- [测试与成本矩阵 →](./test_cost_matrix.md)
- [状态码说明 →](./status_codes.md)
- [← 返回文档首页](../README.md)

