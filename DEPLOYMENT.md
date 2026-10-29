# Streamlit Community Cloud 部署说明

本项目使用 GitHub 作为代码来源，并部署到 Streamlit Community Cloud。部署完成后会得到一个公开的 `https://*.streamlit.app` 地址，可在手机、平板和其他电脑上访问。

## 一、上传范围

需要上传：

- `app.py`、`pages/`、`src/`
- `.streamlit/config.toml`
- `requirements.txt`
- `data_raw/data/`
- `artifacts/experiments/` 中的预置实验结果
- README、数据报告和演示说明

不上传：

- `.venv/`、`.pip-cache/`、`.tmp/`
- `.ppt_build/`、`.codex-finalizer/`
- 原始压缩包 `data.7z`（解压后的运行数据已经包含在仓库中）

当前最大运行数据文件约 35 MB，低于 GitHub 普通单文件 100 MB 的限制。

## 二、GitHub 仓库

1. 创建一个 GitHub 仓库，建议名称为 `traffic-analysis`。
2. 将本项目目录作为仓库根目录。
3. 默认分支使用 `main`。
4. 确认 GitHub 页面中能够看到 `app.py`、`requirements.txt` 和 `data_raw/data/`。

仓库可以设为私有；部署时需要允许 Streamlit Community Cloud 读取该仓库。应用本身需要设置为允许老师通过链接访问。

## 三、Streamlit Community Cloud

1. 打开 `https://share.streamlit.io/`，使用 GitHub 账号登录。
2. 选择 **Create app**。
3. 选择刚创建的 GitHub 仓库。
4. Branch 填写 `main`。
5. Main file path 填写 `app.py`。
6. Advanced settings 中选择 Python 3.12。
7. 点击 Deploy，等待依赖安装和应用启动。

本项目不需要填写 Secrets。

## 四、部署后验收

依次检查：

- 首页能够打开，显示五个核心模块。
- 探索性分析能够切换三套数据并显示曲线和地图。
- 聚类分析能够运行默认 K-means。
- 预测数据构建能够生成默认滑动窗口。
- 预测算法能够运行线性回归。
- 评估与对比能够看到仓库中预置的持久性基线、线性回归和 MLP 结果。

将最终公网网址填写到 README、汇报 PPT 和提交材料中。

## 五、课堂展示

- 展示前 10 分钟访问公网网址并唤醒应用。
- 依次打开五个页面，让数据进入缓存。
- 现场优先展示预置实验结果；若要运行模型，选择线性回归。
- 保留本地 `run_app.bat` 和离线 PPT 作为网络异常时的备用方案。

## 六、云端存储限制

GitHub 仓库中的数据和预置实验会随每次部署恢复。用户在云端运行期间新生成的实验文件不保证在休眠、重启或重新部署后长期保留，因此不要把云端运行目录当作永久数据库。
