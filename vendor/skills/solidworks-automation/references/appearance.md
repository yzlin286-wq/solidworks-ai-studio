# 外观与材质参考

## 推荐用法

```python
from sw_appearance import set_document_appearance, set_feature_appearance

set_document_appearance(model, "iron_red")
set_feature_appearance(feature, "armor_gold")
```

## 预设颜色

| 名称 | 说明 |
|---|---|
| `iron_red` | 深红装甲 |
| `armor_gold` | 金色装甲 |
| `dark_gunmetal` | 深色金属/关节 |
| `arc_blue` | 蓝色发光件 |
| `silver` | 银色金属 |
| `black` | 黑色 |
| `white` | 白色 |

## 稳定性建议

- 单零件多特征上色可能受 SolidWorks 版本、显示状态、特征合并影响。
- 对颜色要求高的模型，优先拆成多个零件，并对每个零件使用文档级外观。
- 复杂项目建议输出装配体，由组件层级表达颜色、材质和可替换模块。
- 生成后必须用 `sw_review.py` 导出预览图检查颜色和层次是否可见。

