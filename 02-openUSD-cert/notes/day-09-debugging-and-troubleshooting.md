# Day 9 — Debugging and Troubleshooting

> **OpenUSD NCP Certification Study Notes**  
> _PrimStack, PropertyStack, TfDebug, MuteLayer, Flattening, Composition Errors, Schema Versions_

---

## Table of Contents

1. [Debugging Mindset — Root Causes](#1-debugging-mindset--root-causes)
2. [The Complete Debugging Toolkit](#2-the-complete-debugging-toolkit)
3. [PrimStack — Inspecting Prim Contributions](#3-primstack--inspecting-prim-contributions)
4. [PropertyStack — Finding the Winning Layer](#4-propertystack--finding-the-winning-layer)
5. [HasAuthoredValue — Authored vs Schema Fallback](#5-hasauthoredvalue--authored-vs-schema-fallback)
6. [Edit Target — The Most Common Silent Bug](#6-edit-target--the-most-common-silent-bug)
7. [MuteLayer — Systematic Isolation](#7-mutelayer--systematic-isolation)
8. [GetCompositionErrors — Broken References](#8-getcompositionerrors--broken-references)
9. [Flattening as a Debug Tool](#9-flattening-as-a-debug-tool)
10. [Namespace and Path Collision Debugging](#10-namespace-and-path-collision-debugging)
11. [TfDebug — Verbose Internal Logging](#11-tfdebug--verbose-internal-logging)
12. [Composition Arc Inspection](#12-composition-arc-inspection)
13. [Schema Version Validation](#13-schema-version-validation)
14. [Layer Offsets and Animation Timing](#14-layer-offsets-and-animation-timing)
15. [usdview Debugging Panels](#15-usdview-debugging-panels)
16. [Common Bugs Reference](#16-common-bugs-reference)
17. [Exam Trap Elimination Guide](#17-exam-trap-elimination-guide)

---

## 1. Debugging Mindset — Root Causes

Almost every USD debugging scenario comes down to one of six root causes:

| Root Cause                          | Symptom                                      | Primary Tool                               |
| ----------------------------------- | -------------------------------------------- | ------------------------------------------ |
| **Wrong value winning**             | Property shows incorrect value               | `GetPropertyStack()`                       |
| **Wrong structure / missing prims** | Prims missing despite being in source        | `GetPrimStack()`, composition tab          |
| **Wrong edit target**               | Value authored but file looks unchanged      | Check `GetEditTarget()`                    |
| **Composition arc conflict**        | Unexpected overrides or missing data         | `GetCompositionErrors()`, PrintComposition |
| **Schema version mismatch**         | Unexpected attribute behaviour across layers | Inspect `customLayerData`, `usdchecker`    |
| **Performance / loading**           | Slow stage open, viewport lag                | `TfDebug`, check payload loading           |

> **Most reliable symptom of poor authoring (invalid references or namespace issues):** prims that are missing from the stage despite being present in source layers. This directly indicates broken composition arcs — either invalid references, missing `defaultPrim`, or namespace collisions.

---

## 2. The Complete Debugging Toolkit

| Tool / Method                        | What It Does                                             | When to Use                                         |
| ------------------------------------ | -------------------------------------------------------- | --------------------------------------------------- |
| `prim.GetPrimStack()`                | All SdfPrimSpecs for a prim, strongest → weakest         | Wrong prim type, missing prim, unexpected specifier |
| `attr.GetPropertyStack(timeCode)`    | All property specs for an attribute, strongest → weakest | Wrong property value                                |
| `Usd.Debug.PrintComposition(prim)`   | Full composition arc breakdown as text                   | Most detailed arc debugging (source builds only)    |
| `prim.GetPrimIndex().DumpToString()` | Full composition graph as text                           | Same as above — works in all USD builds             |
| `UsdUtils.FlattenLayerStack(stage)`  | Merges sublayers only — references/variants kept         | Debug sublayer conflicts                            |
| `stage.Flatten()`                    | Resolves ALL arcs — full composed scene                  | See what the final scene actually looks like        |
| `usdcat --flatten`                   | CLI equivalent of `stage.Flatten()`                      | Quick CLI inspection                                |
| `usdcat --print-composition`         | CLI composition arc graph                                | CLI alternative to PrintComposition                 |
| `stage.GetLayerStack()`              | All layers, strongest → weakest                          | Understanding which layers are loaded               |
| `stage.GetRootLayer()`               | The root layer before composition                        | Examining base scene description                    |
| `stage.GetSessionLayer()`            | Ephemeral in-memory overrides                            | Checking interactive changes                        |
| `stage.MuteLayer(id)`                | Silences a layer without removing it                     | Isolating which layer causes a problem              |
| `stage.GetCompositionErrors()`       | All composition errors on the stage                      | Broken references, invalid paths                    |
| `usdchecker scene.usda`              | Validates file against best practices                    | Pre-delivery QA                                     |
| `Tf.Debug.SetDebugSymbolsByName()`   | Enables verbose internal logging                         | Stage open issues, path resolution                  |

---

## 3. PrimStack — Inspecting Prim Contributions

`prim.GetPrimStack()` returns a list of `SdfPrimSpec` objects — one per layer that has any contribution to this prim's existence or type. Results are ordered **strongest → weakest**.

### Function Signature

```
prim.GetPrimStack() → list[SdfPrimSpec]
```

- **Called on:** a prim (`Usd.Prim`)
- **Parameters:** **none** — takes no arguments at all
- **Why no TimeCode:** prims either exist in a layer or they don't. There is no "at what time does this prim exist" concept — prim existence is time-independent.

### `SdfPrimSpec` Fields

| Field                    | Type            | Description                                                   |
| ------------------------ | --------------- | ------------------------------------------------------------- |
| `spec.layer`             | `SdfLayer`      | The layer object containing this spec                         |
| `spec.layer.identifier`  | `str`           | File path of that layer                                       |
| `spec.specifier`         | `Sdf.Specifier` | `Sdf.SpecifierDef`, `Sdf.SpecifierOver`, `Sdf.SpecifierClass` |
| `spec.typeName`          | `str`           | Type like `"Xform"`, `"Mesh"`, or `""` for `over`             |
| `spec.path`              | `Sdf.Path`      | The prim path                                                 |
| `spec.attributes.keys()` | `list[str]`     | All attribute names this layer authored on this prim          |

### Python API

```python
from pxr import Usd
import os

stage = Usd.Stage.Open("scene.usda")
prim  = stage.GetPrimAtPath("/World/Chair")

# GetPrimStack — no parameters
for i, spec in enumerate(prim.GetPrimStack()):
    layer_name = os.path.basename(spec.layer.identifier)
    print(f"[{i}] {layer_name}")
    print(f"     specifier: {spec.specifier}")   # def / over / class
    print(f"     typeName:  '{spec.typeName}'")  # "Xform", "Mesh", ""
    # Index 0 = strongest spec
```

### What to Look For

| Observation                                   | Meaning                                                     |
| --------------------------------------------- | ----------------------------------------------------------- |
| Two unrelated asset layers in the stack       | Namespace collision — two assets defining the same path     |
| `specifier=over`, `typeName=''` at index 0    | Sparse override — this layer doesn't own the prim           |
| `specifier=def`, `typeName='Mesh'` at index 0 | This layer owns the prim and its type                       |
| Only `over` specs, no `def` spec              | Prim is not truly defined — `IsDefined()` will return False |

---

## 4. PropertyStack — Finding the Winning Layer

`attr.GetPropertyStack(timeCode)` returns a list of `SdfPropertySpec` objects — one per layer that has an opinion on this specific attribute at the given time. Results are ordered **strongest → weakest**.

### Function Signature

```
attr.GetPropertyStack(timeCode: Usd.TimeCode) -> list[SdfPropertySpec]
```

- **Called on:** a specific attribute (`Usd.Attribute`) — you must call `prim.GetAttribute("name")` first
- **Parameter:** `timeCode` — **REQUIRED**. There is no default. Omitting it raises `TypeError`.
- **Returns:** all layers with an opinion on this attribute at `timeCode`, ordered strongest → weakest

### TimeCode Parameter — Critical Distinction

| Expression                 | Meaning                                                                                |
| -------------------------- | -------------------------------------------------------------------------------------- |
| `Usd.TimeCode.Default()`   | The **plain authored default** — no time association. Use for non-animated attributes. |
| `Usd.TimeCode(24)` or `24` | The value **at frame 24**. Use for animated attributes.                                |
| `Usd.TimeCode(0)` or `0`   | The value **at frame 0** — a real point in time. **NOT the same as `Default()`**       |

`TimeCode.Default()` has no numeric shorthand — it must always be written in full. `0` means frame 0, which is distinct from the default value.

### `SdfPropertySpec` Fields

| Field                         | Description                                          |
| ----------------------------- | ---------------------------------------------------- |
| `spec.layer`                  | The `SdfLayer` object                                |
| `spec.layer.identifier`       | File path of the layer                               |
| `spec.default`                | The plain authored value (None if time-sampled only) |
| `spec.GetInfo("timeSamples")` | `{frame: value}` dict for time-sampled attrs         |
| `spec.typeName`               | Value type (e.g., `"Float"`, `"Double3"`)            |

### Python API

```python
from pxr import Usd
import os

prim  = stage.GetPrimAtPath("/World/Chair")
attr  = prim.GetAttribute("chair:brightness")

# Non-animated attribute — use TimeCode.Default()
stack = attr.GetPropertyStack(Usd.TimeCode.Default())

print(f"Number of specs: {len(stack)}")
for i, spec in enumerate(stack):
    layer_name = os.path.basename(spec.layer.identifier)
    note = "<── WINNER" if i == 0 else ""

    # spec.default = plain value. None if time-sampled.
    value = spec.default
    if value is None:
        ts = spec.GetInfo("timeSamples")
        value = ts  # {frame: value} dict

    print(f"[{i}] {layer_name:<35} value={value} {note}")

# Animated attribute — use a specific frame
stack_animated = attr.GetPropertyStack(Usd.TimeCode(24))
# Only layers that have an opinion at frame 24 appear in this stack
```

---

## 5. HasAuthoredValue — Authored vs Schema Fallback

`attr.HasAuthoredValue()` returns `True` if any layer explicitly called `Set()` on this attribute, and `False` if the value you see from `Get()` is only the schema fallback default.

```python
attr = sphere.GetRadiusAttr()

# Both return 1.0 from Get()
# but only one was explicitly Set():
print(attr.Get())              # 1.0 (either way)
print(attr.HasAuthoredValue()) # True = explicitly Set()  False = schema fallback

# Critical use case: "is this 0.0 because someone set it to 0,
# or is 0.0 just the schema default?"
# Get() cannot distinguish these — HasAuthoredValue() can.
```

---

## 6. Edit Target — The Most Common Silent Bug

When you author a value on the wrong edit target:

- No error is raised
- The value is written successfully — to the wrong layer
- The wrong layer may not be visible in the composed result you're examining

```python
stage = Usd.Stage.Open("shot.usda")
# Default edit target = root layer (shot.usda)

# THE BUG: forgot to switch edit target before authoring
prim.GetAttribute("xformOp:translate").Set((5, 0, 0))
# → went to shot.usda (root), not anim.usda

# DETECT: always check before authoring
current = stage.GetEditTarget().GetLayer()
print(f"Writing to: {current.identifier}")

# FIX: save previous target, set correct one, restore
previous = stage.GetEditTarget()
stage.SetEditTarget(anim_layer)
prim.GetAttribute("xformOp:translate").Set((5, 0, 0))
stage.SetEditTarget(previous)  # restore
```

### Session Layer Trap

`stage.GetSessionLayer().Clear()` clears USD's **built-in** session layer. This is different from a sublayer you happen to name `"session.usda"`. The built-in session layer is what usdview's interactive edits go to — and it is **never saved to disk** by `stage.Save()`.

---

## 7. MuteLayer — Systematic Isolation

When a property has the wrong value and you don't know which layer is responsible, mute each candidate layer one at a time. When the wrong value disappears, that layer is the culprit.

```python
candidates = [layer_fx, layer_director, layer_layout]

for layer in candidates:
    stage.MuteLayer(layer.identifier)
    val = attr.Get()

    if val_is_correct(val):
        print(f"CULPRIT: {layer.identifier}")
        # This layer was causing the wrong value

    stage.UnmuteLayer(layer.identifier)  # always restore before trying next

# API reference
stage.GetMutedLayers()           # list of currently muted layer identifiers
stage.IsLayerMuted(identifier)   # True/False
```

### Muting Rules

| Safe to mute      | Never mute                                                  |
| ----------------- | ----------------------------------------------------------- |
| Any sublayer      | Root layer of a referenced asset — causes composition error |
| The session layer | —                                                           |
| Any payload layer | —                                                           |

> Muting the **root layer of a reference** causes a composition error — USD treats it as if the referenced file doesn't exist at all.

---

## 8. GetCompositionErrors — Broken References

```python
stage = Usd.Stage.Open("scene.usda")

# Get all composition errors
errors = stage.GetCompositionErrors()
print(f"Total errors: {len(errors)}")

for err in errors:
    print(str(err))

# Common error types:
# PcpErrorType_InvalidAssetPath   → file not found
# PcpErrorType_InvalidPrimPath    → file found but prim path doesn't exist
#                                   (usually: defaultPrim not set on asset)
# PcpErrorType_ArcCycle           → circular reference A→B→A
```

| Error Type         | Cause                               | Fix                                       |
| ------------------ | ----------------------------------- | ----------------------------------------- |
| `InvalidAssetPath` | Referenced file doesn't exist       | Ensure file exists at the relative path   |
| `InvalidPrimPath`  | File found, prim path doesn't exist | Set `defaultPrim` on the referenced asset |
| `ArcCycle`         | A references B which references A   | Break the circular dependency             |

---

## 9. Flattening as a Debug Tool

Flattening creates a temporary snapshot for inspection. The original stage is **never modified**.

```python
from pxr import Usd, UsdUtils

stage = Usd.Stage.Open("scene.usda")

# FlattenLayerStack — sublayers only, references and variants preserved
flat_layer = UsdUtils.FlattenLayerStack(stage)
flat_stage_a = Usd.Stage.Open(flat_layer)
# Inspect sublayer conflicts here
# Discard when done — original stage untouched

# stage.Flatten() — resolves EVERYTHING
flat_layer_full = stage.Flatten()
flat_stage_b = Usd.Stage.Open(flat_layer_full)
# Inspect fully composed scene here
# Discard when done — original stage untouched

# For delivery (not just debugging): save to disk
flat_layer_full.Export("delivery.usda")
```

### FlattenLayerStack vs stage.Flatten()

| Feature                | `UsdUtils.FlattenLayerStack()` | `stage.Flatten()`             |
| ---------------------- | ------------------------------ | ----------------------------- |
| Sublayers merged       | ✅ Yes                         | ✅ Yes                        |
| References resolved    | ❌ No — kept as-is             | ✅ Yes                        |
| Variants preserved     | ✅ Yes                         | ❌ No — collapsed to selected |
| Time samples preserved | ✅ Yes                         | ✅ Yes                        |
| Use for                | Debug sublayer conflicts       | See fully composed scene      |

---

## 10. Namespace and Path Collision Debugging

A namespace collision occurs when two unrelated assets both define a prim at the same path in the same layer stack. The stronger layer wins silently — no error is raised.

```python
# SYMPTOM: wrong attributes on a prim, or data from one asset
# appearing on what should be a different prim

# DETECT using GetPrimStack
for spec in prim.GetPrimStack():
    print(spec.layer.identifier)
# RED FLAG: two unrelated asset layers both appearing for one prim

# FIX: reference each asset at a DIFFERENT namespace path
# Instead of: /World/Chair (both assets land here)
# Use:        /World/OfficeArea/Chair   ← from office_chair.usda
#             /World/DiningArea/Chair   ← from dining_chair.usda
```

### Path Case Sensitivity

USD paths are **case-sensitive**:

```python
stage.GetPrimAtPath("/World/Chair").IsValid()   # True
stage.GetPrimAtPath("/World/chair").IsValid()   # False — different path!
```

An override targeting `/World/chair` will never apply to `/World/Chair`. This is one of the most subtle and common path mismatch bugs.

---

## 11. TfDebug — Verbose Internal Logging

`Tf.Debug` enables verbose logging from USD's internal subsystems. Output goes to stderr.

```python
from pxr import Tf

# Enable a debug symbol before opening the stage
Tf.Debug.SetDebugSymbolsByName("USD_STAGE_OPEN", True)
stage = Usd.Stage.Open("scene.usda")   # verbose output printed to stderr
Tf.Debug.SetDebugSymbolsByName("USD_STAGE_OPEN", False)

# List all available symbols
all_symbols = Tf.Debug.GetDebugSymbolNames()

# Check if a symbol is enabled
Tf.Debug.IsDebugSymbolNameEnabled("USD_COMPOSITION")  # True/False
```

### Key Debug Symbols

| Symbol             | Use when                                          |
| ------------------ | ------------------------------------------------- |
| `USD_STAGE_OPEN`   | Stage opens but prims are wrong or missing        |
| `USD_COMPOSITION`  | Reference or variant not resolving as expected    |
| `AR_RESOLVER_INIT` | Asset path fails to resolve to a file             |
| `USD_PAYLOADS`     | Payload geometry not appearing                    |
| `USD_CHANGES`      | Too many change notifications — performance issue |
| `USD_INSTANCING`   | Instancing not sharing prototypes correctly       |

### CLI Alternative

```bash
# Windows
set TF_DEBUG=USD_STAGE_OPEN AR_RESOLVER_INIT

# Linux / macOS
export TF_DEBUG=USD_STAGE_OPEN AR_RESOLVER_INIT

# Wildcard — enables ALL USD_ symbols at once
set TF_DEBUG=USD*
```

---

## 12. Composition Arc Inspection

### `prim.GetPrimIndex().DumpToString()`

Works in **all** USD builds including `pip install usd-core`:

```python
index = prim.GetPrimIndex()
dump  = index.DumpToString()
print(dump)
# Shows full composition arc graph:
# "root node" = local opinions (strongest)
# "reference" = reference arc and its contributing layers
# "inherit"   = inherit arc
# Error annotations for broken arcs
```

### `Usd.Debug.PrintComposition(prim)`

Available in **full source builds only** — raises `AttributeError` in `pip install usd-core`:

```python
# Check availability before using
if hasattr(Usd, 'Debug') and hasattr(Usd.Debug, 'PrintComposition'):
    Usd.Debug.PrintComposition(prim)
else:
    # Use DumpToString instead — always available
    print(prim.GetPrimIndex().DumpToString())
```

### Availability Summary

| Method                               | pip usd-core        | Source build | CLI |
| ------------------------------------ | ------------------- | ------------ | --- |
| `prim.GetPrimIndex().DumpToString()` | ✅                  | ✅           | —   |
| `Usd.Debug.PrintComposition(prim)`   | ❌ `AttributeError` | ✅           | —   |
| `usdcat --print-composition`         | ✅                  | ✅           | ✅  |

---

## 13. Schema Version Validation

When layers authored with different schema versions are composed together, attribute names may differ between versions — causing subtle composition failures where two opinions exist for the same concept but with different names.

```
old_layer (v1.0):  "shader:roughness" = 0.3
new_layer (v2.0):  "inputs:roughness" = 0.5

Composed result: BOTH attributes exist on the prim simultaneously
The renderer uses "inputs:roughness" = 0.5
The old "shader:roughness" = 0.3 has no effect — silently wrong
```

### Prevention — Tag Every Layer with Version Metadata

```python
# When authoring any layer
stage.GetRootLayer().customLayerData = {
    "pipeline:schemaVersion": "2.0",
    "pipeline:studio":        "AcmeStudios",
    "pipeline:exportTool":    "MayaExporter_v2",
}

# When reading layers to validate compatibility
for layer in stage.GetLayerStack():
    custom  = layer.customLayerData   # returns {} if not set
    version = custom.get("pipeline:schemaVersion", "NOT SET")
    print(f"{layer.identifier}: version={version}")
    # "NOT SET" = old layer predating version tagging
    # → inspect attribute names manually for old naming conventions
```

> `customLayerData` is a plain Python dict stored in the layer's metadata header. Use `.get(key, default)` to safely read it — never raises `KeyError` on old layers that have no metadata.

---

## 14. Layer Offsets and Animation Timing

Layer offsets apply a time transformation to all time-sampled data from a reference or payload arc.

```
composed_time = (source_time × scale) + offset
```

```python
# Reference with offset=100, scale=2.0
# Source keyframe at time=10 appears at:
# composed = (10 × 2.0) + 100 = 120

ref = Sdf.Reference(
    assetPath   = "./walk_cycle.usda",
    primPath    = Sdf.Path("/Character"),
    layerOffset = Sdf.LayerOffset(offset=100.0, scale=2.0)
)
```

> **If animation appears at the wrong time code — check layer offsets first.** This is a frequently missed debugging step. "Ignoring layer offsets as they do not affect composition results" is **WRONG** — layer offsets directly affect all time-varying data.

---

## 15. usdview Debugging Panels

### Composition Tab

`Metadata/Composition panel → Composition tab` shows the full composition arc graph for the selected prim — the visual equivalent of `prim.GetPrimIndex().DumpToString()`. Use this to understand what arcs contributed and in what order.

### LayerStack Tab

`Metadata/Composition panel → LayerStack tab` shows all layers contributing to the selected prim with their authored values for each property. This is the visual equivalent of `GetPropertyStack()` — the strongest layer appears first.

### Layers Panel

`View → Layers` (or `Windows → Layers` depending on USD version) lists all layers in the stage. Untick/mute a layer interactively and watch property values update live in the Properties panel. Visual equivalent of `stage.MuteLayer()`.

### Properties Panel

Click any property in the Properties panel:

- **Greyed/muted value** = schema fallback — nobody called `Set()` on this attribute
- **Normal/bright value** = explicitly authored value

This is the visual equivalent of `HasAuthoredValue()`.

---

## 16. Common Bugs Reference

| Bug                            | Symptom                                      | Fix                                                    |
| ------------------------------ | -------------------------------------------- | ------------------------------------------------------ |
| Wrong edit target              | Value authored but file unchanged. No error. | Check `GetEditTarget()` before every Set()             |
| Missing defaultPrim            | Reference fails, prim is empty               | `stage.SetDefaultPrim(root_prim)`                      |
| Session layer not saved        | Value reverts on next open                   | SetEditTarget to a file-backed layer                   |
| `CreateNew()` on existing file | Output file has only `#usda 1.0`             | Delete file first, or use `CreateInMemory()` + Export  |
| Namespace collision            | Wrong attributes on a prim                   | Use unique paths per asset                             |
| Path case mismatch             | Override never applies                       | Match case exactly — `/World/Chair` not `/World/chair` |
| Schema version mismatch        | Duplicate attributes, wrong values           | Tag layers with `customLayerData` version info         |
| Layer offset ignored           | Animation at wrong time code                 | Check `Sdf.LayerOffset` on reference arc               |

---

## 17. Exam Trap Elimination Guide

Eliminate any option that contains these patterns:

| Pattern in option                                                | Always wrong because                                        |
| ---------------------------------------------------------------- | ----------------------------------------------------------- |
| "Directly editing the composed stage's in-memory representation" | Composed stage is READ-ONLY                                 |
| "Clear the USD cache to reset composition"                       | USD composition is deterministic — cache = performance only |
| "Manually edit root layer to remove all references"              | Destructive, doesn't address root cause                     |
| "Delete all payloads and reload"                                 | Destructive, doesn't fix composition conflicts              |
| "Modify the USD schema to force specific opinions"               | Schemas define structure, not composition behaviour         |
| "Ignore layer offsets as they don't affect composition"          | Layer offsets DO affect time-varying data                   |
| "usdchecker automatically fixes composition issues"              | usdchecker VALIDATES only — never auto-fixes                |
| "Rely solely on GetSessionLayer() for all composition debugging" | Session layer only contains ephemeral overrides             |
| "Flatten the stage to minimize layer composition overhead"       | Flattening INCREASES memory and removes layering benefits   |
| "GetPrimAtPath() retrieves prims ignoring composition arcs"      | Returns the FULLY COMPOSED prim — all arcs already applied  |

---

_Previous: [Day 8 — Content Aggregation](day-08-content-aggregation.md)_  
_Next: [Day 9 — Debugging and Troubleshooting](day-09-debugging-and-troubleshooting.md)_
