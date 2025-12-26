# DirectorMV 文档中心

> 📖 **MV Director System - ComfyUI 自定义节点文档**

---

## 快速导航

| 分类 | 文档 | 说明 |
|------|------|------|
| 🎬 **Workflow** | [**草稿 vs 成片流程**](./workflows/draft_vs_production.md) | ⭐ 草稿引擎使用指南、最佳实践 |
| 🔌 **API** | [测试与成本矩阵](./api/test_cost_matrix.md) | Provider 能力、计费规则、冒烟测试 |
| 🔌 **API** | [节点参数参考](./api/node_reference.md) | DMV_API_Image2Video 完整参数 |
| 🔌 **API** | [状态码说明](./api/status_codes.md) | 测试/生产模式状态码定义 |
| ⚙️ **运维** | [配置指南](./operations/configuration.md) | 环境变量、API Key 设置 |
| ⚙️ **运维** | [日志系统](./operations/logging.md) | API 日志位置、字段、分析 |
| 🎬 **Workflow** | [Workflow 指南](./workflows/guide.md) | 预置 Workflow 说明和使用 |
| 📋 **实现** | [实现总结](./implementation/summary.md) | 开发记录、完成状态 |

---

## 目录结构

```
docs/
├── README.md                    # 本文档（总入口）
├── api/                         # API 相关文档
│   ├── test_cost_matrix.md      # 测试与成本矩阵
│   ├── node_reference.md        # 节点参数参考
│   └── status_codes.md          # 状态码说明
├── operations/                  # 运维相关文档
│   ├── configuration.md         # 配置指南
│   └── logging.md               # 日志系统
├── workflows/                   # Workflow 文档
│   ├── guide.md                 # Workflow 使用指南
│   └── draft_vs_production.md   # ⭐ 草稿 vs 成片流程
└── implementation/              # 实现细节
    └── summary.md               # 实现总结
```

---

## 常用场景

### 🚀 快速开始

1. [配置 API Key](./operations/configuration.md)
2. [验证连通性（零成本）](./api/test_cost_matrix.md#零成本验证-api-配置)
3. [加载 Workflow](./workflows/guide.md)

### 💰 控制成本

- [Provider 计费规则](./api/test_cost_matrix.md#provider-测试能力矩阵)
- [最低成本冒烟测试](./api/test_cost_matrix.md#最低成本冒烟测试)
- [测试模式使用](./api/node_reference.md#测试模式)

### 🔧 调试问题

- [查看 API 日志](./operations/logging.md)
- [理解状态码](./api/status_codes.md)
- [节点参数说明](./api/node_reference.md)

---

## 支持的 Provider

### Production Providers（成片引擎 - 商业 API）

| Provider | 模型 | 最低成本 | 文档 |
|----------|------|----------|------|
| **MiniMax** | I2V-01, I2V-01-Director, I2V-01-live, S2V-01 | $0.48 | [详情](./api/test_cost_matrix.md#minimax-海螺-ai) |
| **Kling** | kling-v1, kling-v1-5, kling-v2 | $0.14 | [详情](./api/test_cost_matrix.md#kling-快手可灵) |
| **Runway** | gen3a_turbo, gen4_turbo | $0.25 | [详情](./api/test_cost_matrix.md#runway) |
| **Vidu** | vidu-1.0, vidu-1.5, vidu-2.0 | $0.20 | [详情](./api/test_cost_matrix.md#vidu-清华-vidu) |

### Draft Providers（草稿引擎 - 本地 GPU）

| Provider | 模型 | VRAM | 成本 | 文档 |
|----------|------|------|------|------|
| **local_turbodiffusion** | TurboDiffusion | 16 GB | 🆓 $0.00 | [详情](./workflows/draft_vs_production.md) |
| **local_wan_i2v** | Wan I2V | 20 GB | 🆓 $0.00 | [详情](./workflows/draft_vs_production.md) |
| **local_cogvideo_fast** | CogVideoX Fast | 18 GB | 🆓 $0.00 | [详情](./workflows/draft_vs_production.md) |

> ⚠️ **草稿 Provider 仅用于预览/迭代，非终稿质量。最终成片请用商业 API。**

---

## 返回项目

- [← 项目 README](../README.md)
- [← Workflow 文件目录](../workflows/)

