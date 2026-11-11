import importlib
import inspect
import pkgutil

from atguigu.domain.action import Action
from atguigu.task.action.action_runner import ActionRunner
from atguigu.task.action.custom.lookup_order_status import LookupOrderStatusAction
from atguigu.task.action.registry import ActionRegistry


def register_actions()->ActionRegistry:

    registry = ActionRegistry()
    order_status_action = LookupOrderStatusAction()
    registry.register(order_status_action)
    return registry

def register_custom_actions_to_registry()->ActionRegistry:
    registry = ActionRegistry()

    package = importlib.import_module("atguigu.task.action.custom")

    for _,module_name,is_package in pkgutil.iter_modules(package.__path__,prefix=f"{package.__name__}."):

        if is_package:
            continue

        module = importlib.import_module(module_name)

        for _,action_class in inspect.getmembers(module,inspect.isclass):
            if not issubclass(action_class,Action) or action_class is Action:
                continue

            if action_class.__module__ != module_name:
                continue

            registry.register(action_class())
    return registry

def build_action_runner()->ActionRunner:
    registry = register_custom_actions_to_registry()
    action_runner = ActionRunner(registry)
    return action_runner