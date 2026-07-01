# Day 2 — Composition Arcs Part 1

> **OpenUSD NCP Certification Study Notes**  
> _Sublayers, References, Payloads, and Value Resolution_

---

## Table of Contents

1. [What is Composition?](#1-what-is-composition)
2. [Opinions and Value Resolution](#2-opinions-and-value-resolution)
3. [LIVERPS — The Strength Order](#3-liverps--the-strength-order)
4. [Sublayers](#4-sublayers)
5. [References](#5-references)
6. [Payloads](#6-payloads)
7. [Layer Offsets and Time Shifting](#7-layer-offsets-and-time-shifting)
8. [Key Takeaways](#8-key-takeaways)

---

## 1. What is Composition?

**Composition** is the process by which USD assembles multiple layers of scene description into one unified, final scene. Instead of a single monolithic file, a USD scene is intentionally split across many files — each owned by a different department or concern — and composed together at runtime.

```
  model.usda        anim.usda        lighting.usda        fx.usda
  (geometry)        (keyframes)      (lights, sky)        (particles)
       │                 │                 │                   │
       └─────────────────┴─────────────────┴───────────────────┘
                                   │
                               shot_042.usda
                               (root layer)
                                   │
                                   ▼
                          ╔══════════════════╗
                          ║  COMPOSED STAGE  ║
                          ║  (in-memory)     ║
                          ╚══════════════════╝
```

The mechanism connecting layers is a **composition arc**. USD defines six arc types, each serving a different purpose. Together they are ordered by strength using the acronym **LIVERPS**.

---

## 2. Opinions and Value Resolution

Every value stored in a layer is called an **opinion**. When multiple layers each have an opinion about the same property on the same prim, USD must choose a winner. This is **value resolution**.

### The Resolution Rule

The **strongest layer** (highest in the layer stack) always wins for the same property. If the strongest layer has no opinion on a property, USD falls through to the next layer, and so on down the stack. If no layer has an opinion, the **schema fallback** (default value defined in the schema) is returned.

```
Layer Stack (strongest → weakest)       Translate on /Robot
───────────────────────────────────      ─────────────────────
[0] anim.usda         STRONGEST          (5, 0, 0)  ← WINS
[1] layout.usda                          (0, 0, 0)
[2] model.usda        WEAKEST            (0, 0, 0)

Composed result: Robot.translate = (5, 0, 0)
```

**Non-destructive overrides:** this system means stronger layers can override weaker ones without modifying them. The weaker layer is untouched — its value is simply not used because a stronger opinion exists.

### Per-Property Resolution

Resolution happens per-property, not per-prim. A stronger layer can override only `translate` while the weaker layer still provides `size`:

```
anim.usda:    over "Robot" { translate = (5,0,0) }   # only translate
model.usda:   def Xform "Robot" { size = (1,2,1), translate = (0,0,0) }

Composed Robot:
  translate = (5,0,0)   ← from anim.usda (stronger)
  size      = (1,2,1)   ← from model.usda (only layer with an opinion)
```

### Python API — Inspecting Value Resolution

```python
from pxr import Usd

stage = Usd.Stage.Open("shot.usda")
prim  = stage.GetPrimAtPath("/World/Robot")
attr  = prim.GetAttribute("xformOp:translate")

# Read the composed (winning) value
value = attr.Get()
print(value)  # (5, 0, 0) — anim layer wins

# Inspect every layer that has an opinion on this attribute
# Signature: attr.GetPropertyStack(timeCode: Usd.TimeCode) -> list[SdfPropertySpec]
# timeCode is REQUIRED — there is no default argument
stack = attr.GetPropertyStack(Usd.TimeCode.Default())
for i, spec in enumerate(stack):
    print(f"[{i}] {spec.layer.identifier}  value={spec.default}")
# [0] anim.usda    value=(5,0,0)   ← winner
# [1] model.usda   value=(0,0,0)

# Check if the value was explicitly authored vs a schema fallback
print(attr.HasAuthoredValue())  # True = explicitly Set(), False = fallback
```

---

## 3. LIVERPS — The Strength Order

When the same prim is contributed by multiple **different sources**, which source's opinion wins? USD resolves this with a fixed priority order remembered by the acronym **LIVERPS**:

```
L — Local          (opinions authored directly in the local layer)
I — Inherit
V — Variant
E — rEference  *note: the 'E' stands for the 'e' in reference
R — (Relocates in older USD literature — ignore for NCP-OUSD)
P — Payload
S — Specializes
```

This order is **fixed and cannot be changed**. Local opinions always beat inherited opinions, which always beat variant opinions, and so on.

| Position      | Source          | Strength    | Notes                                             |
| ------------- | --------------- | ----------- | ------------------------------------------------- |
| 1 (strongest) | **Local**       | Highest     | Direct opinions in the composing layer            |
| 2             | **Inherit**     | High        | Inherited from a class prim via Inherit arc       |
| 3             | **Variant**     | Medium-high | The active variant's opinions                     |
| 4             | **rEference**   | Medium      | Opinions from a referenced file via Reference arc |
| 5             | **Payload**     | Medium-low  | Opinions from a payload arc (deferred loading)    |
| 6 (weakest)   | **Specializes** | Lowest      | Fallback defaults via Specialize arc              |

> **Specializes is the weakest position.** It provides fallback defaults that any other source can override. It does NOT override anything — this is a common exam trap.

### Critical Distinction — Variant is NOT an Arc Type

This is one of the most precise distinctions in USD terminology and directly tested on the exam:

**LIVERPS describes opinion strength** — where in the priority queue a value comes from.  
**Arc types describe composition relationships** — structural edges that connect prims or pull in external data.

These are related but **not the same thing**. Variant occupies a position in LIVERPS but is **not** a composition arc type.

#### The 4 true composition arc types

```
Reference  → prepend references  = @./file.usda@     points to external file
Payload    → prepend payload     = @./heavy.usda@     points to external file (deferred)
Inherit    → prepend inherits    = </_ClassPrim>      points to another prim
Specialize → prepend specializes = </_BasePrim>       points to another prim
```

Every real arc uses a **path or file reference** — it creates a directed edge to something external.

#### Why Variant is different

A variant set lives **entirely within the prim itself**. Selecting a variant does not create a cross-prim connection — it switches which **local block of opinions** is currently active:

```usda
def Xform "Chair" (
    variants = { string color = "red" }   ← no path, no external file
    prepend variantSets = "color"         ← activates a local block
) {
    variantSet "color" = {
        "red"  { color3f[] primvars:displayColor = [(0.8, 0.2, 0.2)] }
        "blue" { color3f[] primvars:displayColor = [(0.2, 0.4, 0.9)] }
    }
}
```

No external file. No other prim referenced. The variant just switches which block of the prim's **own data** is active. That's why it's not a composition arc — it doesn't compose anything from outside.

#### The exam question pattern

| Question asks                                     | Include Variant? |
| ------------------------------------------------- | ---------------- |
| "Which are composition **arc types**?"            | ❌ No            |
| "Which are part of **LIVERPS**?"                  | ✅ Yes           |
| "Which affect **composition strength order**?"    | ✅ Yes           |
| "Which create a **directed edge** between prims?" | ❌ No            |
| "Which **pull in external data**?"                | ❌ No            |

---

## 4. Sublayers

A **sublayer** merges an entire layer's namespace into the compositing layer stack. All prims from the sublayer appear at the same paths — there is no path remapping.

```
shot.usda          anim.usda            Composed result
─────────────      ─────────────        ───────────────
subLayers = [      over "Robot" {       /Robot.translate = (5,0,0)  ← anim wins
  anim.usda,         translate=(5,0,0)  /Robot.size      = (1,2,1)  ← model provides
  model.usda       }
]
                   model.usda
                   def Xform "Robot" {
                     size = (1,2,1)
                     translate = (0,0,0)
                   }
```

### When to Use Sublayers

| ✅ Correct use                                                        | ❌ Wrong use                                                   |
| --------------------------------------------------------------------- | -------------------------------------------------------------- |
| Separating workstreams on the same scene (anim, layout, fx, lighting) | Bringing in an external asset (use Reference)                  |
| Non-destructive overrides on existing prims                           | Adding the same asset multiple times (sublayer = one instance) |
| Department-specific layers in a shot                                  | Heavy geometry you want to load lazily (use Payload)           |

> **Key distinction — Sublayer vs Reference:**  
> Sublayer = merge the whole namespace (same scene, different concerns)  
> Reference = graft one prim from another file at a chosen path (asset reuse)

### USDA Syntax

```usda
#usda 1.0
(
    subLayers = [
        @./anim.usda@,       # FIRST = STRONGEST — wins all conflicts
        @./layout.usda@,     # second strongest
        @./model.usda@       # LAST = WEAKEST
    ]
)
```

### Python API

```python
from pxr import Usd, Sdf

stage      = Usd.Stage.Open("shot.usda")
root_layer = stage.GetRootLayer()

# Inspect current sublayers (index 0 = strongest)
print(root_layer.subLayerPaths)
# ['./anim.usda', './layout.usda', './model.usda']

# Add a sublayer as the WEAKEST (append = last position)
root_layer.subLayerPaths.append("./fx.usda")

# Add a sublayer as the STRONGEST (insert at index 0)
root_layer.subLayerPaths.insert(0, "./director_overrides.usda")

# Iterate all layers in strength order
for layer in stage.GetLayerStack():
    print(layer.identifier)

# Mute a layer for debugging (temporarily removes its contributions)
stage.MuteLayer("./layout.usda")
# When wrong value disappears after muting → that layer is the source
stage.UnmuteLayer("./layout.usda")
```

---

## 5. References

A **Reference** grafts a specific prim from another USD file into your scene at a chosen path. It is the standard mechanism for **asset reuse** — the same chair asset can be referenced in ten different scenes, each scene getting its own copy of the prim hierarchy.

```
scene.usda                      chair_asset.usda
───────────                     ─────────────────
def Xform "World" {             def Xform "Chair" {   ← defaultPrim
  def Xform "ChairA" (              def Mesh "seat_geo" { ... }
    prepend references =            def Mesh "legs_geo" { ... }
      @./chair_asset.usda@      }
  ) { }
}

Composed result:
/World/ChairA/seat_geo
/World/ChairA/legs_geo
```

References **add new prims** to the composing scene — the referenced prim hierarchy appears under the referencing path, even if those paths don't exist in the root layer at all.

### `defaultPrim` — Critical

When you write `@./chair_asset.usda@` with no prim path, USD looks for the `defaultPrim` metadata on the referenced file to know which prim to bring in. If `defaultPrim` is not set, the reference fails.

```python
# On the asset file — always set defaultPrim before publishing
asset_stage = Usd.Stage.Open("chair_asset.usda")
root_prim   = asset_stage.GetPrimAtPath("/Chair")
asset_stage.SetDefaultPrim(root_prim)
asset_stage.Save()
```

### `prepend` and `append` — List Insertion Behaviour

Both keywords control where a new arc is inserted relative to existing arcs of the same type on that prim.

| Keyword   | Equivalent to          | Position      | Strength                    |
| --------- | ---------------------- | ------------- | --------------------------- |
| `prepend` | `list.insert(0, item)` | Front of list | Stronger than existing arcs |
| `append`  | `list.append(item)`    | Back of list  | Weaker than existing arcs   |

**Multiple separate `prepend` lines behave like repeated `insert(0)` calls — the last one written ends up at index 0:**

```usda
prepend references = @./base_geometry.usda@      # insert(0) → ["base_geometry"]
prepend references = @./material_override.usda@  # insert(0) → ["material_override", "base_geometry"]
#                                                               ↑ index 0 — WINS despite being written second
```

This is counterintuitive — the arc written last in the file ends up strongest. Use a single list to make order explicit:

```usda
def Xform "Chair" (
    prepend references = [
        @./material_override.usda@,   # index 0 — strongest
        @./base_geometry.usda@        # index 1 — weaker
    ]
) { }
```

**Mixed prepend and append on the same prim:**
prepend items → fill the front of the list (strongest)

append items → fill the back of the list (weakest)
Final order: [prepend[0], prepend[1], ..., append[0], append[1], ...]

**On a fresh prim with no existing arcs, `prepend` and `append` produce identical results** — the distinction only matters when arcs already exist on the prim.

### Reference Composition Rules

- References are positioned at **E** in LIVERPS — weaker than local, inherit, and variant
- Local opinions on the referencing prim **override** opinions from the reference
- References can point to a specific prim path within the file: `@./asset.usda@</SpecificPrim>`
- Multiple references can be stacked on one prim: `prepend references = [@./a.usda@, @./b.usda@]`

### USDA Syntax

```usda
def Xform "ChairA" (
    prepend references = @./chair_asset.usda@
    # or with explicit target prim:
    # prepend references = @./chair_asset.usda@</Chair>
) {
    # Local opinions here override the reference
    double3 xformOp:translate = (5, 0, 0)
}
```

### Python API

```python
from pxr import Usd, UsdGeom, Sdf

stage = Usd.Stage.CreateNew("scene.usda")
world = UsdGeom.Xform.Define(stage, "/World")

# Define a prim and add a reference to it
chair_a = stage.DefinePrim("/World/ChairA")
chair_a.GetReferences().AddReference("./chair_asset.usda")

# Reference with an explicit target prim path
chair_b = stage.DefinePrim("/World/ChairB")
chair_b.GetReferences().AddReference("./chair_asset.usda", "/Chair")

# Reference with a layer offset (shifts the animation in time)
from pxr import Sdf
ref = Sdf.Reference(
    assetPath  = "./chair_asset.usda",
    primPath   = Sdf.Path("/Chair"),
    layerOffset = Sdf.LayerOffset(offset=100.0, scale=2.0)
)
chair_c = stage.DefinePrim("/World/ChairC")
chair_c.GetReferences().AddReference(ref)
```

---

## 6. Payloads

A **Payload** is structurally identical to a Reference — it grafts a prim from another file — but with one key difference: **payload data is not loaded until explicitly requested**.

This is USD's mechanism for **deferred loading**, enabling large scenes (e.g., a city with thousands of buildings) to be opened quickly, showing only lightweight proxy geometry, while the heavy mesh data loads on demand.

```
scene.usda opens quickly:          After stage.Load("/World/City/BuildingA"):
───────────────────────────        ────────────────────────────────────────
/World/City                        /World/City
  /World/City/BuildingA (empty)      /World/City/BuildingA
  /World/City/BuildingB (empty)        /legs_geo (mesh, fully loaded)
  /World/City/BuildingC (empty)        /walls_geo (mesh, fully loaded)
```

### Explicit prim path vs defaultPrim

When referencing or payloading a file, USD needs to know **which prim inside that file** to bring in. There are two ways to tell it:

**Without explicit path — relies on `defaultPrim`**

```usda
prepend references = @./chair_asset.usda@
prepend payload    = @./chair_asset.usda@
```

USD opens the file and looks for `defaultPrim` in its metadata. If not set — silent failure, empty prim.

**With explicit path — bypasses `defaultPrim` entirely**

```usda
prepend references = @./chair_asset.usda@</Chair>
prepend payload    = @./chair_asset.usda@</Chair>
```

The path after `@` inside `<>` tells USD exactly which prim to target. `defaultPrim` is irrelevant.

### Payload vs Reference

| Property            | Reference               | Payload                        |
| ------------------- | ----------------------- | ------------------------------ |
| Data loaded on open | ✅ Always               | ❌ Only when explicitly loaded |
| LIVERPS position    | E (4th)                 | P (5th, weaker)                |
| Good for            | Assets always needed    | Heavy data, optional content   |
| Typical content     | Props, characters, sets | High-res geometry, caches      |

### Python API

```python
from pxr import Usd, UsdGeom, Sdf

stage = Usd.Stage.Open("scene.usda", Usd.Stage.LoadNone)
# LoadNone = open the stage but don't load ANY payloads
# The stage opens instantly even for gigantic scenes

# Inspect what payloads exist without loading them
for prim in stage.Traverse():
    if prim.HasPayload():
        print(f"Payload available: {prim.GetPath()}")

# Load a specific payload on demand
stage.Load("/World/City/BuildingA")

# Unload it (frees memory, prim becomes empty again)
stage.Unload("/World/City/BuildingA")

# Check if a prim is currently loaded
prim = stage.GetPrimAtPath("/World/City/BuildingA")
print(prim.IsLoaded())   # True or False

# Author a payload in USDA syntax:
def Xform "BuildingA" (
    prepend payload = @./building_a_geo.usda@
) { }
```

### USDA Syntax

```usda
def Xform "BuildingA" (
    prepend payload = @./building_a_geo.usda@
) {
    # This prim is visible on the stage but its children
    # are only populated when explicitly loaded
}
```

> **Exam distinction:** Payloads CREATE a new composition arc (like References). Sublayers do NOT create new arcs — they merge directly into the existing layer stack.

---

## 7. Layer Offsets and Time Shifting

A **layer offset** is attached to a reference or payload arc and applies a time transformation to all time-sampled data from that arc.

The transformation formula is:

```
composed_time = (source_time × scale) + offset
```

### Example

```usda
def Xform "Character" (
    prepend references = @./walk_cycle.usda@ (offset = 100, scale = 2.0)
) { }
```

A keyframe at `source_time = 10` in `walk_cycle.usda` appears at:

```
composed_time = (10 × 2.0) + 100 = 120
```

### Why This Matters for Debugging

If animation appears at the wrong time code, **check the layer offset on the reference arc first**. This is a commonly missed debugging step.

> **Exam trap:** "Ignoring layer offsets as they do not affect composition results" is INCORRECT. Layer offsets directly affect time-varying data composition. They must always be accounted for when debugging animation timing issues.

### Python API

```python
from pxr import Sdf

ref = Sdf.Reference(
    assetPath   = "./walk_cycle.usda",
    primPath    = Sdf.Path("/Character"),
    layerOffset = Sdf.LayerOffset(offset=100.0, scale=2.0)
)
prim.GetReferences().AddReference(ref)
```

---

## 8. Key Takeaways

| Concept                | What to Remember                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Composition**        | USD assembles multiple layers at runtime into one unified stage                                              |
| **Opinion**            | Any value stored in a layer for a specific property                                                          |
| **Value resolution**   | Strongest layer (first in stack) wins per property                                                           |
| **LIVERPS**            | Local → Inherit → Variant → rEference → Payload → Specializes                                                |
| **Variant in LIVERPS** | Describes opinion _strength_ — not an arc type. Variants switch local data blocks, not external connections. |
| **4 arc types**        | Reference, Payload, Inherit, Specialize — these create structural edges to external files or prims           |
| **Variant ≠ arc**      | "Which are arc types?" → exclude Variant. "Which are in LIVERPS?" → include Variant.                         |
| **Specializes**        | Weakest position — provides fallback defaults, does NOT override                                             |
| **Sublayer**           | Merges entire namespace. Same prims, different concerns.                                                     |
| **Reference**          | Grafts one prim from another file at a chosen path. Asset reuse.                                             |
| **Payload**            | Like Reference but deferred — not loaded until `stage.Load()`                                                |
| **defaultPrim**        | Must be set on every published asset for references to work                                                  |
| **Layer offset**       | Applies `composed = source × scale + offset` to all time samples                                             |
| **Non-destructive**    | Stronger layers override without touching weaker ones                                                        |

---

_Previous: [Day 1 — USD Foundations](day-01-usd-foundations.md)_  
_Next: [Day 3 — Composition Arcs Part 2](day-03-composition-arcs-part-2.md)_
