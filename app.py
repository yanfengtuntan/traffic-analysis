from __future__ import annotations

import streamlit as st

from src.config import COURSE_NAME, PROJECT_AUTHOR


st.set_page_config(
    page_title="区域电信流量分析与预测平台",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background: white; border: 1px solid #DDE8E5; padding: 1rem; border-radius: 0.8rem;}
    .project-kicker {color: #0F766E; font-size: 0.86rem; font-weight: 700; letter-spacing: .08em; line-height: 1.5; padding-top: .35rem;}
    .project-card {background: linear-gradient(135deg, #E8F3F1 0%, #F8FBFA 100%); border: 1px solid #CFE5DF; border-radius: 1rem; padding: 1.2rem 1.4rem;}
    .module-number {color: #0F766E; font-size: .78rem; font-weight: 700; letter-spacing: .08em; margin-bottom: .35rem;}
    .module-title {font-size: 1.18rem; font-weight: 700; color: #16302B; line-height: 1.35; margin-bottom: .45rem;}
    .module-copy {font-size: .86rem; color: #5B6F69; line-height: 1.55;}
    </style>
    """,
    unsafe_allow_html=True,
)


def home() -> None:
    st.markdown('<div class="project-kicker">AI FINAL PROJECT · TRAFFIC INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title("📡 区域电信流量分析与预测平台")
    st.caption("面向区域时空流量的探索、聚类、数据构建、预测与公平评估")
    st.markdown(
        """
        <div class="project-card">
          <b>当前可用能力</b><br>
          已接入 Milano、Trentino 与 ZTE（济南）三套真实数据，并提供真实聚类、12 种预测算法、持久性基线、实验保存与公平比较。建议从“探索性分析”开始完整体验流程。
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("五个核心模块")
    columns = st.columns(5)
    modules = [
        ("01", "探索性分析", "时间曲线、周期模式与空间联动"),
        ("02", "聚类分析", "识别相似区域流量模式"),
        ("03", "预测数据构建", "时间切分与滑动窗口"),
        ("04", "预测算法", "多模型真实训练与预测"),
        ("05", "评估与对比", "实验记录、指标与导出"),
    ]
    for column, (number, title, description) in zip(columns, modules):
        with column:
            st.markdown(
                f'<div class="module-number">{number}</div><div class="module-title">{title}</div><div class="module-copy">{description}</div>',
                unsafe_allow_html=True,
            )
    st.info("建议先进入“探索性分析”，默认展示 ZTE（济南）数据。")
    st.divider()
    st.caption(f"{COURSE_NAME} · 作者：{PROJECT_AUTHOR}（提交前请在 src/config.py 中填写）")


pages = {
    "平台": [st.Page(home, title="首页", icon="🏠", default=True)],
    "分析流程": [
        st.Page("pages/01_exploration.py", title="探索性分析", icon="🗺️"),
        st.Page("pages/02_clustering.py", title="聚类分析", icon="🧩"),
        st.Page("pages/03_dataset_builder.py", title="预测数据构建", icon="🪟"),
        st.Page("pages/04_forecasting.py", title="预测算法", icon="🧠"),
        st.Page("pages/05_evaluation.py", title="评估与对比", icon="📊"),
    ],
}

navigation = st.navigation(pages)
navigation.run()

