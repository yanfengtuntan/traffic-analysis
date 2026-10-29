# 数据与运行环境检查报告

检查日期：2026-10-22  
项目目录：`D:\26作业\人工智能\traffic_analysis`

## 1. 结论摘要

- 已读取 `PROJECT_BRIEF.md`，后续工作目录固定为本项目目录。
- `data.7z` 已安全解压到 `data_raw/data/`；原压缩包未删除、未覆盖、未改名。
- 压缩包内恰好包含 3 个 CSV 与 3 个对应的 GeoJSON。
- 三套 CSV 的时间戳均严格递增、间隔一致，无重复时间、缺失时间点、空值、非数值、无穷值或负值。
- Milano 与 Trentino 的 CSV 区域和 GeoJSON 区域完全一一对应。
- ZTE CSV 的 148 个区域全部能匹配 GeoJSON；GeoJSON 另有 14 个无流量数据区域，应用中必须显式标为“无数据”。
- ZTE 数据含 735 个精确零值，因此不能把普通 MAPE 作为主要指标。建议以 MAE、RMSE 为主，可选增加 sMAPE 或带保护项的 MAPE，并清楚标注定义。
- 数据包没有说明数值的物理单位或是否经过归一化，界面统一使用“流量值”，不标为 GB。
- 当前可执行的 Python 是 MSYS2/MinGW 版 Python 3.11.9，不是常见的官方 Windows CPython；其二进制包标签为 `mingw_x86_64_ucrt`。NumPy、pandas、scikit-learn、Streamlit 等常用 PyPI Windows 轮子通常是 `win_amd64`，直接安装存在兼容风险。正式开发前应安装或选用官方 64 位 CPython 3.11/3.12，并创建项目独立虚拟环境。

## 2. 原始文件与解压结果

原压缩包：

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `data.7z` | 25,846,518 | `E8B75A10E4D96B6170FC806ED8C00C2CEAA99191EC7B223F5658FB4F32E0E0A5` |

解压文件：

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `milano_traffic_nid.csv` | 14,597,187 | `001CA22429C6FB2362A10CB2D8806FE1DD1EE32AA09F5DE0DE9FB29612FC04AF` |
| `milano.geojson` | 1,090,792 | `141559D8730DD4D58A503FC59A796A88CEB9F8D8BCA5EAC8FC7DB99BACB2DE60` |
| `trentino_traffic_nid.csv` | 36,814,681 | `7522881673CE4CE1765BFA9C39FEAFC1B2EC54655D1834EA73C41462A612083F` |
| `trento.geojson` | 927,287 | `8DFAE12FC87CF1940C129C5632729DAD672E76A4068C8CBE0CC24220F1A7D4D3` |
| `zte_4g_down.region.csv` | 5,757,121 | `DEB776ACFACCAD2F5D3CAAD9A0DFEE8436CF622D3E50CB87415A54391B144A61` |
| `zte_4g_down.traffic.geojson` | 1,408,893 | `07676C541649FFEDE384003525C47587274252E7DE15F05A6A5461899653136F` |

说明：Windows 自带的 `C:\Windows\System32\tar.exe` 能直接列出并解压此 7z；系统未找到独立的 7-Zip 命令。

## 3. CSV 结构与质量

| 数据集 | 时间列 | 区域数 | 时间点数 | 起始时间 | 结束时间 | 间隔 | 数值单元格 | 零值 | 最小值 | 最大值 |
| --- | --- | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| Milano | 首列列名为空 | 88 | 8,928 | 2013-11-01 00:00 | 2014-01-01 23:50 | 10 分钟 | 785,664 | 0 | 54.5918 | 103,678.4785 |
| Trentino | 首列列名为空 | 223 | 8,928 | 2013-11-01 00:00 | 2014-01-01 23:50 | 10 分钟 | 1,990,944 | 0 | 6.1168 | 54,278.5867 |
| ZTE（济南） | `date` | 148 | 2,784 | 2024-07-28 00:00 | 2024-08-25 23:45 | 15 分钟 | 412,032 | 735 | 0 | 292,035,287.58 |

补充核验：

- 三套数据的区域列名均唯一，所有行的列数正确。
- 三套数据均无空值、非数值、NaN/无穷值和负值。
- 三套数据均无重复时间戳，且没有缺失的时间步。
- Milano 和 Trentino 各覆盖连续 62 天；ZTE 覆盖连续 29 天。
- CSV 时间戳没有携带时区信息，应用按数据中的本地“朴素时间”展示，不擅自换算时区。
- Milano/Trentino 首列列名为空，加载时需显式重命名为统一字段（例如 `timestamp`）。
- ZTE 数值量级明显高于另两套数据；三套数据必须分别分析和缩放，不能拼接或跨数据集拟合同一缩放器。

## 4. GeoJSON 结构与匹配

三套文件都是 `FeatureCollection`，坐标参考标识均为 `urn:ogc:def:crs:OGC:1.3:CRS84`，即展示时按经度、纬度处理。

| 数据集 | 要素数 | 匹配属性 | 几何类型 | CSV 精确匹配 | 仅地图有 |
| --- | ---: | --- | --- | ---: | ---: |
| Milano | 88 | `NIL` | 88 Polygon | 88 | 0 |
| Trentino | 223 | `NAME_3` | 188 Polygon、35 MultiPolygon | 223 | 0 |
| ZTE（济南） | 162 | `unique_id` | 159 Polygon、3 MultiPolygon | 148 | 14 |

所有地图要素都有几何和匹配键，匹配键没有重复。大致边界框（西、南、东、北）如下：

- Milano：`[9.040602, 45.386723, 9.277981, 45.535944]`
- Trentino：`[10.453161, 45.673965, 11.963678, 46.533653]`
- ZTE（济南）：`[116.216088, 35.992103, 117.969736, 37.536913]`

ZTE 中仅地图存在、CSV 无流量列的 14 个区域编码：

`370104004`、`370104005`、`370105003`、`370112005`、`370112011`、`370112013`、`370113201`、`370114003`、`370114005`、`370114006`、`370114008`、`370114010`、`370114012`、`370114015`

ZTE GeoJSON 的 `name` 与 `ext_path` 是正常中文，例如“解放路街道”和“山东省 济南市 历下区 解放路街道”。若在终端看到乱码，是当前 MinGW Python 使用 GBK stdout，而外层工具按另一编码解释导致；不是数据文件损坏。地图关联应使用稳定的 `unique_id`，不要使用中文名称。

GeoJSON 中的 `mean_traffic` 是随文件附带的静态属性，只可用于核验或说明，不能充当用户所选时刻/时段的地图值。应用必须从 CSV 按当前选择重新计算聚合值。

## 5. Python 与依赖环境

| 项目 | 检查结果 |
| --- | --- |
| 操作系统 | Windows 11，64 位（内部版本 22631） |
| `python` | 3.11.9，`D:\c\ucrt64\bin\python.exe` |
| Python 构建 | GCC UCRT / MSYS2 MinGW，平台标签 `mingw_x86_64_ucrt` |
| `pip` | 24.2，可调用 |
| `venv` | 模块可调用 |
| `py` 启动器 | 存在，但报告“没有已安装的 Python” |
| Git | 可用；当前项目尚不是 Git 仓库 |
| 7-Zip CLI | 未安装；系统 `tar.exe` 可处理当前 7z |

以下项目依赖均未安装：`numpy`、`pandas`、`streamlit`、`scikit-learn`、`plotly`、`geopandas`、`shapely`、`statsmodels`、`torch`、`tensorflow`、`py7zr`。

环境建议：

1. 使用官方 Windows x86-64 CPython 3.11 或 3.12，而不是当前 MinGW Python。
2. 在项目内创建 `.venv`，全部依赖固定到 `requirements.txt`。
3. 第一版优先使用 pandas、NumPy、scikit-learn、Plotly、Streamlit、statsmodels；地图先使用 Plotly GeoJSON，尽量避免不必要的重型 GIS 依赖。
4. 深度学习算法优先选 PyTorch CPU 版；是否加入 Chronos-2 在核心功能完成后再评估，不把它作为至少 10 种算法的必要组成。

## 6. 对设计与评估的直接约束

- 默认演示可使用 ZTE：输入 96 点（24 小时），输出 4 点（1 小时）。
- 10 分钟数据对应的 24 小时输入是 144 点。
- 训练/验证/测试必须按时间顺序切分；缩放器只能在训练段拟合。
- 所有最终指标在还原到原始尺度后计算。
- ZTE 含零值，主指标使用 MAE、RMSE；普通 MAPE 不适合作为主指标。
- 多模型比较只允许在数据集、区域、测试区间、输入/输出长度和预测方式一致时进行。
- ZTE 地图的 14 个无数据区域需要独立配色和图例，不能当成 0。

## 7. 下一阶段准备创建的文件

在先建立官方 CPython 虚拟环境并验证依赖后，第二阶段拟建立以下最小结构：

```text
traffic_analysis/
├─ app.py                         # 中文首页与全局数据集选择
├─ requirements.txt              # 固定可复现依赖
├─ README.md                     # Windows 安装与运行说明
├─ .streamlit/config.toml        # 中文界面主题与服务配置
├─ pages/
│  ├─ 01_exploration.py          # 探索性分析、地图与曲线联动
│  ├─ 02_clustering.py           # 聚类分析
│  ├─ 03_dataset_builder.py      # 预测数据构建
│  ├─ 04_forecasting.py          # 模型配置、训练与预测
│  └─ 05_evaluation.py           # 实验记录、比较与导出
├─ src/
│  ├─ config.py                  # 数据集元数据与默认值
│  ├─ data_loader.py             # 统一加载、缓存与字段标准化
│  ├─ maps.py                    # 动态地图聚合与无数据处理
│  └─ charts.py                  # 时间、日内、每周图表
└─ artifacts/                    # 后续实验记录与导出结果
```

第二阶段的首个验收点是：在本机启动 Streamlit，选择 ZTE 的区域和时间/时段后，区域曲线与济南地图使用同一份筛选结果同步变化，14 个无数据区域显示为“无数据”。

## 8. 复核方式

项目保留了无第三方依赖的只读检查脚本：

```powershell
python .\scripts\analyze_data.py
```

脚本只读取 `data_raw/data/` 并向标准输出打印 JSON，不会改写原始数据。
