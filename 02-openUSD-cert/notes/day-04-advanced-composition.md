# Day 4 — Advanced Composition Concepts

> **OpenUSD NCP Certification Study Notes**  
> *Edit Targets, Session Layer, Sparse Overrides, Flattening, and Asset Structure*

---

## Table of Contents

1. [Edit Target](#1-edit-target)
2. [The Session Layer](#2-the-session-layer)
3. [Sparse Overrides](#3-sparse-overrides)
4. [Flattening — Baking Composition](#4-flattening--baking-composition)
5. [Encapsulation — Asset Structure Principles](#5-encapsulation--asset-structure-principles)
6. [Change Processing and SdfChangeBlock](#6-change-processing-and-sdfchangeblock)
7. [Full Composition Mental Model](#7-full-composition-mental-model)
8. [Key Takeaways](#8-key-takeaways)

---

## 1. Edit Target

The **edit target** controls which layer receives all authoring operations. When you call `Set()`, `DefinePrim()`, or any other authoring API, the resulting spec is written to exactly one layer — the current edit target.

By default, the edit target is the **root layer** of the stage. It can be switched to any layer in the layer stack at any time.

```
Stage (shot.usda)
├── root_layer.usda   ← edit target (default)
├── anim.usda
└── lighting.usda

prim.GetAttribute("translate").Set((5,0,0))
→ writes ONLY to root_layer.usda
→ anim.usda and lighting.usda are untouched
```

> **Most common USD pipeline bug:** authoring to the wrong edit target. The operation succeeds silently — no error is raised — but the opinion goes to the wrong layer. Always check `stage.GetEditTarget()` before authoring in multi-layer pipelines.

### Python API

```python
from pxr import Usd, Sdf

stage = Usd.Stage.Open("shot.usda")

# Check the current edit target
current = stage.GetEditTarget()
print(current.GetLayer().identifier)  # current layer receiving edits

# Switch edit target to a specific layer
anim_layer = Sdf.Layer.FindOrOpen("./anim.usda")
stage.SetEditTarget(anim_layer)
# Now ALL edits go to anim.usda

# Safe pattern — save and restore
previous = stage.GetEditTarget()
try:
    stage.SetEditTarget(anim_layer)
    prim.GetAttribute("xformOp:translate").Set((5, 0, 0))
finally:
    stage.SetEditTarget(previous)  # always restore
```

---

## 2. The Session Layer

The **session layer** is a special in-memory layer that is always the **strongest** layer in the stage. It is never saved to disk by `stage.Save()`.

```
Strength order when session layer is involved:
[0] session layer     ← STRONGEST (in-memory, never saved)
[1] root_layer.usda   ← default edit target
[2] anim.usda
[3] model.usda        ← weakest
```

### What the Session Layer Is For

- Storing ephemeral interactive overrides (e.g. usdview edits)
- Per-session customisation without affecting shared files
- Temporary overrides that should not persist after the session ends

### What It Is NOT

The session layer is **not** the same as a sublayer you create and name `"session.usda"`. It is USD's built-in in-memory layer, accessible via `stage.GetSessionLayer()`.

```python
# Access the session layer
session = stage.GetSessionLayer()

# Author into the session layer
stage.SetEditTarget(session)
prim.GetAttribute("visibility").Set("invisible")
# This override exists only in this session — not saved to disk

# Clear all session layer opinions
stage.GetSessionLayer().Clear()
# Removes ALL interactive edits made this session
```

> **Important:** `stage.Save()` never touches the session layer. If you need an override to persist, author it to a real file-backed layer instead.

---

## 3. Sparse Overrides

A **sparse override** uses an `over` spec to change only specific properties on a prim that is owned by another layer. The overriding layer only contains the properties it needs to change — all other properties flow through from the original layer unmodified.

```
model.usda (weaker — owns the prim):          anim.usda (stronger — sparse override):
def Xform "Chair" {                           over "Chair" {
    double3 xformOp:translate = (0,0,0)           double3 xformOp:translate = (5,0,0)
    double3 xformOp:scale = (1,1,1)               # scale NOT mentioned — flows from model
    token visibility = "inherited"                # visibility NOT mentioned — flows through
}                                             }

Composed result:
    translate = (5,0,0)  ← from anim (stronger)
    scale     = (1,1,1)  ← from model (anim has no opinion)
    visibility = "inherited" ← from model (anim has no opinion)
```

This is USD's **non-destructive override** system. The stronger layer is minimal — it only contains what it changes.

```python
from pxr import Usd, Sdf

stage      = Usd.Stage.Open("shot.usda")
anim_layer = Sdf.Layer.FindOrOpen("./anim.usda")

# Switch to the override layer
stage.SetEditTarget(anim_layer)

# Override ONLY translate — nothing else is touched
prim = stage.GetPrimAtPath("/World/Chair")
prim.GetAttribute("xformOp:translate").Set((5, 0, 0))
# anim.usda now contains an 'over "Chair"' with only translate
# model.usda is completely unchanged
```

---

## 4. Flattening — Baking Composition

**Flattening** resolves all composition arcs and produces a single layer containing only the winning values. It is a one-way operation — the original source files are untouched but the composition structure (references, variants, sublayers) is permanently discarded in the output.

```
Before flatten:                    After flatten:
shot.usda                          flat_delivery.usda
├── anim.usda                      (one layer, no arcs)
├── layout.usda                    /World/Chair.translate = (5,0,0)
└── model.usda                     /World/Chair.size = (1,2,1)
    └── ref → chair_asset.usda     ...all winning values baked in
```

### What Flattening Preserves vs Discards

| Preserved | Discarded |
|-----------|-----------|
| ✅ All winning property values | ❌ Composition arcs (references, sublayers) |
| ✅ Animation time samples | ❌ Variant sets (collapsed to selected) |
| ✅ All prim hierarchy | ❌ Layer stack structure |
| ✅ Geometry types | ❌ Payload lazy-loading |

> **Time samples are PRESERVED.** Flattening does NOT bake animation to static values. That is a separate, deliberate operation.

### `stage.Flatten()` vs `UsdUtils.FlattenLayerStack()`

| Method | What it resolves | Returns |
|--------|-----------------|---------|
| `stage.Flatten()` | Everything — sublayers, references, variants, payloads | `SdfLayer` |
| `UsdUtils.FlattenLayerStack(stage)` | Sublayers only — references and variants kept intact | `SdfLayer` |
| `usdcat --flatten` | Same as `stage.Flatten()` | CLI output |

```python
from pxr import Usd, UsdUtils

stage = Usd.Stage.Open("shot.usda")

# Full flatten — resolves EVERYTHING
flat_layer = stage.Flatten()
flat_layer.Export("delivery.usda")   # save flat result to disk
# Original shot.usda and all its layers are completely untouched

# Sublayer-only flatten — references and variants preserved
flat_sublayers = UsdUtils.FlattenLayerStack(stage)
flat_stage = Usd.Stage.Open(flat_sublayers)
# inspect the result...
```

> **Flatten is safe to call for debugging** — `stage.Flatten()` returns a **new** `SdfLayer` object. It never modifies the original stage. Inspect the flat layer and discard it when done. For delivery, call `.Export()` on the result.

---

## 5. Encapsulation — Asset Structure Principles

**Encapsulation** means an asset contains all the prims it needs within its own hierarchy. Nothing reaches outside its root prim to access data from the referencing scene.

### Why It Matters

When an asset is referenced into a scene, only the hierarchy under the referenced prim is brought in. If the asset has prims outside that hierarchy — like a material at `/Looks/WoodMat` while the geometry is at `/Chair` — the material is not brought in with the reference.

```
❌ Unencapsulated asset (broken):
/Chair                    ← referenced in
  /seat_geo  (Mesh)       ✅ brought in
/Looks                    ← NOT brought in (outside /Chair)
  /WoodMat   (Material)   ← geometry can't find its material!

✅ Encapsulated asset (correct):
/Chair                    ← referenced in
  /seat_geo  (Mesh)       ✅ brought in
  /Looks                  ✅ brought in (inside /Chair)
    /WoodMat (Material)   ✅ found correctly
```

### Asset Structure Rules

1. **Set `defaultPrim`** — every published asset must have a `defaultPrim` set to its root prim
2. **Keep materials inside the asset root** — `/Asset/Looks/` not `/Looks/` at the root
3. **Use relative paths** — `./textures/wood.png` not `C:/studio/textures/wood.png`
4. **One root prim** — the `defaultPrim` is the single entry point for references

---

## 6. Change Processing and SdfChangeBlock

USD sends **change notifications** whenever the stage is modified. Listeners (e.g., Hydra, viewport updates) receive these notifications and update only the parts of the scene that changed. This is far more efficient than a full scene re-evaluation on every edit.

### SdfChangeBlock — Batching Notifications

`Sdf.ChangeBlock` defers all change notifications until the block exits, then sends one consolidated notification. This is critical for performance when making many edits in a loop.

```python
from pxr import Usd, Sdf

stage = Usd.Stage.Open("scene.usda")
attr  = stage.GetPrimAtPath("/World/Mesh").GetAttribute("points")

# Without ChangeBlock: 10,000 individual notifications
for i in range(10000):
    attr.Set(new_points[i], time=i)    # 10,000 notifications sent

# With ChangeBlock: ONE consolidated notification
with Sdf.ChangeBlock():
    for i in range(10000):
        attr.Set(new_points[i], time=i)
# ONE notification sent after the block exits — ~10,000× faster
```

### Stage Caching — `Usd.StageCache`

Opening a stage is expensive — it reads all layers and runs composition. `UsdStageCache` stores previously opened stages so they can be reused without re-opening.

```python
from pxr import Usd

cache = Usd.StageCache()

with Usd.StageCacheContext(cache):
    # First open — reads from disk and runs composition
    stage = Usd.Stage.Open("scene.usda")
    
    # Second open of the SAME file — returns cached stage instantly
    stage2 = Usd.Stage.Open("scene.usda")
    assert stage is stage2  # same object
```

---

## 7. Full Composition Mental Model

When USD composes a prim, it collects all **PrimSpecs** from every layer that has an opinion on that prim, orders them by LIVERPS strength, and merges the winning values:

```
1. Collect all PrimSpecs for /World/Chair across all layers
   (from sublayers, references, inherits, variants, specializes)

2. Order by LIVERPS strength:
   [Local opinions in root layer]           strength 1
   [Inherited from class prim]              strength 2
   [Active variant content]                 strength 3
   [Referenced asset opinions]              strength 4
   [Payload opinions]                       strength 5
   [Specialized class opinions]             strength 6 (weakest)

3. For each property: take the value from the strongest spec that has an opinion
   If no spec has an opinion → use schema fallback value

4. Result: the composed prim with its final resolved values
```

---

## 8. Key Takeaways

| Concept | What to Remember |
|---------|-----------------|
| **Edit target** | Controls which layer receives all authoring operations |
| **Default edit target** | Root layer — always check before authoring in multi-layer stages |
| **Session layer** | Always strongest. In-memory. Never saved. `stage.GetSessionLayer()` |
| **Sparse override** | `over` spec changes only specific properties. Non-destructive. |
| **`stage.Flatten()`** | Returns new `SdfLayer` with all composition resolved. Never modifies source. |
| **`FlattenLayerStack()`** | Merges sublayers only. References and variants kept intact. |
| **Time samples preserved** | Flattening does NOT bake animation to static values |
| **Variants collapsed** | Flattening collapses variant sets to the currently selected variant |
| **Encapsulation** | Materials and all prims inside the asset root prim. Relative paths. |
| **defaultPrim** | Must be set on every published asset |
| **SdfChangeBlock** | Batch many edits into one notification — critical for performance |
| **UsdStageCache** | Cache open stages to avoid redundant recomposition |

---

*Previous: [Day 3 — Composition Arcs Part 2](day-03-composition-arcs-part-2.md)*  
*Next: [Day 5 — Schemas and Data Modeling](day-05-schemas-and-data-modeling.md)*
