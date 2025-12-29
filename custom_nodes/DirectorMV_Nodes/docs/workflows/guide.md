# DirectorMV Workflow 指南

> 📌 **预置 Workflow 模板说明和使用指南。**

---

## Workflow 命名规范

| 后缀 | 说明 |
|------|------|
| `_dmv_main.json` | **生产 Workflow** - 仅使用 DMV_* 节点 |
| `_baseline.json` | 对比 Workflow - 直接使用第三方节点 |

**重要**：生产 Workflow (`*_dmv_main.json`) 不应直接使用第三方 API 节点（Kling、Runway 等），应使用 `DMV_API_*` 统一节点。

---

## Workflow 版本

### v0 - 单人（最小可行版本）

**主 Workflow**: `v0_dmv_main.json` ⭐ (生产)
**对比 Workflow**: `v0_kling_baseline.json` (仅对比)

#### v0 Main Workflow (`v0_dmv_main.json`)

仅使用 DMV 统一节点：

**流程**:
1. 加载参考图片
2. 通过 `DMV_IdentityExtractor` 提取身份
3. 通过 `DMV_IdentityCache` 缓存身份
4. 通过 `DMV_API_Image2Video` 生成视频 (provider=auto)
5. 通过 `DMV_API_LipSync` 应用口型同步 (provider=auto)
6. 通过 `DMV_TaskTracker` 跟踪成本

**使用的 DMV 节点**:
- `DMV_IdentityExtractor`
- `DMV_IdentityCache`
- `DMV_API_Image2Video` (统一 Provider 抽象)
- `DMV_API_LipSync` (统一 Provider 抽象)
- `DMV_TaskTracker`

**特性**:
- 自动 Provider 选择 (Kling → MiniMax → Vidu → Local)
- Provider 失败时自动回退
- 每任务成本追踪
- Task ID 日志便于调试

**需求**:
- Workflow 中不需要第三方节点
- 通过环境变量配置 API Key

---

### v1 - 双人

**文件**: `v1_dual_person.json`

完整双人 MV，支持分镜调度。

**流程**:
1. 加载两个角色图片
2. 提取并缓存身份
3. 解析分镜脚本
4. 调度镜头
5. 生成每个镜头（双人/单人按需）
6. 合成最终视频
7. 应用口型同步

**需求**:
- PuLID_ComfyUI
- Kling API 访问权限
- ComfyUI-VideoHelperSuite

---

### v2 - 生产版（计划中）

**文件**: `v2_production.json`

生产就绪 Workflow，完整质量控制和重试逻辑。

**额外特性**:
- 自动质量门控
- 失败重试
- 成本路由（本地 vs API）
- 语音克隆集成
- 批处理

---

## 使用方法

1. 打开 ComfyUI
2. 加载所需 Workflow JSON
3. 配置输入（图片、音频、分镜脚本）
4. 连接现有节点（PuLID、Kling 等）
5. 执行 Workflow

---

## 自定义

这些模板是起点，可通过以下方式自定义：
- 调整质量门控阈值
- 更改 Router 中的视频生成策略
- 添加额外处理节点

---

## Workflow 文件列表

| 文件 | 描述 | 状态 |
|------|------|------|
| `v0_dmv_main.json` | 单人生产 Workflow | ✅ 可用 |
| `v0_kling_baseline.json` | Kling 对比 Workflow | ✅ 可用 |
| `v0_single_person_workflow.json` | 单人 Workflow（旧版） | ✅ 可用 |
| `v0_single_person.json` | 单人 Workflow（简化） | ✅ 可用 |
| `v1_dual_person.json` | 双人 Workflow | ✅ 可用 |

---

## 相关文档

- [节点参数参考 →](../api/node_reference.md)
- [测试与成本矩阵 →](../api/test_cost_matrix.md)
- [← 返回文档首页](../README.md)


---

## v2 Styling Castpack Safety (test_connect)

- `v2_styling_castpack.json` shows `run_mode`, `select_index`, and a "Kling VTON executed?" status in UI.
- If ImpactSwitch lazy bypass does not prevent Kling execution on older ComfyUI:
  1) Duplicate `v2_styling_castpack.json`.
  2) Disconnect `KlingVirtualTryOnNode` and `ImpactSwitch`.
  3) Connect `DMV_ApplyOutfitTransfer.person_image` directly into the hair inpaint chain.
  4) Keep `run_mode=test_connect` so logs record `vton_called=false`.
