# SheetPilot Beacon

SheetPilot Beacon 是一款离线 Excel 审计工具，用于定位脆弱公式、隐藏依赖、
公式区域中的硬编码常量、异常单元格和业务规则漂移。目标用户包括财务、运营、
造价、咨询和数据分析团队。

项目不会把工作簿上传到外部服务，也不会修改输入原件。公开仓库抽样检索未发现
同名且高度同构的活跃项目；检索范围、相邻项目和差异化见
[`docs/COMPETITOR_SCAN.md`](docs/COMPETITOR_SCAN.md)。

## 当前状态

首个公开契约版本为 `v0.1.0`，运行环境为 Python 3.12。

## 开发环境

```bash
python -m pip install -e ".[dev]"
python scripts/verify.py
```

后续实现里程碑会在本文件补齐真实 CLI、Web 界面、样例工作簿、演示和安全边界。

## 许可证

MIT。仓库脚本生成的合成样例工作簿同样采用 MIT 许可证。
