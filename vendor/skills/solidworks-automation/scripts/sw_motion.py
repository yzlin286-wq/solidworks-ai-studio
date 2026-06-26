"""
SolidWorks Motion Study 自动化工具。

本模块封装 Motion Study 中最容易踩坑的流程：加载专用类型库、创建运动算例、
创建匀速旋转马达并触发计算。SolidWorks API 使用米作为长度单位；转速参数使用 RPM。
"""
import glob
import os

try:
    from .sw_preflight import import_com_dependencies
    from .sw_connect import safe_get_com_member
    from .sw_assembly import find_largest_cylinder_face
except ImportError:
    from sw_preflight import import_com_dependencies
    from sw_connect import safe_get_com_member
    from sw_assembly import find_largest_cylinder_face

pythoncom, win32com_client, VARIANT = import_com_dependencies()


SW_FM_AEM_ROTATIONAL_MOTOR = 78
SW_MOTION_STUDY_BASIC_MOTION = 1


def _motion_typelib_candidates():
    """枚举常见 SolidWorks Motion Study 类型库路径。"""
    patterns = [
        r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\swmotionstudy.tlb",
        r"C:\Program Files\SOLIDWORKS Corp*\SOLIDWORKS\swmotionstudy.tlb",
        r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS*\swmotionstudy.tlb",
        r"C:\Program Files\Dassault Systemes\SOLIDWORKS*\swmotionstudy.tlb",
        r"E:\Solidworks\SOLIDWORKS\swmotionstudy.tlb",
    ]
    seen = set()
    for pattern in patterns:
        for path in glob.glob(os.path.expandvars(pattern)):
            norm = os.path.normcase(os.path.abspath(path))
            if norm in seen:
                continue
            seen.add(norm)
            yield path


def ensure_motion_type_library(raise_on_error=False):
    """
    @brief 生成 SolidWorks Motion Study 类型库的 pywin32 包装。
    @param raise_on_error 找不到或加载失败时是否抛异常。
    @return 成功加载的类型库路径；失败且 raise_on_error=False 时返回 None。

    Motion Study 的 `IMotionStudyManager` 位于 `swmotionstudy.tlb`，不在主
    `sldworks` 类型库里。未加载该类型库时，pywin32 动态对象常出现
    `CreateMotionStudy`、`GetMotionStudyCount` 等成员像属性不像方法的情况。
    """
    errors = []
    for path in _motion_typelib_candidates():
        try:
            tlb = pythoncom.LoadTypeLib(path)
            guid, lcid, _syskind, major, minor, _flags = tlb.GetLibAttr()
            win32com_client.gencache.EnsureModule(guid, lcid, major, minor)
            return path
        except Exception as exc:
            errors.append(f"{path}: {exc}")

    if raise_on_error:
        detail = "\n".join(errors) if errors else "未找到 swmotionstudy.tlb"
        raise RuntimeError("无法加载 SolidWorks Motion Study 类型库:\n" + detail)
    return None


def motion_member(obj, attr_name, *args):
    """
    @brief 兼容 Motion Study COM 成员“属性/方法”双态。
    @param obj COM 对象。
    @param attr_name 成员名。
    @param args 当成员可调用时传入的参数。
    @return 成员值或方法返回值。

    实测 SolidWorks 2024 + pywin32 下，`CreateMotionStudy`、`Activate`、
    `Calculate`、`Play` 可能表现为属性，`SetDuration`、`CreateDefinition`、
    `CreateFeature` 通常表现为方法。本函数统一隐藏差异。
    """
    member = getattr(obj, attr_name)
    if args:
        if callable(member):
            return member(*args)
        if len(args) == 0:
            return member
        raise TypeError(f"Motion Study 成员不可调用: {attr_name}")
    try:
        return member() if callable(member) else member
    except Exception as exc:
        message = str(exc)
        if "-2147352573" in message or "找不到成员" in message or "Member not found" in message:
            return member
        raise


def get_motion_study_manager(asm_model, load_type_library=True):
    """
    @brief 获取装配体的 MotionStudyManager。
    @param asm_model 装配体 IModelDoc2/IAssemblyDoc。
    @param load_type_library 是否先加载 `swmotionstudy.tlb`。
    @return MotionStudyManager COM 对象。
    """
    if load_type_library:
        ensure_motion_type_library(raise_on_error=False)
    manager = safe_get_com_member(asm_model.Extension, "GetMotionStudyManager")
    if manager is None:
        raise RuntimeError("无法获取 MotionStudyManager，请确认当前文档是装配体且 SolidWorks Motion 可用")
    return manager


def create_motion_study(asm_model, name=None, duration=4.0, study_type=None):
    """
    @brief 创建并激活一个 Motion Study。
    @param asm_model 装配体 IModelDoc2/IAssemblyDoc。
    @param name 可选算例名称。
    @param duration 动画时长，单位秒。
    @param study_type 可选 Motion Study 类型；None 时保持 SolidWorks 默认。
    @return Motion Study COM 对象。
    """
    manager = get_motion_study_manager(asm_model)
    study = motion_member(manager, "CreateMotionStudy")
    if study is None:
        raise RuntimeError("新建 Motion Study 失败")
    if name:
        try:
            study.Name = name
        except Exception:
            pass
    if study_type is not None:
        try:
            study.StudyType = int(study_type)
        except Exception:
            pass
    if not bool(motion_member(study, "Activate")):
        raise RuntimeError("激活 Motion Study 失败")
    if duration is not None:
        try:
            motion_member(study, "SetDuration", float(duration))
        except Exception:
            pass
    return study


def _set_first_supported(obj, names, value):
    """按候选属性名设置第一个可用属性。"""
    last_error = None
    for name in names:
        try:
            setattr(obj, name, value)
            return name
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError("候选属性名不能为空")


def _set_load_references(motor_data, references):
    """
    @brief 为马达设置载荷引用，兼容 tuple/list/VARIANT 多种 COM 接收方式。
    @param motor_data ISimulationMotorFeatureData。
    @param references 装配体上下文实体列表。
    @return True 表示设置成功。
    """
    variants = [
        tuple(references),
        list(references),
        VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, list(references)),
        VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, list(references)),
    ]
    for refs in variants:
        try:
            motor_data.LoadReferences = refs
            return True
        except Exception:
            continue
    return False


def add_constant_speed_rotary_motor(
    motion_study,
    direction_reference,
    load_reference,
    rpm=60.0,
    relative_component=None,
    name=None,
    reverse=False,
):
    """
    @brief 给 Motion Study 添加匀速旋转马达。
    @param motion_study Motion Study COM 对象。
    @param direction_reference 旋转方向引用，通常为装配体上下文中的轴或圆柱面。
    @param load_reference 被驱动组件引用，通常为叶轮/转子圆柱面。
    @param rpm 转速，单位 RPM。
    @param relative_component 可选相对静止组件。
    @param name 可选马达特征名。
    @param reverse 是否反向旋转。
    @return 创建出的马达 Feature。
    """
    motor_data = motion_member(motion_study, "CreateDefinition", SW_FM_AEM_ROTATIONAL_MOTOR)
    if motor_data is None:
        raise RuntimeError("创建旋转马达 FeatureData 失败")

    motor_data.DirectionReference = direction_reference
    motion_member(motor_data, "ConstantSpeedMotor", float(rpm))
    motor_data.ReverseDirection = bool(reverse)
    if relative_component is not None:
        motor_data.RelativeComponent = relative_component

    try:
        motor_data.Location = load_reference
    except Exception:
        pass

    if not _set_load_references(motor_data, [load_reference]):
        raise RuntimeError("设置旋转马达 LoadReferences 失败")
    motor_feature = motion_member(motion_study, "CreateFeature", motor_data)
    if motor_feature is None:
        raise RuntimeError("创建旋转马达特征失败")
    if name:
        try:
            motor_feature.Name = name
        except Exception:
            pass
    return motor_feature


def add_constant_speed_rotary_motor_by_cylinders(
    motion_study,
    shaft_component,
    rotor_component,
    shaft_radius=None,
    rotor_radius=None,
    rpm=60.0,
    name=None,
    reverse=False,
):
    """
    @brief 通过两个圆柱面查找旋转轴和被驱动转子，并添加匀速旋转马达。
    @param motion_study Motion Study COM 对象。
    @param shaft_component 静止轴/支架组件。
    @param rotor_component 被驱动旋转组件。
    @param shaft_radius 轴圆柱半径范围 `(min, max)`，单位米；None 表示不限。
    @param rotor_radius 转子圆柱半径范围 `(min, max)`，单位米；None 表示不限。
    @param rpm 转速，单位 RPM。
    @param name 可选马达特征名。
    @param reverse 是否反向旋转。
    @return 创建出的马达 Feature。
    """
    shaft_radius = shaft_radius or (0.0, None)
    rotor_radius = rotor_radius or (0.0, None)
    direction_reference = find_largest_cylinder_face(
        shaft_component,
        min_radius=shaft_radius[0],
        max_radius=shaft_radius[1],
    )
    load_reference = find_largest_cylinder_face(
        rotor_component,
        min_radius=rotor_radius[0],
        max_radius=rotor_radius[1],
    )
    return add_constant_speed_rotary_motor(
        motion_study,
        direction_reference,
        load_reference,
        rpm=rpm,
        relative_component=shaft_component,
        name=name,
        reverse=reverse,
    )


def calculate_and_play(motion_study, play=True):
    """
    @brief 计算 Motion Study，并可选播放动画。
    @param motion_study Motion Study COM 对象。
    @param play True 时计算成功后调用 Play。
    @return Calculate 的布尔结果。
    """
    calculated = bool(motion_member(motion_study, "Calculate"))
    if play and calculated:
        try:
            motion_member(motion_study, "Play")
        except Exception:
            pass
    return calculated
