# Day 7 — Pipeline Development and Data Exchange

> **OpenUSD NCP Certification Study Notes**  
> *File Formats, Exporters, Importers, Validators, Data Exchange, Pipeline Tools*

---

## Table of Contents

1. [USD File Format Trade-offs](#1-usd-file-format-trade-offs)
2. [Command-Line Tools](#2-command-line-tools)
3. [Stage Traversal](#3-stage-traversal)
4. [Writing a USD Exporter](#4-writing-a-usd-exporter)
5. [Asset Validators — usdchecker](#5-asset-validators--usdchecker)
6. [Exporter Hooks — Pre/Post Export](#6-exporter-hooks--prepost-export)
7. [Removing Proprietary Dependencies](#7-removing-proprietary-dependencies)
8. [Pipeline Documentation Standards](#8-pipeline-documentation-standards)
9. [Flattening Best Practices](#9-flattening-best-practices)
10. [UI/UX for USD Pipelines](#10-uiux-for-usd-pipelines)
11. [Build Configuration Management](#11-build-configuration-management)
12. [Pipeline Design Principles](#12-pipeline-design-principles)
13. [Conceptual Data Mapping Documents](#13-conceptual-data-mapping-documents)
14. [Custom Importers — Intermediate Representation Pattern](#14-custom-importers--intermediate-representation-pattern)
15. [Data Interchange Script Best Practices](#15-data-interchange-script-best-practices)
16. [Key Takeaways](#16-key-takeaways)

---

## 1. USD File Format Trade-offs

| Extension | Format | Readable | Speed | Self-contained | Best for |
|-----------|--------|----------|-------|----------------|---------|
| `.usda` | ASCII text | ✅ Yes | Slow | ❌ No | Authoring, debugging, version control |
| `.usdc` | Binary crate | ❌ No | Very fast | ❌ No | Production pipelines, large data |
| `.usd` | Auto-detected | Depends | Depends | ❌ No | Generic — USD reads header to determine format |
| `.usdz` | Zip archive | ❌ No | Fast | ✅ Yes | External delivery, AR/VR distribution |

### Renaming Rules

Renaming `.usda` → `.usd` is **valid** — USD detects ASCII content from the file header.  
Renaming `.usda` → `.usdc` is **invalid** — these have completely different internal binary formats.

---

## 2. Command-Line Tools

### `usdcat` — Format Conversion and Inspection

```bash
# Convert ASCII to binary
usdcat scene.usda -o scene.usdc

# Flatten ALL composition into a single file
usdcat --flatten scene.usda -o flat.usda

# Print composition arc graph for all prims
usdcat --print-composition scene.usda
```

### `usdzip` — Package .usdz Archives

```bash
# Package a USD file and ALL its dependencies into .usdz
usdzip -r delivery.usdz scene.usda

# List contents without extracting
usdzip -l delivery.usdz
```

> `usdcat` handles format conversion and flattening. `usdzip` handles `.usdz` packaging. These are separate tools for separate purposes.

### `usdchecker` — Asset Validation

```bash
# Validate a USD file against best practices
usdchecker scene.usda

# Validate a .usdz package
usdchecker delivery.usdz
```

`usdchecker` **validates** — it does NOT automatically fix issues.

### `usddiff` — Compare Two USD Files

```bash
usddiff scene_v1.usda scene_v2.usda
```

---

## 3. Stage Traversal

`stage.Traverse()` visits all prims in the scene graph in depth-first order. Predicates filter the traversal.

```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.Open("scene.usda")

# Traverse ALL active, defined prims
for prim in stage.Traverse():
    print(prim.GetPath(), prim.GetTypeName())

# Traverse only loaded prims (excludes unloaded payloads)
predicate = Usd.TraverseInstanceProxies(
    Usd.PrimIsActive & Usd.PrimIsDefined & Usd.PrimIsLoaded
)
for prim in stage.TraverseAll():
    if predicate(prim):
        print(prim.GetPath())

# Find all meshes
for prim in stage.Traverse():
    if prim.IsA(UsdGeom.Mesh):
        mesh = UsdGeom.Mesh(prim)
        print(f"Mesh found: {prim.GetPath()}")
```

---

## 4. Writing a USD Exporter

A USD exporter translates data from a proprietary format into USD scene description. The correct approach uses the USD API — never hand-writes ASCII.

### Exporter Pattern

```python
from pxr import Usd, UsdGeom, UsdShade, Sdf, Vt, Gf

def export_scene(source_data: dict, output_path: str):
    # 1. Create the stage
    stage = Usd.Stage.CreateNew(output_path)

    # 2. Set stage metadata — always set these
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    stage.SetMetadata("timeCodesPerSecond", 24)

    # 3. Create root prim and set as defaultPrim
    root = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(root.GetPrim())

    # 4. Export geometry using USD API (not hand-written ASCII)
    for mesh_data in source_data["meshes"]:
        mesh = UsdGeom.Mesh.Define(stage, f"/World/{mesh_data['name']}")
        mesh.GetPointsAttr().Set(Vt.Vec3fArray(mesh_data["points"]))
        mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray(mesh_data["face_counts"]))
        mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(mesh_data["indices"]))

    # 5. Export animation using time samples
    for frame, transform in source_data["animation"].items():
        prim.GetAttribute("xformOp:translate").Set(
            Gf.Vec3d(*transform), time=frame
        )

    # 6. Save
    stage.Save()
```

### Key Exporter Rules

| ✅ Do | ❌ Don't |
|-------|---------|
| Use USD Python API to create UsdPrims with schemas | Write raw USD ASCII by hand |
| Use relative paths for all references | Use absolute paths |
| Set `defaultPrim` on the root prim | Leave `defaultPrim` unset |
| Use time samples for animated data | Use only default values for animation |
| Use registered schemas or metadata for proprietary data | Embed unregistered string blobs |
| Use USD's layering model | Flatten everything into one file |

---

## 5. Asset Validators — usdchecker

`usdchecker` validates a USD file or package against a defined set of rules designed to ensure the asset is **interoperable and renderable** by downstream tools.

Common things `usdchecker` validates:
- `defaultPrim` is set
- All meshes have an `extent` attribute
- All material bindings resolve to valid prims
- Referenced files exist and are accessible
- Schema version compatibility
- `.usdz` package completeness

```python
# Programmatic validation using UsdUtils
from pxr import UsdUtils

errors = UsdUtils.ComplianceChecker.GetErrors(stage)
for error in errors:
    print(error)
```

> `usdchecker` validates but does NOT auto-fix. It is used as a pre-delivery QA tool, not a repair tool.

---

## 6. Exporter Hooks — Pre/Post Export

Exporter hooks are **extension points** in the export workflow where custom logic can be injected **without modifying the core exporter code**. This follows the same principle as schema inheritance: extend, never override.

```
Core exporter logic:
  pre_export_hook()   ← inject custom logic BEFORE
  [core export runs]
  post_export_hook()  ← inject custom logic AFTER
```

### Pre-Export Hook

Runs before the core export. Use to:
- Validate source data
- Set stage metadata (upAxis, metersPerUnit)
- Add pipeline version metadata to the root layer

### Post-Export Hook

Runs after the core export. Use to:
- Add custom schema attributes to exported prims
- Run `usdchecker` on the output
- Register the exported asset in the pipeline database

```python
def pre_export_hook(stage, export_options):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.GetRootLayer().customLayerData = {
        "pipeline:version": "2.1",
        "pipeline:studio": "AcmeStudios",
    }

def post_export_hook(stage, exported_path):
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            prim.CreateAttribute(
                "pipeline:exportVersion",
                Sdf.ValueTypeNames.String
            ).Set("2.1")
    # Run validation
    # Register with asset database
```

### Wrong Approaches

| Wrong approach | Why |
|----------------|-----|
| Override the main export function | Loses all built-in functionality — hooks exist to avoid this |
| Modify USD files on disk after export | Error-prone, bypasses pipeline control, risk of corruption |
| Create a separate generator for custom requirements | Duplicates effort, breaks pipeline consistency |

---

## 7. Removing Proprietary Dependencies

Proprietary shaders and plugins in USD assets create vendor lock-in — assets can only be used in tools that support the proprietary technology.

### The Correct Approach

Refactor proprietary shaders into **USD native schemas and shader definitions** (UsdPreviewSurface or MaterialX).

```
Before (proprietary — Arnold only):
  def Shader "Mat" {
      uniform token info:id = "ArnoldStandardSurface"
      float inputs:base = 0.8
  }

After (USD native — any renderer):
  def Shader "Mat" {
      uniform token info:id = "UsdPreviewSurface"
      color3f inputs:diffuseColor = (0.8, 0.8, 0.8)
      float inputs:roughness = 0.3
  }
```

### Wrong Approaches

| Wrong approach | Why |
|----------------|-----|
| Replace USD with proprietary formats | Increases dependency, defeats USD's purpose |
| Reference proprietary files without converting | Dependency still exists |
| Encapsulate without converting | Long-term maintenance problem, dependency still present |

---

## 8. Pipeline Documentation Standards

Good USD pipeline documentation must include enough technical detail for developers to implement and maintain the pipeline.

### Required Contents

- USD **schema types** at each pipeline node
- **Stage layering structure** — which layers compose how
- **Data flow** between nodes — what enters and exits each stage
- **Composition arc annotations** — which arcs connect which assets
- **Dependency mapping** — explicit list of what each stage depends on

### What's Insufficient

- Generic block diagrams without USD-specific detail
- Code snippets only without visual diagrams
- High-level business flowcharts for technical work

---

## 9. Flattening Best Practices

| Action | Part of flattening? | Notes |
|--------|--------------------|----|
| Resolve references and payloads into one file | ✅ Yes | Self-contained output |
| Merge all layers into one | ✅ Yes | Core purpose of flattening |
| Ensure unique prim paths | ✅ Yes | Namespace collisions must be resolved |
| Collapse variants to selected variant | ✅ Yes | Variant switching no longer possible |
| Bake time-sampled data to static values | ❌ No | Animation is PRESERVED — separate operation |
| Convert geometry to single mesh type | ❌ No | Geometry types never change |
| Preserve all variant sets intact | ❌ No | Variants collapse to selected |

---

## 10. UI/UX for USD Pipelines

USD pipeline tools should reflect USD's modular, graph-based nature:

| ✅ Good patterns | ❌ Anti-patterns |
|-----------------|----------------|
| Node-based visual editor with drag-and-drop | Modal dialogs for every configuration change |
| Real-time feedback on execution status and errors | Linear-only pipeline flows (USD branches and merges) |
| Context-sensitive help and tooltips for nodes | No customisation options |
| Support for branching and merging node flows | — |

> Node-based editors are specifically recommended because USD's composition model **is** a graph — layers reference layers, assets reference assets, variants branch and merge. The UI should reflect this structure.

---

## 11. Build Configuration Management

| ✅ Correct practices | ❌ Anti-patterns |
|--------------------|----------------|
| Explicit build variants in config files | Undocumented environment variables |
| Centralised version-controlled config | Hardcoded paths in build scripts |
| Conditional logic for different platforms | Ignoring build cache (forces unnecessary rebuilds) |
| Documented environment variables | — |

---

## 12. Pipeline Design Principles

```python
from pxr import Usd, Sdf

# Stage Caching — avoid redundant recomposition
cache = Usd.StageCache()
with Usd.StageCacheContext(cache):
    stage = Usd.Stage.Open("scene.usda")
    # Second Open returns cached stage — no recomposition
    stage2 = Usd.Stage.Open("scene.usda")

# Change Notifications — SdfChangeBlock for bulk authoring
with Sdf.ChangeBlock():
    for i in range(10000):
        attr.Set(value[i], time=i)
# ONE notification sent after block — not 10,000
```

---

## 13. Conceptual Data Mapping Documents

A conceptual data mapping document is the **logical blueprint** that specifies how source schema attributes map to target USD schema attributes before writing any code.

### Required Contents

- **Attribute correspondences** — source name → target name, data type, units
- **Transformation rules** — how complex conversions work (unit scaling, axis flipping)
- **Mandatory vs optional fields** — which must be present for a valid exchange

### NOT in Mapping Documents

- Version histories of source/target schemas (belongs in schema management)
- Physical storage format details (implementation concern)
- Example payloads with actual data (belongs in testing documentation)

---

## 14. Custom Importers — Intermediate Representation Pattern

The standard architecture for a custom USD importer decouples file format parsing from USD API authoring.

```
WRONG — interleaved (hard to debug, brittle):
  open_file()
  create_usd_prim()     ← mixing I/O with USD authoring
  read_next_object()
  set_usd_attribute()   ← fragile coupling

CORRECT — two-pass (clean separation):
  PASS 1: parse_proprietary_file() → intermediate Python dict/objects
           validates data, converts units, handles errors
  
  PASS 2: populate_usd_stage(intermediate) → USD stage
           uses clean validated data, no file I/O concerns
```

```python
def import_file(filepath: str, output_usd: str):
    # Pass 1 — parse to intermediate
    intermediate = {
        "meshes":     [],
        "materials":  [],
        "transforms": [],
    }
    with open(filepath) as f:
        # parse proprietary format into intermediate
        # validate data, convert units, handle errors here
        pass

    # Pass 2 — populate USD from intermediate
    stage = Usd.Stage.CreateNew(output_usd)
    for mesh_data in intermediate["meshes"]:
        mesh = UsdGeom.Mesh.Define(stage, mesh_data["path"])
        mesh.GetPointsAttr().Set(mesh_data["points"])
        # ...

    stage.Save()
```

> **Why this pattern:** (1) Parsing and USD authoring can each be tested independently. (2) Errors are caught before any USD state is created. (3) USD API calls can be batched inside `SdfChangeBlock` for performance.

### Wrong Approaches

| Wrong | Why |
|-------|-----|
| `Implementing a custom UsdSchema` for the import | Custom schemas are for extending USD data types — not required for importing |
| Writing USD ASCII files directly | Bypasses USD validation and layering |
| Using only `UsdGeom` namespace | Animation may need `UsdSkel`, materials need `UsdShade` |

---

## 15. Data Interchange Script Best Practices

| ✅ Always do | ❌ Never do |
|-------------|-----------|
| Use USD's layering and composition to combine sources | Manually merge data in scripts |
| Use USD Python API to create UsdPrims with schemas | Write USD ASCII by hand |
| Use relative paths or asset resolvers | Use absolute file paths |
| Use proper schemas for proprietary metadata | Embed unregistered string blobs |
| Use time samples for animated data | Use static defaults for animation |

---

## 16. Key Takeaways

| Concept | What to Remember |
|---------|-----------------|
| `.usd` extension | Generic — USD auto-detects ASCII vs binary from file header |
| Rename `.usda` → `.usdc` | Invalid — different binary formats |
| `usdcat` | Format conversion and flattening. `usdzip` for `.usdz` packaging |
| `usdchecker` | Validates. Does NOT auto-fix. |
| Exporter hooks | Pre/post hooks extend export. Never override the main export function |
| Proprietary dependencies | Refactor to USD native (UsdPreviewSurface, custom schemas) |
| Mapping docs contain | Attribute correspondences, transformation rules, mandatory/optional fields |
| Mapping docs exclude | Version histories, storage format details, example payloads |
| Importer pattern | Parse to intermediate first, then populate USD |
| Custom schema for import | NOT required for importing — only needed when extending USD data types |
| Stage caching | `UsdStageCache` — avoids redundant recomposition |
| `SdfChangeBlock` | Batches change notifications — critical for bulk authoring performance |
| Flatten preserves | Time samples (animation), geometry types |
| Flatten discards | Variant sets (collapsed), composition arcs |

---

*Previous: [Day 6 — Visualization](day-06-visualization.md)*  
*Next: [Day 8 — Content Aggregation](day-08-content-aggregation.md)*
