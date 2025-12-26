# DirectorMV API 状态码说明

> 📌 **测试模式返回的 status 使用专用状态码，不会伪装成生产成功。**

---

## 状态码一览

| 状态码 | 说明 | 适用模式 |
|--------|------|----------|
| `TEST_CONNECT_OK` | 连通性测试成功 | test_connect |
| `TEST_CONNECT_FAIL` | 连通性测试失败 | test_connect |
| `TEST_CREATE_OK` | 任务创建成功 | test_create |
| `TEST_CREATE_FAIL` | 任务创建失败 | test_create |
| `TEST_POLL_OK` | 轮询测试成功 | test_poll |
| `TEST_POLL_FAIL` | 轮询测试失败 | test_poll |
| `TEST_DOWNLOAD_OK` | 下载测试成功 | test_download |
| `TEST_DOWNLOAD_FAIL` | 下载测试失败 | test_download |
| `PROD_SUCCESS` | 生产模式成功 | prod_full |
| `PROD_FAIL` | 生产模式失败 | prod_full |

---

## 状态码详解

### test_connect 模式

- **`TEST_CONNECT_OK`**: API Key 有效，网络连通正常
- **`TEST_CONNECT_FAIL`**: API Key 无效、网络错误或鉴权失败

### test_create 模式

- **`TEST_CREATE_OK`**: 任务创建成功，返回有效 task_id
- **`TEST_CREATE_FAIL`**: 任务创建失败（参数错误、余额不足等）

### test_poll 模式

- **`TEST_POLL_OK`**: 轮询期间任务状态正常（进行中或已完成）
- **`TEST_POLL_FAIL`**: 轮询期间任务失败或超时

### test_download 模式

- **`TEST_DOWNLOAD_OK`**: 下载链接有效，可以获取视频
- **`TEST_DOWNLOAD_FAIL`**: 下载链接无效或权限不足

### prod_full 模式

- **`PROD_SUCCESS`**: 视频生成完成，文件已下载
- **`PROD_FAIL`**: 生成过程中出错

---

## 设计原则

1. **明确区分**：测试状态码以 `TEST_` 前缀，生产状态码以 `PROD_` 前缀
2. **不伪装成功**：测试模式永远不会返回 `PROD_SUCCESS`
3. **详细诊断**：当 `return_debug=True` 时，status 包含完整错误信息
4. **从不返回 "unknown error"**：所有错误都有明确的状态码和描述

---

## 相关文档

- [测试与成本矩阵 →](./test_cost_matrix.md)
- [节点参数参考 →](./node_reference.md)
- [← 返回文档首页](../README.md)

