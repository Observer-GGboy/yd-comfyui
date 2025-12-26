# DirectorMV API 日志系统

> 📌 **所有 API 调用都会记录到日志文件，便于调试和成本追踪。**

---

## 日志位置

```
ComfyUI/temp/directormv/api_logs/*.jsonl
```

每个会话生成一个独立的日志文件，命名格式：`session_YYYYMMDD_HHMMSS.jsonl`

---

## 日志字段

| 字段 | 说明 |
|------|------|
| `timestamp` | ISO 时间戳 |
| `provider` | 提供商 (minimax/kling/runway/vidu/local) |
| `model` | 使用的模型 |
| `run_mode` | 运行模式 |
| `operation` | 操作类型 (image2video/lipsync 等) |
| `request_url` | 请求 URL |
| `http_status` | HTTP 状态码 |
| `response_body` | 响应体 (截断 ≤ 2KB) |
| `task_id` | 任务 ID |
| `file_id` | 文件 ID (如有) |
| `download_url` | 下载 URL (参数打码) |
| `error` | 错误信息 (如有) |
| `duration_seconds` | 操作耗时 |
| `estimated_cost_usd` | 预估成本 |
| `actual_cost_usd` | 实际成本 (如可获取) |

---

## 敏感信息处理

日志系统自动对敏感信息进行脱敏处理：

| 类型 | 处理方式 | 示例 |
|------|----------|------|
| API Key | 部分打码 | `sk-xxxx****xxxx` |
| 下载 URL 参数 | 完全打码 | `?[PARAMS_MASKED]` |
| 响应体 | 截断 | ≤ 2KB |

---

## 日志示例

```json
{
  "timestamp": "2025-12-26T18:14:02.709286",
  "provider": "minimax",
  "model": "I2V-01",
  "run_mode": "prod_full",
  "operation": "image2video",
  "request_url": "https://api.minimax.chat/v1/video_generation",
  "http_status": 200,
  "task_id": "dmv_minimax_image2video_20251226181402_0001",
  "provider_task_id": "348942904557692",
  "duration_seconds": 172.308488,
  "estimated_cost_usd": 0.48,
  "status": "success"
}
```

---

## 日志分析

### 查找失败任务

```bash
grep "FAIL" ComfyUI/temp/directormv/api_logs/*.jsonl
```

### 统计成本

```bash
grep "cost_usd" ComfyUI/temp/directormv/api_logs/*.jsonl | jq -s 'map(.actual_cost_usd) | add'
```

---

## 相关文档

- [配置指南 →](./configuration.md)
- [实现总结 →](../implementation/summary.md)
- [← 返回文档首页](../README.md)

