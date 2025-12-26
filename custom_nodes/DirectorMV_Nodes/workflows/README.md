# DirectorMV Workflows

> 📖 **完整文档请见**: [docs/workflows/guide.md](../docs/workflows/guide.md)

预置 Workflow 模板，用于常见 MV 生成场景。

---

## Workflow 文件

| 文件 | 描述 | 状态 |
|------|------|------|
| `v0_dmv_main.json` | 单人生产 Workflow ⭐ | ✅ 可用 |
| `v0_kling_baseline.json` | Kling 对比 Workflow | ✅ 可用 |
| `v0_single_person_workflow.json` | 单人 Workflow（旧版） | ✅ 可用 |
| `v0_single_person.json` | 单人 Workflow（简化） | ✅ 可用 |
| `v1_dual_person.json` | 双人 Workflow | ✅ 可用 |

---

## 命名规范

| 后缀 | 说明 |
|------|------|
| `_dmv_main.json` | **生产 Workflow** - 仅使用 DMV_* 节点 |
| `_baseline.json` | 对比 Workflow - 直接使用第三方节点 |

---

## 相关文档

- [Workflow 使用指南 →](../docs/workflows/guide.md)
- [节点参数参考 →](../docs/api/node_reference.md)
- [测试与成本矩阵 →](../docs/api/test_cost_matrix.md)
- [← 项目 README](../README.md)

