"""
SolidWorks 外观与材质工具。

SolidWorks 的外观 API 在不同版本和对象类型上差异较多，本模块优先提供
容错封装：同一颜色会依次尝试文档、特征、组件层级的常见接口。
"""
import re


PRESET_COLORS = {
    "iron_red": "#8A0E0E",
    "armor_gold": "#D99A22",
    "dark_gunmetal": "#1F2328",
    "arc_blue": "#2AA8FF",
    "black": "#050505",
    "white": "#F2F2F2",
    "silver": "#BFC4C8",
}


def rgb01(color):
    """
    将颜色转换为 0..1 RGB。

    支持:
        - 预设名，如 "iron_red"
        - 十六进制，如 "#8A0E0E"
        - 0..255 RGB 元组
        - 0..1 RGB 元组
    """
    if isinstance(color, str):
        value = PRESET_COLORS.get(color, color).strip()
        match = re.fullmatch(r"#?([0-9a-fA-F]{6})", value)
        if not match:
            raise ValueError(f"未知颜色: {color}")
        hex_value = match.group(1)
        return tuple(int(hex_value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    if len(color) != 3:
        raise ValueError("RGB 颜色必须包含 3 个值")
    if max(color) > 1:
        return tuple(float(v) / 255.0 for v in color)
    return tuple(float(v) for v in color)


def material_values(color, ambient=0.35, diffuse=0.75, specular=0.45,
                    shininess=0.35, transparency=0.0, emission=0.0):
    """
    生成 SolidWorks 材质属性数组。

    数组顺序为:
        red, green, blue, ambient, diffuse, specular, shininess, transparency, emission
    """
    red, green, blue = rgb01(color)
    return [red, green, blue, ambient, diffuse, specular, shininess, transparency, emission]


def _try_set(target, attr_name, values):
    """尝试设置属性或调用方法。"""
    try:
        member = getattr(target, attr_name)
        if callable(member):
            result = member(values)
        else:
            setattr(target, attr_name, values)
            result = True
        return bool(result) if result is not None else True
    except Exception:
        return False


def set_document_appearance(model, color, configuration=""):
    """
    设置文档级外观颜色。

    返回:
        bool 是否至少一个接口调用成功。
    """
    values = material_values(color)
    ok = False
    ok = _try_set(model, "MaterialPropertyValues", values) or ok
    try:
        ok = bool(model.SetMaterialPropertyValues2(values, 0, configuration)) or ok
    except Exception:
        pass
    try:
        ok = bool(model.ISetMaterialPropertyValues2(values, 0, configuration)) or ok
    except Exception:
        pass
    return ok


def set_feature_appearance(feature, color, configuration=""):
    """
    设置特征级外观颜色。

    返回:
        bool 是否至少一个接口调用成功。
    """
    values = material_values(color)
    ok = False
    try:
        ok = bool(feature.SetMaterialPropertyValues2(values, 0, configuration)) or ok
    except Exception:
        pass
    try:
        ok = bool(feature.ISetMaterialPropertyValues2(values, 0, configuration)) or ok
    except Exception:
        pass
    ok = _try_set(feature, "MaterialPropertyValues", values) or ok
    return ok


def set_component_appearance(component, color, configuration=""):
    """
    设置装配体组件外观颜色。

    返回:
        bool 是否至少一个接口调用成功。
    """
    values = material_values(color)
    ok = False
    try:
        ok = bool(component.SetMaterialPropertyValues2(values, 0, configuration)) or ok
    except Exception:
        pass
    try:
        ok = bool(component.ISetMaterialPropertyValues2(values, 0, configuration)) or ok
    except Exception:
        pass
    ok = _try_set(component, "MaterialPropertyValues", values) or ok
    return ok


def apply_named_appearance(target, name):
    """
    给任意常见对象应用预设外观。

    该函数会按文档、组件、特征的顺序尝试。
    """
    return (
        set_document_appearance(target, name)
        or set_component_appearance(target, name)
        or set_feature_appearance(target, name)
    )

