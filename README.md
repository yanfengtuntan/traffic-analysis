# 区域电信流量分析与预测平台

这是一个面向人工智能课程 final project 的中文 Streamlit 应用。当前版本已完成五个功能模块、三套真实数据分析、12 种预测算法、实验保存与公平对比，并配套运行说明、演示脚本和汇报 PPT。

## 用 VS Code 打开

1. 在 VS Code 中选择“文件 → 打开文件夹”。
2. 打开 `D:\26作业\人工智能\traffic_analysis`。
3. 如果右下角询问 Python 解释器，选择 `.venv\Scripts\python.exe`。项目的 `.vscode/settings.json` 已配置默认解释器。
4. 打开 VS Code 集成终端，运行：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

浏览器会打开本地网址 `http://localhost:8501`。停止应用时，在终端按 `Ctrl+C`。

也可以直接双击项目根目录下的 `run_app.bat`。脚本只使用项目内 `.venv`，并把缓存和临时文件限制在本项目目录。

## 在线访问与部署

课程 final presentation 要求应用部署到网络。正式提交使用 Streamlit Community Cloud 公网地址，不使用 `localhost`。部署完成后在这里填写最终网址：

```text
公网应用地址：部署后填写
```

完整发布步骤和课堂前检查见 `DEPLOYMENT.md`。免费平台长时间无人访问后会休眠，展示前应提前访问一次完成唤醒。

## 在新电脑上重建环境

先安装官方 64 位 Python 3.12，然后在本目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 当前进度

- 已完成：数据解压与核验、项目内虚拟环境、五模块导航骨架。
- 已完成：Milano、Trentino、ZTE 三套数据切换。
- 已完成：区域时间曲线、日内模式、每周模式、所选时段统计和动态地图。
- 已完成：ZTE 地图额外 14 个无数据区域的灰色标识。
- 已完成：按时间顺序切分、训练集缩放、滑动窗口、样本数量与预览。
- 已完成：持久性基线、线性回归、KNN、SVR、决策树、随机森林、Extra Trees、梯度提升的真实运行。
- 已完成：原始尺度 MAE/RMSE、实验持久化、预测明细和公平比较。
- 已完成：K-means、DBSCAN 的真实时间模式聚类、地图、代表曲线、PCA 展示与导出。
- 已完成：ARIMA、MLP、1D CNN、LSTM、GRU；神经网络逐轮显示并保存训练/验证损失。
- 已满足：12 种真正可运行的预测算法，另含持久性基线。
- 已完成：主要异常提示、界面打磨、完整运行说明、演示脚本和 11 页汇报 PPT。

## 项目结构

```text
app.py                      Streamlit 入口与导航
pages/                      五个功能页面
src/                        数据、地图、聚类、预测和实验管理逻辑
data_raw/data/              解压后的只读原始数据副本
artifacts/experiments/      已保存实验、预测明细和训练历史
scripts/analyze_data.py     无第三方依赖的数据检查脚本
DATA_REPORT.md              数据质量与环境检查报告
DEMO_SCRIPT.md              课堂演示顺序和讲解词
DELIVERY_CHECKLIST.md       提交前检查清单
DEPLOYMENT.md               公网部署与验收说明
run_app.bat                 Windows 一键启动
ppt_output/                 课程汇报 PPT
```

## 常见问题

### 端口 8501 被占用

在 VS Code 终端换一个端口启动：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

### 地图区域能显示，但底图为空

区域边界来自本地 GeoJSON，不受影响；浅色道路底图来自在线地图服务。检查网络后刷新页面即可。

### 神经网络运行时间较长

当前使用 CPU 版 PyTorch。课堂演示建议把最大训练轮数设为 5；正式实验可增加轮数并保留早停。

### 新电脑无法直接使用现有 `.venv`

虚拟环境通常不能跨电脑复制。安装官方 64 位 Python 3.12 后，按“在新电脑上重建环境”重新创建即可。

## 提交前必须填写

打开 `src/config.py`，把 `PROJECT_AUTHOR = "待填写"` 改为真实姓名。汇报 PPT 中的姓名、学号和班级也需手工填写。

原始压缩包 `data.7z` 保持不变。数据检查细节见 `DATA_REPORT.md`。

