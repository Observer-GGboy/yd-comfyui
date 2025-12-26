# DirectorMV 配置指南

> 📌 **环境变量和 API Key 配置说明。**

---

## 环境变量配置

通过环境变量配置各 Provider 的 API Key：

```bash
# MiniMax (海螺 AI)
export MINIMAX_API_KEY="your_minimax_key"

# Kling (快手可灵)
export KLING_API_KEY="your_kling_key"

# Runway
export RUNWAY_API_KEY="your_runway_key"

# Vidu (清华 Vidu)
export VIDU_API_KEY="your_vidu_key"
```

---

## Windows 配置

### 临时设置（当前会话）

```powershell
$env:MINIMAX_API_KEY = "your_minimax_key"
$env:KLING_API_KEY = "your_kling_key"
$env:RUNWAY_API_KEY = "your_runway_key"
$env:VIDU_API_KEY = "your_vidu_key"
```

### 永久设置（用户级别）

```powershell
[Environment]::SetEnvironmentVariable("MINIMAX_API_KEY", "your_key", "User")
[Environment]::SetEnvironmentVariable("KLING_API_KEY", "your_key", "User")
[Environment]::SetEnvironmentVariable("RUNWAY_API_KEY", "your_key", "User")
[Environment]::SetEnvironmentVariable("VIDU_API_KEY", "your_key", "User")
```

---

## 节点内覆盖

也可以在节点中使用 `api_key_override` 参数直接传入 API Key：

```
api_key_override: "sk-your-key-here"
```

**注意**：节点参数优先级高于环境变量。

---

## 验证配置

使用 `test_connect` 模式验证 API Key 是否有效：

```
run_mode: test_connect
provider: minimax  # 或任何需要验证的 provider
```

返回 `TEST_CONNECT_OK` 表示配置正确。

---

## 相关文档

- [测试与成本矩阵 →](../api/test_cost_matrix.md)
- [日志系统 →](./logging.md)
- [← 返回文档首页](../README.md)

