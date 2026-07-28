# SheetPilot Beacon

[English](README.md)

[![CI](https://github.com/KanadeK/sheetpilot-beacon/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/sheetpilot-beacon/actions/workflows/ci.yml)
[![Security](https://github.com/KanadeK/sheetpilot-beacon/actions/workflows/security.yml/badge.svg)](https://github.com/KanadeK/sheetpilot-beacon/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-0f766e.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/KanadeK/sheetpilot-beacon)](https://github.com/KanadeK/sheetpilot-beacon/releases)

**离线审计 Excel 公式风险、依赖关系和版本漂移。**

SheetPilot Beacon 用于发现脆弱公式、隐藏依赖、硬编码常量、高影响单元格和
公式漂移；无需把工作簿上传到外部服务，也不会保存或修改原文件。

![SheetPilot Beacon 正在审计预算样例](docs/assets/sheetpilot-beacon-ui.png)

- **给证据，而不是只给分数：**每项发现都包含代码、位置、证据、严重度和建议。
- **非破坏式契约：**分析前后校验 SHA-256，标注结果只写入新的工作簿副本。
- **同一套真实核心：**CLI、本地 Streamlit 界面和 Python 服务层共用确定性逻辑。

```bash
python -m pip install -e ".[dev]"
sheetpilot scan examples/budget_model.xlsx --output-dir audit-output
```

真实输入 → 真实输出：

```text
budget_model.xlsx: 5 findings, 18 formulas, 19 dependency edges
HTML: audit-output/budget_model.audit.html
JSON: audit-output/budget_model.audit.json
Annotated workbook: audit-output/budget_model.annotated.xlsx
```

核心不会发起网络请求；内部快照及 HTML/JSON 报告不会保留原始常量值。标注版
工作簿是源文件的完整副本，因此仍包含源数据，必须留在相同信任边界内。当前契约：
**v0.1.0**、Python 3.12、仅支持 `.xlsx`。

## 能检测什么

| 检测器 | 发现内容 |
|---|---|
| `hardcoded_intrusion` | 连续公式区域被常量打断 |
| `broken_reference` | 显式 `#REF!` 引用 |
| `formula_inconsistency` | 偏离周边主导相对引用模式的公式 |
| `high_fanout` | 被大量公式依赖的高影响单元格 |
| `hidden_dependency` | 可见计算依赖隐藏工作表 |
| `external_link` | 指向工作簿外部的公式或关系 |
| `circular_reference` | 依赖图中的公式循环 |

工具还会盘点公式、命名范围、隐藏/深度隐藏工作表、合并单元格和外链，构建单元格
与工作表依赖图，并比较两个版本中的公式、常量指纹和工作表漂移。

## 安装

### 从源码安装

```bash
git clone https://github.com/KanadeK/sheetpilot-beacon.git
cd sheetpilot-beacon
python -m venv .venv
python -m pip install -e ".[dev]"
```

请使用虚拟环境中的 Python 3.12。仓库也提交了 `uv.lock`：

```bash
uv sync --frozen --all-extras
```

### 从 GitHub Release 安装

从 [v0.1.0](https://github.com/KanadeK/sheetpilot-beacon/releases/tag/v0.1.0)
下载平台无关 wheel，先用 `SHA256SUMS.txt` 校验，再安装：

```bash
python -m pip install sheetpilot_beacon-0.1.0-py3-none-any.whl
```

## 快速开始

审计仓库内的三个合成样例，并生成静态报告索引：

```bash
sheetpilot demo --samples-dir examples --output-dir demo-output
```

打开 `demo-output/index.html`，也可以查看已发布的
[静态样例演示](https://kanadek.github.io/sheetpilot-beacon/)。

启动本地界面：

```bash
sheetpilot web --port 8501
```

界面支持工作簿审计、版本对比、HTML/JSON 下载和标注版工作簿下载。文件只在本地
Streamlit 进程内处理。

## CLI

```text
sheetpilot scan WORKBOOK [--output-dir DIR] [--fanout-threshold N]
                          [--fail-on none|critical|high|medium|low|info]
sheetpilot diff BEFORE AFTER [--output-dir DIR]
sheetpilot demo [--samples-dir DIR] [--output-dir DIR]
sheetpilot web [--port PORT]
sheetpilot --version
```

`scan` 成功时返回 `0`，输入/输出失败时返回 `1`；启用 `--fail-on` 且发现达到
阈值时返回 `3`。解析失败不会被伪装成“零问题”的成功结果。

对比两个版本：

```bash
sheetpilot diff \
  examples/budget_model.xlsx \
  revised-budget.xlsx \
  --output-dir drift-output
```

漂移模型会区分：新增/删除/修改公式、公式被常量替换、常量被公式替换、常量指纹
改变，以及工作表新增/删除。报告不会写出常量原值。

## Python 接口

v0.1.0 不提供网络 API；稳定的程序化边界是类型化服务层：

```python
from pathlib import Path

from sheetpilot_beacon.services.audit import audit_workbook
from sheetpilot_beacon.services.diff import compare_workbooks

audit = audit_workbook(Path("examples/budget_model.xlsx"))
print(audit.metrics.formula_cell_count, len(audit.issues))

drift = compare_workbooks(Path("before.xlsx"), Path("after.xlsx"))
for change in drift.changes:
    print(change.kind.value, change.sheet, change.cell)
```

Pydantic 模型不可变且拒绝未知字段；时间相关逻辑使用可注入 clock，便于测试和演示
稳定复现。

## 样例契约

仓库提交了三个 MIT 许可的纯合成工作簿：

| 工作簿 | 公式数 | 预置发现 | 场景 |
|---|---:|---:|---|
| `budget_model.xlsx` | 18 | 5 | 部门预算与隐藏假设 |
| `sales_forecast.xlsx` | 18 | 5 | 区域销售预测与历史外部费率 |
| `engineering_boq.xlsx` | 18 | 5 | 工程量清单与成本汇总 |

`examples/expected_findings.json` 声明全部 15 个预期
`(code, sheet, cell)`。集成测试既会检查漏报，也会检查超出清单的误报。详见
[样例说明](examples/README.md)。

## 输出格式

- **HTML 审计：**独立、响应式、键盘可读的证据表。
- **JSON 审计：**供自动化使用的稳定类型数据，不含常量原值。
- **标注 `.xlsx`：**新副本，包含 `Beacon Audit` 工作表、批注、链接、筛选和颜色。
- **HTML/JSON 漂移：**精确列出版本变化和两端源文件哈希。

导出器会 HTML 转义工作簿文本，并对写入审计表且形似公式的文本添加前缀，防止
报告标记注入和生成审计单元格中的 Excel 公式注入。

## 架构

```text
CLI / Streamlit / Python
            │
services：audit · diff · demo
            │
domain：不可变模型 · 公式解析 · 依赖图 · 检测器 · 漂移
            │
adapters：openpyxl 读取 · HTML/JSON/XLSX 导出 · 样例生成
```

领域层不依赖 Streamlit 或网络。依赖边从前置单元格指向使用它的公式单元格；
读取器不会让 Excel 计算公式。模块职责、数据流和不变量详见
[架构文档](docs/ARCHITECTURE.md)。

## 隐私与安全边界

- 分析器离线运行且无遥测。
- `.xlsx` 作为不可信输入处理；损坏的压缩包会显式失败。
- 默认文件上限 100 MiB、单工作表范围 1,000,000 个单元格、公式范围展开上限
  10,000 个单元格。
- 常量以带类型的 SHA-256 指纹表示，不进入报告原文。
- 公式和外链证据中形似凭据的内容会被掩码。
- 不执行宏；`.xls`、`.xlsm` 和加密工作簿不属于本版本契约。
- 静态分析不能证明工作簿计算结果正确。
- 标注副本保留所有源数据；分享任何产物前都应人工检查。

完整威胁模型、控制措施、剩余风险与披露方式见
[隐私与安全](docs/PRIVACY_AND_SECURITY.md)。

## 验证

完整本地质量门会运行 lint、格式检查、严格 mypy、全部单元/集成/隐私/回归/E2E
测试和分支覆盖率，最后进行隔离 wheel 与 sdist 构建：

```bash
python scripts/verify.py
```

等价的分步命令：

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80
python -m build
```

v0.1.0 发布门在 Windows 上通过 **51 项测试、85.82% 总覆盖率**，包含三条子进程
CLI 工作流及 Streamlit 应用契约。样例性能实测见
[基准](docs/BENCHMARK.md)，发布门见
[发布清单](docs/RELEASE_CHECKLIST.md)。

## 复现演示素材

README 截图来自真实本地 Streamlit 进程：脚本上传
`examples/budget_model.xlsx`，运行审计后再截图。

```bash
python -m playwright install chromium
python scripts/capture_demo.py
```

脚本会等待 Streamlit 健康检查，上传真实样例，确认审计和下载控件可用，再捕获渲染
结果；不会使用任何生产工作簿。

构建并检查完整 Release 制品：

```bash
python scripts/package_release.py
python scripts/release_check.py
```

打包步骤会构建 wheel 和 sdist、复制三个样例、生成静态报告与演示压缩包，在全新
虚拟环境中安装 wheel 并执行真实扫描，最后写入 `SHA256SUMS.txt`。

## 非目标与已知限制

- 不负责公式求值、财务模型认证或业务数值正确性验证。
- 不编辑或修复源工作簿。
- 不支持 VBA、`.xls`、`.xlsb`、`.xlsm`、加密文件、Power Query、数据连接和
  完整 Excel 计算链仿真。
- 尚不能完美解析所有 Excel 扩展语法、表结构化引用、动态数组或 Cube 公式。
- 不提供托管上传服务；Pages 只部署由合成样例生成的静态报告。

检测结果是复核线索，不是缺陷判决。对有意不规则的模型，仍可能出现误报或漏报。

## 路线图

0.1 之后的优先方向包括：表结构化引用、可配置策略文件、SARIF 输出、大工作簿
流式处理，以及面向财务和工程模型的检测器校准。任何检测语义变化都必须附带合成
样例和回归证据。

## 贡献与安全

修改检测器前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，只使用合成工作簿。
安全问题请通过 GitHub 私密漏洞报告提交，详见 [SECURITY.md](SECURITY.md)。

公开仓库抽样检索未发现同名且高度同构的活跃项目。SheetPilot Beacon 的差异化在于
组合了离线风险规则、公式被常量替换的漂移检测、非破坏式导出和可执行的 15 问题
样例契约。这是有限范围的公开仓库抽样结论，不是全球唯一性声明。详见
[竞品扫描](docs/COMPETITOR_SCAN.md)。

## 常见问题

### 会上传我的工作簿吗？

不会。CLI、Python 核心和本地 Streamlit 进程不会发起外部请求。静态演示由仓库
合成样例生成，也不接受上传。

### 会修改原工作簿吗？

不会。审计前后都会校验源文件哈希；需要标注结果时，只写入不同路径的新副本。

### 为什么 HTML/JSON 中没有常量原值？

结构化公式审计不需要这些值。模型保存带类型的指纹，因此版本对比仍能发现常量
变化，而无需序列化其内容。

### 每一项发现都是错误吗？

不是。发现代表值得复核的证据，建议栏会说明下一步检查；有意设置的例外可以保留。

### 能审计 `.xlsm` 或计算公式吗？

v0.1.0 不能。接受的格式是 `.xlsx`，分析器只读取公式文本，不运行 Excel、宏或
计算引擎。

## 许可证

[MIT](LICENSE)。三个合成样例工作簿及生成的样例报告采用相同许可证。
