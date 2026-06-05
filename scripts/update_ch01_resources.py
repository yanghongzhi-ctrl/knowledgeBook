from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = next((ROOT / "data/raw/ch01").glob("*.json"))
REPORT_PATH = ROOT / "output/ch01_rag_engine/reports/interactive_script_extraction_ch01.json"


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.in_script = False
        self.in_style = False
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.in_script = True
        if tag == "style":
            self.in_style = True
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_script = False
        if tag == "style":
            self.in_style = False
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self.in_script and not self.in_style:
            self.text.append(text)


def extracted_labels(path: Path) -> list[str]:
    parser = TextParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    labels: list[str] = []
    for item in parser.text:
        text = " ".join(item.split())
        if 1 < len(text) < 80 and not re.fullmatch(r"[{}();,.:#\-\s0-9%pxrem/]+", text) and text not in labels:
            labels.append(text)
    return labels[:60]


IMAGE_BINDINGS = {
    "ch01_fig_1_1": {
        "file_path": "assets/ch01/images/ch01_fig_1_1.png",
        "related_kps": ["kp_ch01_001", "kp_ch01_003", "kp_ch01_010", "kp_ch01_017", "kp_ch01_025"],
        "keywords": ["发展阶段", "CAD", "BIM", "BIM+GIS", "数字孪生", "演进"],
    },
    "ch01_fig_1_2": {
        "file_path": "assets/ch01/images/ch01_fig_1_2.png",
        "related_kps": ["kp_ch01_032", "kp_ch01_033", "kp_ch01_038", "kp_ch01_042", "kp_ch01_046", "kp_ch01_049"],
        "keywords": ["四大理念", "构件化", "参数化", "协同化", "生命周期化"],
    },
    "ch01_fig_1_3": {
        "file_path": "assets/ch01/images/ch01_fig_1_3.png",
        "related_kps": ["kp_ch01_050", "kp_ch01_051", "kp_ch01_052", "kp_ch01_053"],
        "keywords": ["技术体系", "CAD", "BIM", "GIS", "数字孪生", "AI", "平台协同"],
    },
    "ch01_fig_1_4": {
        "file_path": "assets/ch01/images/ch01_fig_1_4.png",
        "related_kps": ["kp_ch01_062", "kp_ch01_063", "kp_ch01_064"],
        "keywords": ["模型核心", "设计流程", "GIS", "BIM", "CAD", "成果交付", "全生命周期"],
    },
}


SCRIPT_META = {
    "ch01_script_timeline": {
        "theme": "道路数字化设计阶段演进",
        "objects": ["CAD阶段", "BIM阶段", "BIM+GIS阶段", "数字孪生阶段", "阶段主视觉", "关键词与典型成果"],
        "steps": ["使用上一阶段/下一阶段切换四个发展阶段", "观察每个阶段的设计对象、典型成果和核心认识", "对照图 1-1 总结从图纸表达到虚实闭环的演进主线"],
        "triggers": ["这个时间轴脚本应该怎么看？", "CAD到BIM再到数字孪生怎么演进？", "第一章发展阶段图说明了什么？", "道路数字化设计阶段有什么区别？"],
    },
    "ch01_script_cad_semantics": {
        "theme": "CAD图元语义与设计变更联动",
        "objects": ["CAD图元", "工程语义", "设计变更", "联动影响"],
        "steps": ["查看CAD图元与工程语义的对应关系", "比较图元修改对后续成果的影响", "归纳CAD图形导向机制的局限"],
        "triggers": ["CAD图元为什么不能自动联动？", "CAD阶段图元语义脚本怎么看？", "为什么说CAD缺乏工程语义？", "CAD设计变更为什么容易人工联动？"],
    },
    "ch01_script_bim_prr": {
        "theme": "道路BIM构件语义与PRR参数驱动",
        "objects": ["BIM构件", "PRR机制", "设计参数", "规则校核", "横断面结果"],
        "steps": ["选择不同工况预设", "调整设计速度、车道数、宽度和填挖高度参数", "观察参数、规则和结果的同步变化"],
        "triggers": ["PRR机制怎么演示？", "道路BIM构件语义脚本怎么看？", "BIM参数变化如何影响模型结果？", "参数规则结果之间是什么关系？"],
    },
    "ch01_script_bim_gis_overlay": {
        "theme": "BIM+GIS图层叠加与路线适宜性分析",
        "objects": ["DEM地形", "坡度分区", "河流水系", "滑坡风险区", "生态敏感区", "候选路线"],
        "steps": ["勾选基础环境图层和约束控制图层", "切换显示模式观察空间约束", "点击候选路线比较指标并判断推荐路线"],
        "triggers": ["BIM+GIS叠加分析能帮选线解决什么问题？", "路线适宜性分析脚本怎么操作？", "为什么路线B更均衡？", "GIS图层叠加如何支持道路选线？"],
    },
    "ch01_script_digital_twin": {
        "theme": "数字孪生虚实闭环联动",
        "objects": ["物理道路实体", "数字孪生模型", "IoT监测数据", "AI引擎", "预警与管控反馈"],
        "steps": ["点击不同监测数据源", "观察感知数据、模型更新、状态识别、风险预警和管控建议的联动", "归纳数字孪生区别于静态BIM的虚实闭环机制"],
        "triggers": ["数字孪生虚实闭环脚本怎么看？", "感知数据如何驱动模型更新？", "数字孪生为什么强调反馈控制？", "边坡位移联动分析说明了什么？"],
    },
    "ch01_script_concepts": {
        "theme": "道路工程数字化设计四大理念",
        "objects": ["构件化", "参数化", "协同化", "生命周期化", "核心转变", "课堂提问"],
        "steps": ["点击四个理念板块切换内容", "查看核心含义、道路工程示例和区别提示", "用四大理念解释数字化设计范式转变"],
        "triggers": ["四大理念脚本应该怎么看？", "构件化参数化协同化生命周期化有什么区别？", "道路数字化设计理念图说明什么？", "四大理念如何支撑数字化设计？"],
    },
    "ch01_script_tech_system": {
        "theme": "CAD、BIM、GIS、数字孪生技术体系协同",
        "objects": ["CAD平台", "BIM平台", "GIS平台", "数字孪生平台", "协同核心", "输入输出"],
        "steps": ["点击四个平台模块", "查看核心作用、典型任务、输入输出和协同关系", "总结多平台协同的数据流与职责分工"],
        "triggers": ["技术体系脚本怎么讲？", "CAD BIM GIS 数字孪生如何分工？", "多平台协同的核心是什么？", "道路数字化设计技术体系图怎么看？"],
    },
    "ch01_script_model_flow": {
        "theme": "以模型为核心的数字化设计流程",
        "objects": ["传统图纸流程问题", "GIS空间选线", "BIM参数建模", "CDE协同管理", "模型成果交付", "数字孪生反馈"],
        "steps": ["点击传统流程问题查看对应解决机制", "拖拽流程卡片到六个槽位", "检查从前期分析到施工运维的模型数据贯通逻辑"],
        "triggers": ["以模型为核心的流程脚本怎么操作？", "数字化设计流程包括哪些环节？", "为什么模型能解决图纸流程问题？", "GIS BIM CDE 数字孪生在流程中如何衔接？"],
    },
    "ch01_script_data_control": {
        "theme": "数据驱动的平面线形设计控制",
        "objects": ["平面线形", "转角", "圆曲线半径", "切线长", "曲线长", "规则校核", "属性反馈"],
        "steps": ["调整设计速度、圆曲线半径和路线转角", "观察几何要素自动计算", "查看规则校核和属性反馈如何随参数变化"],
        "triggers": ["数据驱动设计控制脚本怎么看？", "圆曲线半径变化会影响哪些指标？", "规则校核如何体现数据驱动？", "参数变化如何带动平面线形要素联动？"],
    },
    "ch01_script_software_modes": {
        "theme": "典型工具软件在设计阶段中的应用模式",
        "objects": ["前期分析", "路线比选", "详细设计", "协同流转", "工具平台", "输出成果"],
        "steps": ["点击阶段卡片查看主导平台和核心任务", "比较GIS、BIM、CAD、数字孪生的平台职责", "梳理输出成果在阶段间的流转关系"],
        "triggers": ["典型工具软件脚本怎么看？", "不同阶段应该用哪些工具软件？", "GIS BIM CAD 数字孪生在工程阶段怎么衔接？", "工具软件应用模式和成果流转是什么？"],
    },
}


def main() -> int:
    data = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    resources = {row["resource_id"]: row for row in data["Resources"]}

    for resource_id, binding in IMAGE_BINDINGS.items():
        row = resources[resource_id]
        row.update(binding)
        row["status"] = "bound"
        row["qa_use"] = "当问题命中相关知识点时优先推荐；当问题询问图示、示意图、流程图时可推荐"
        row["teaching_use"] = "课堂讲授、自学复习、图示解释和AI回答后资源推荐"

    scripts = []
    for resource_id, meta in SCRIPT_META.items():
        row = resources[resource_id]
        script = {
            "script_id": resource_id.replace("ch01_script_", "ch01_interactive_"),
            "resource_id": resource_id,
            "chapter_id": "ch01",
            "title": row["title"],
            "file_path": row["file_path"],
            "interaction_theme": meta["theme"],
            "display_objects": meta["objects"],
            "operation_steps": meta["steps"],
            "trigger_questions": meta["triggers"],
            "related_kps": row.get("related_kps") or [],
            "extracted_labels": extracted_labels(ROOT / row["file_path"]),
            "status": "checked",
        }
        scripts.append(script)
        row["trigger_questions"] = meta["triggers"]
        row["keywords"] = list(dict.fromkeys((row.get("keywords") or []) + meta["objects"] + [meta["theme"]]))

    data["Interactive_Scripts"] = scripts
    RAW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(scripts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated={RAW_PATH}")
    print(f"interactive_scripts={len(scripts)}")
    print(f"report={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
