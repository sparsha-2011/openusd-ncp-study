# Day 8 — Content Aggregation

> **OpenUSD NCP Certification Study Notes**  
> *Instancing, PointInstancer, Asset Management, Scenegraph Best Practices*

---

## Table of Contents

1. [Instancing — Native USD Instancing](#1-instancing--native-usd-instancing)
2. [Point Instancing — UsdGeomPointInstancer](#2-point-instancing--usdgeompointinstancer)
3. [Per-Instance Overrides](#3-per-instance-overrides)
4. [Asset Versioning and Management](#4-asset-versioning-and-management)
5. [Scenegraph Organisation Patterns](#5-scenegraph-organisation-patterns)
6. [Key Takeaways](#6-key-takeaways)

---

## 1. Instancing — Native USD Instancing

**Instancing** allows multiple prims to share the same underlying data (the **prototype**) without duplicating it in memory. All instances reference one prototype, dramatically reducing memory usage for repeated objects.

```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.Open("scene.usda")

# Make a prim instanceable
tree_prim = stage.GetPrimAtPath("/World/Tree_001")
tree_prim.SetInstanceable(True)
# USD now treats this prim as an instance that shares a prototype

# Check instancing status
print(tree_prim.IsInstanceable())   # True
print(tree_prim.IsInstance())       # True — if USD has promoted to instance
print(tree_prim.IsPrototype())      # True — if this prim IS the prototype
```

### Native Instancing Rules

- A prim becomes **instanceable** when `instanceable = True` is set in its metadata
- USD automatically creates a **prototype** (the shared data)
- All instanceable prims that reference the same data become instances of that prototype
- Instances share geometry data — memory usage is for one prototype, not N copies
- **Instance proxies** — reading properties on an instance returns the prototype's value; writing directly to an instance's children requires `SetInstanceable(False)` first

```usda
def Xform "Tree_001" (
    instanceable = true
    prepend references = @./tree_asset.usda@
) { }

def Xform "Tree_002" (
    instanceable = true
    prepend references = @./tree_asset.usda@
) { }
# Both trees share one prototype — memory for one tree
```

---

## 2. Point Instancing — UsdGeomPointInstancer

`UsdGeomPointInstancer` places many instances of one or more prototype prims at positions defined by arrays. It is the highest-performance instancing mechanism in USD — designed for forests, crowds, particle systems, and any scenario with thousands to millions of repeated objects.

```
UsdGeomPointInstancer (/World/Forest)
├── prototypes (hidden):
│   └── /World/Forest/Protos/Tree (Mesh — the shared geometry)
├── protoIndices  = [0, 0, 0, 0, ...]  # which prototype each instance uses
├── positions     = [(x,y,z), ...]      # where each instance is placed
├── orientations  = [(quat), ...]       # rotation of each instance
└── scales        = [(sx,sy,sz), ...]   # scale of each instance
```

### Python API — `UsdGeom.PointInstancer`

```python
from pxr import UsdGeom, Vt, Gf, Usd

stage      = Usd.Stage.CreateInMemory()
instancer  = UsdGeom.PointInstancer.Define(stage, "/World/Forest")

# 1. Define the prototype (the shared geometry)
proto_root = stage.DefinePrim("/World/Forest/Protos")
tree_proto = UsdGeom.Sphere.Define(stage, "/World/Forest/Protos/Tree")
tree_proto.GetRadiusAttr().Set(0.5)

# 2. Point instancer to the prototypes
instancer.GetPrototypesRel().AddTarget("/World/Forest/Protos/Tree")

# 3. Define per-instance arrays
num_instances = 1000
import random

positions = Vt.Vec3fArray([
    Gf.Vec3f(random.uniform(-50, 50), 0, random.uniform(-50, 50))
    for _ in range(num_instances)
])
proto_indices = Vt.IntArray([0] * num_instances)  # all use prototype 0

instancer.GetPositionsAttr().Set(positions)
instancer.GetProtoIndicesAttr().Set(proto_indices)
```

### Per-Instance Customisation

Point instancing supports per-instance variation through the per-instance arrays:

| Array | Type | Controls |
|-------|------|---------|
| `positions` | `point3f[]` | World position of each instance |
| `orientations` | `quath[]` | Rotation (quaternion) of each instance |
| `scales` | `float3[]` | Scale of each instance |
| `protoIndices` | `int[]` | Which prototype each instance uses (enables variety) |
| `invisibleIds` | `int64[]` | Instance IDs to hide |

---

## 3. Per-Instance Overrides

Point instancing supports per-instance attribute variations. Each instance can have different colours, materials, or custom attributes driven by primvars on the PointInstancer or by connecting shader inputs to per-instance primvars.

### Correct Override Approaches

| Approach | How | Use case |
|----------|-----|---------|
| Per-instance transforms | `positions`, `orientations`, `scales` arrays | Different placement per instance |
| Per-instance material variation | Connect `UsdShade` inputs to primvars | Different colour per instance |
| `UsdReferences` with payloads | Reference asset at different paths with selective overrides | Targeted property overrides |

### Wrong Approaches

| Wrong approach | Why it's wrong |
|----------------|---------------|
| Modify the prototype prim directly | Changes ALL instances — not a per-instance override |
| Duplicate the entire prototype for each instance | Destroys instancing efficiency — defeats the purpose |
| Use `variantSets` on the prototype for per-instance variation | Variants on the prototype affect ALL instances globally |

> **Point instancing DOES support per-instance material variations.** This is a common exam trap — the false statement is "point instancing disables per-instance material variations." It does not. Per-instance materials work via primvar-driven shader inputs.

---

## 4. Asset Versioning and Management

### References — Single Source of Truth

Using references instead of duplicating data means there is one authoritative copy of each asset. Update the asset file and all scenes that reference it automatically see the update.

```python
# Instead of duplicating chair geometry into every scene:
# scene_A.usda, scene_B.usda, scene_C.usda all reference:
chair = stage.DefinePrim("/World/ChairA")
chair.GetReferences().AddReference("./assets/chair_v003.usda")
# Update chair_v003.usda → all three scenes update automatically
```

### Variant Sets for Versioning

Variant sets can represent different versions or configurations of the same asset within one file:

```usda
def Xform "Chair" (
    prepend variantSets = "version"
    variants = { string version = "v003" }
) {
    variantSet "version" = {
        "v001" { prepend references = @./chair_v001.usda@ }
        "v002" { prepend references = @./chair_v002.usda@ }
        "v003" { prepend references = @./chair_v003.usda@ }
    }
}
```

### Payloads for Performance

Reference large assets as payloads so scenes open quickly even when they contain many heavy assets:

```python
# Heavy asset referenced as payload — not loaded until explicitly requested
heavy_prim = stage.DefinePrim("/World/HighResCity")
heavy_prim.GetPayloads().AddPayload("./city_highres.usda")

# Open stage without loading any payloads — instant open
stage = Usd.Stage.Open("scene.usda", Usd.Stage.LoadNone)

# Load only the assets you need
stage.Load("/World/HighResCity")
```

### Version Control Best Practices

| ✅ Do | ❌ Don't |
|-------|---------|
| Reference assets — one source of truth | Embed all data in each stage |
| Use variant sets for version switching | Rely only on file naming conventions |
| Version delivery files (`v001`, `v002`) | Overwrite original USD files directly |
| Keep source composition files under version control | Edit flattened delivery files directly |

---

## 5. Scenegraph Organisation Patterns

### Standard Hierarchy Convention

```
/World                              ← Xform — root of the scene
├── /World/Geometry  (Scope)        ← all renderable geometry
│   ├── /World/Geometry/Chair (Mesh)
│   └── /World/Geometry/Table (Mesh)
├── /World/Lights    (Scope)        ← all lights
│   └── /World/Lights/KeyLight
├── /World/Looks     (Scope)        ← all materials
│   └── /World/Looks/WoodMat
└── /World/Cameras   (Scope)
    └── /World/Cameras/MainCam
```

### `UsdGeomScope` vs `UsdGeomXform`

| Schema | Transform? | Use case |
|--------|-----------|---------|
| `UsdGeomXform` | ✅ Yes | Grouping prims that need to move together |
| `UsdGeomScope` | ❌ No | Namespace organisation only — no transform overhead |

Use `Scope` for containers like `/World/Looks/`, `/World/Lights/` where you need grouping but no transform. Use `Xform` where the group itself needs to be positioned or animated.

---

## 6. Key Takeaways

| Concept | What to Remember |
|---------|-----------------|
| **Native instancing** | `SetInstanceable(True)` — shares prototype data, reduces memory |
| **PointInstancer** | Highest performance — for forests, crowds, particles |
| **`positions`, `protoIndices`** | Core per-instance arrays on PointInstancer |
| **Per-instance materials** | Supported via primvar-driven shader inputs — not disabled |
| **Modify prototype = global change** | Affects ALL instances — not a per-instance override |
| **References = single source of truth** | Update asset file → all referencing scenes update |
| **Payloads for heavy assets** | `Stage.LoadNone` + explicit `Load()` — optimal for large scenes |
| **UsdGeomScope** | Namespace grouping, no transform. For `/Looks/`, `/Lights/` |
| **UsdGeomXform** | Transform container. For groups that need to move. |
| **Don't overwrite originals** | Version deliveries (`v001`, `v002`), never overwrite source |

---

*Previous: [Day 7 — Pipeline Development and Data Exchange](day-07-pipeline-and-data-exchange.md)*  
*Next: [Day 9 — Debugging and Troubleshooting](day-09-debugging-and-troubleshooting.md)*
