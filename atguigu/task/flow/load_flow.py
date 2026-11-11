from pathlib import Path
from typing import Any
import yaml
from atguigu.domain.flow_catalog import FlowCatalog, Flow, FlowSlot, FlowStep, CollectSlotStep


class FlowLoader:

    def load_many(self, flow_paths:list[Path])->FlowCatalog:
        """
            加载多个流程定义文件返回流程清单对象
        :param flow_paths: 多个文件路径
        :return: FlowCatalog
        """
        slots: dict[str, FlowSlot] = {}
        flows: dict[str, Flow] = {}
        # 遍历路径列表
        for flow_path in flow_paths:
            flow_catalog:FlowCatalog = self.load(flow_path)
            slots.update(flow_catalog.slots)
            flows.update(flow_catalog.flows)
        return FlowCatalog(flows, slots)

    def load(self, flow_path: Path) -> FlowCatalog:
        """读取但个流程定义yaml文件，获取所有流程定义、槽位定义"""
        slots: dict[str, FlowSlot] = {}
        flows: dict[str, Flow] = {}

        # 1.通过yaml模块safe_load读取yaml内容，得到字典
        with open(flow_path, "r", encoding="utf-8") as f:
            # 得到yaml内容得到字典
            data = yaml.safe_load(f)
        # 2.处理槽位配置
        slots = self._load_slots(data.get("slots", {}))

        # 3.处理流程配置
        flows = self._load_flows(data.get("flows", {}), slots)

        return FlowCatalog(flows=flows, slots=slots)

    def _load_slots(self, slots_data: dict[str, Any]) -> dict[str, FlowSlot]:
        """读取字典配置，封装槽位信息"""
        slots: dict[str, FlowSlot] = {}
        for slot_name, slot_data in slots_data.items():
            # slot_name槽位名称 slot_data槽位字典
            slots[slot_name] = FlowSlot(**slot_data, name=slot_name)
        return slots

    def _load_flows(self, flows_data: dict[str, Any], slots: dict[str, FlowSlot]) -> dict[str, Flow]:
        """
            解析所有流程定义，返回所有流程配置字典
        :param flows_data: 流程配置 字典
        :param slots: 系统支持槽位配置 字典
        :return: 流程字典
        """
        flows: dict[str, Flow] = {}
        for flow_id,flow_data in flows_data.items():
            flows[flow_id] = self._load_flow(flow_id, flow_data, slots)
        return flows

    def _load_flow(self, flow_id:str, flow_data:dict[str, Any], slots:dict[str, FlowSlot])->Flow:
        """封装单个流程配置对象"""
        #1.获取该流程内包含所有步骤列表
        steps:list[FlowStep] = [FlowStep.from_dict(step_data) for step_data in flow_data.get("steps")]
        #2.获取收集类型步骤列表获取步骤所需槽位，得到槽位列表
        step_slots:list[FlowSlot] = [slots.get(step.slot_name) for step in steps if isinstance(step, CollectSlotStep) ]
        #3.封装流程对象
        return Flow(
            id=flow_id,
            description=flow_data.get("description"),
            name=flow_data.get("name"),
            steps=steps,
            slots=step_slots
        )