# Day 1 — USD Foundations

> **OpenUSD NCP Certification Study Notes**  
> *Universal Scene Description — Core Architecture*

---

## Table of Contents

1. [The Stage](#1-the-stage)
2. [Layers](#2-layers)
3. [Prims — The Scene Graph](#3-prims--the-scene-graph)
4. [Properties — Attributes and Relationships](#4-properties--attributes-and-relationships)
5. [SdfPath — Addressing the Scene](#5-sdfpath--addressing-the-scene)
6. [USD File Formats](#6-usd-file-formats)
7. [Metadata](#7-metadata)
8. [Time Samples and Animation](#8-time-samples-and-animation)
9. [Key Takeaways](#9-key-takeaways)

---

## 1. The Stage

The **Stage** (`Usd.Stage`) is the top-level in-memory container that represents your entire 3D scene. It is what renderers, viewports, and tools operate on. Everything — geometry, lights, cameras, materials — is accessed through the stage.

> **Critical concept:** A Stage is *not* a file. It is a live, in-memory composition assembled from one or more **Layers**. When you open a USD file, USD reads it, resolves all references, and assembles a composed Stage in memory.

```
                ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
                │ lighting.   │  │ layout.     │  │ models.     │
                │ usda        │  │ usda        │  │ usda        │
                └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
                       │                │                  │
                       └────────────────┴──────────────────┘
                                        │
                                        ▼
                             ┌──────────────────────┐
                             │   COMPOSED STAGE     │
                             │  (in-memory view)    │
                             └──────────────────────┘
```

### Python API — `Usd.Stage`

```python
from pxr import Usd

# Create a new stage backed by a real file on disk
# The file is created immediately even before any content is added
stage = Usd.Stage.CreateNew("my_scene.usda")

# Open an existing USD file
# USD loads the file and all files it transitively references
stage = Usd.Stage.Open("my_scene.usda")

# Create an in-memory stage with no file backing
# Use for testing, temporary work, or before deciding on output path
stage = Usd.Stage.CreateInMemory()

# Save all changes back to the backing file(s)
stage.Save()

# Export the stage to a new path (optionally converting format)
# stage.Export() flattens ALL composition into a single layer
stage.Export("output.usdc")

# Inspect the stage as USDA text — invaluable for debugging
print(stage.ExportToString(addSourceFileComment=False))
```

| Method | Behaviour |
|--------|-----------|
| `CreateNew(path)` | Creates file on disk immediately, returns writable stage |
| `Open(path)` | Opens existing file, assembles all referenced layers |
| `CreateInMemory()` | No disk file, all in RAM |
| `Save()` | Writes dirty layers back to their backing files |
| `Export(path)` | Flattens and writes to a new file at `path` |

---

## 2. Layers

A **Layer** (`Sdf.Layer`) is a single USD file — or in-memory buffer — containing scene description. It is the physical unit of storage. Stages are assembled from layers; layers are what actually exist on disk.

### Layer Stack

Every stage has a **root layer** and zero or more **sublayers**. Sublayers are declared inside the root layer's metadata and are loaded in order. The order matters — earlier sublayers have **higher strength** (their opinions win when there is a conflict).

```usda
#usda 1.0
(
    subLayers = [
        @./anim.usda@,       # strongest — loaded first
        @./layout.usda@,
        @./model.usda@       # weakest — loaded last
    ]
)
```

### Python API — `Sdf.Layer`

```python
from pxr import Sdf, Usd

# Find a layer that is already loaded (by its identifier/path)
layer = Sdf.Layer.FindOrOpen("model.usda")

# Access the root layer of a stage
root_layer = stage.GetRootLayer()

# Access the session layer (in-memory, ephemeral, always strongest)
session_layer = stage.GetSessionLayer()

# Inspect all layers in the root layer stack, strongest → weakest
for layer in stage.GetLayerStack():
    print(layer.identifier)

# Add a sublayer programmatically
root_layer.subLayerPaths.append("./new_layer.usda")

# Read and write layer-level metadata
root_layer.customLayerData = {
    "pipeline:schemaVersion": "2.0",
    "pipeline:studio":        "AcmeStudios",
}
```

> **The session layer** is a special in-memory layer that is always the strongest. It captures interactive edits (e.g., from usdview). It is **never saved to disk** by `stage.Save()`. Use it for temporary per-session overrides.

---

## 3. Prims — The Scene Graph

A **Prim** (Primitive) is every individual node in the scene graph. Every mesh, light, camera, material, or empty organising container is a prim. The scene graph is a tree of prims.

```
/                             ← pseudo-root (always exists, invisible)
└── World  (Xform)            ← organising container
    ├── Geometry  (Scope)     ← namespace grouping (no transform)
    │   ├── Chair  (Mesh)     ← polygon geometry
    │   └── Table  (Mesh)
    ├── Lights  (Scope)
    │   └── KeyLight  (DistantLight)
    └── Materials  (Scope)
        └── WoodMat  (Material)
```

### Prim Specifiers

Every prim in a USDA file begins with one of three **specifier keywords**. Understanding these is fundamental to understanding composition.

| Specifier | Meaning | Use case |
|-----------|---------|----------|
| `def` | **Define** — creates a new prim and claims full ownership | Authoring new content |
| `over` | **Override** — adds opinions on an *existing* prim without claiming ownership | Overriding values in a stronger layer |
| `class` | **Class** — an abstract template prim, never rendered directly | Used with `inherits` arc |

```usda
# model.usda — defines the prim (weaker layer)
def Xform "Chair" {
    double3 xformOp:translate = (0, 0, 0)
}

# anim.usda — overrides the prim (stronger layer)
over "Chair" {
    # No type declaration — over doesn't claim ownership
    double3 xformOp:translate = (5, 0, 0)   # this wins
}
# Composed result: Chair is at (5, 0, 0)
```

> **Important:** An `over` with no corresponding `def` anywhere in the layer stack has no effect. It silently composes to nothing. This is a common source of "why isn't my change applying?" debugging scenarios.

### Python API — `Usd.Prim`

```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateInMemory()

# Define a prim using the generic API
# Signature: stage.DefinePrim(path: str, typeName: str = "") -> Usd.Prim
chair = stage.DefinePrim("/World/Chair", "Xform")
# Produces: def Xform "Chair" { }

# Define a prim using the schema-specific API (preferred)
# This gives type-safe access to schema attributes
sphere = UsdGeom.Sphere.Define(stage, "/World/Ball")
sphere.GetRadiusAttr().Set(5.0)

# Retrieve a prim by path
prim = stage.GetPrimAtPath("/World/Chair")
# Returns an invalid prim (evaluates to False) if path does not exist
if not prim:
    print("Prim not found")

# Inspect prim properties
print(prim.GetPath())       # Sdf.Path("/World/Chair")
print(prim.GetTypeName())   # "Xform"
print(prim.IsValid())       # True
print(prim.IsDefined())     # True if at least one 'def' spec exists
print(prim.IsActive())      # True unless deactivated

# Navigate the hierarchy
for child in prim.GetChildren():
    print(child.GetPath())

# Type checking
print(prim.IsA(UsdGeom.Xform))     # True
print(prim.HasAPI(UsdGeom.MotionAPI)) # True/False
```

### Common Prim Types

| Schema Type | Module | Purpose |
|-------------|--------|---------|
| `Xform` | `UsdGeom` | Transform node — groups children, applies translate/rotate/scale |
| `Scope` | `UsdGeom` | Namespace container — no transform |
| `Mesh` | `UsdGeom` | Polygonal geometry |
| `Sphere`, `Cube`, `Cylinder` | `UsdGeom` | Parametric primitives |
| `Camera` | `UsdGeom` | Camera with lens attributes |
| `DistantLight`, `SphereLight`, `RectLight`, `DomeLight` | `UsdLux` | Light sources |
| `Material` | `UsdShade` | Shading network container |
| `Shader` | `UsdShade` | Individual shading node |

---

## 4. Properties — Attributes and Relationships

Properties are the **data stored on a prim**. There are exactly two kinds:

### Attributes

An attribute stores a **typed value** — a number, a vector, a colour, a string, an array. This is where all actual 3D data lives.

```usda
double   radius = 5.0
float    intensity = 1000.0
bool     doubleSided = false
token    visibility = "inherited"
double3  xformOp:translate = (0, 5, 0)
color3f  inputs:diffuseColor = (0.8, 0.2, 0.1)
color3f[] primvars:displayColor = [(1, 0, 0)]
int[]    faceVertexCounts = [4, 4, 4]
```

### Relationships

A relationship stores a **path pointing to another prim** — no value, only a connection.

```usda
rel material:binding = </World/Materials/WoodMat>
```

### Value Types Reference

| USDA Type | Python/Gf Equivalent | Description |
|-----------|----------------------|-------------|
| `double` | `float` | 64-bit float |
| `float` | `float` | 32-bit float |
| `int` | `int` | 32-bit integer |
| `bool` | `bool` | Boolean |
| `token` | `str` | Interned string (enum-like) |
| `string` | `str` | Arbitrary string |
| `double3` | `Gf.Vec3d` | 3-component double vector |
| `float3` | `Gf.Vec3f` | 3-component float vector |
| `color3f` | `Gf.Vec3f` | RGB colour |
| `matrix4d` | `Gf.Matrix4d` | 4×4 transform matrix |
| `asset` | `Sdf.AssetPath` | File path reference |
| `T[]` | `Vt.Array` | Array of any type `T` |

### Python API — `Usd.Attribute`

```python
from pxr import Usd, UsdGeom, Sdf, Gf, Vt

stage  = Usd.Stage.CreateInMemory()
sphere = UsdGeom.Sphere.Define(stage, "/World/Ball")

# --- Reading attributes ---

# Get the Attribute object (does not return the value)
attr = sphere.GetRadiusAttr()

# Get the composed value (default time)
value = attr.Get()              # returns 1.0 (schema fallback)

# Get the value at a specific time code
value_at_t = attr.Get(time=24)  # returns value at frame 24

# Check if this value was explicitly authored (vs schema fallback)
attr.HasAuthoredValue()         # True = explicitly Set(), False = fallback

# --- Writing attributes ---

sphere.GetRadiusAttr().Set(5.0)

# Set at a specific time code (creates a time sample = animation keyframe)
sphere.GetRadiusAttr().Set(5.0,  time=1)
sphere.GetRadiusAttr().Set(10.0, time=24)

# --- Creating custom attributes ---
# Signature: prim.CreateAttribute(name, typeName, custom=True) -> Usd.Attribute
prim = sphere.GetPrim()
custom_attr = prim.CreateAttribute(
    "pipeline:assetId",
    Sdf.ValueTypeNames.String
)
custom_attr.Set("CHAIR_001_v3")

# --- Primvars ---
# Primvars inherit down the hierarchy and are used by renderers
from pxr import UsdGeom
primvar = UsdGeom.PrimvarsAPI(sphere.GetPrim()).CreatePrimvar(
    "displayColor",
    Sdf.ValueTypeNames.Color3fArray,
    UsdGeom.Tokens.constant
)
primvar.Set(Vt.Vec3fArray([Gf.Vec3f(1.0, 0.0, 0.0)]))  # red
```

---

## 5. SdfPath — Addressing the Scene

Every prim and property in a USD scene has a unique **path** — a string address that identifies its location in the scene graph. Paths are represented as `Sdf.Path` objects.

```
/World/Chair/seat_geo.primvars:displayColor
│            │         │
│            │         └─ property name (with namespace)
│            └─────────── prim name (child of Chair)
└──────────────────────── root prim
```

### Path Syntax Rules

| Rule | Example |
|------|---------|
| Always begins with `/` | `/World/Chair` |
| Prim names separated by `/` | `/World/Geometry/Mesh` |
| Property separated from prim by `.` | `/World/Chair.visibility` |
| Colons `:` inside names indicate namespacing | `xformOp:translate`, `inputs:diffuseColor` |
| No spaces anywhere in a path | `/World/My_Chair` ✅ `/World/My Chair` ❌ |
| Case-sensitive | `/World/Chair` ≠ `/World/chair` |

```python
from pxr import Sdf

# Construct paths
prim_path = Sdf.Path("/World/Chair")
prop_path = Sdf.Path("/World/Chair.xformOp:translate")

# Navigate relative to an existing path
parent  = prim_path.GetParentPath()     # /World
name    = prim_path.name                # "Chair"
is_prop = prop_path.IsPropertyPath()   # True

# Get a child path
child = prim_path.AppendChild("Armrest")  # /World/Chair/Armrest
```

---

## 6. USD File Formats

USD supports four file extensions. Choosing the right format is a tested topic.

| Extension | Format | Human-readable | Speed | Self-contained | Use case |
|-----------|--------|---------------|-------|----------------|---------|
| `.usda` | ASCII text | ✅ Yes | Slow | ❌ No | Authoring, debugging, version control |
| `.usdc` | Binary crate | ❌ No | Very fast | ❌ No | Production pipelines, large geometry |
| `.usd` | Either (auto-detected) | Depends | Depends | ❌ No | Generic — USD detects format at load time |
| `.usdz` | Zip archive | ❌ No | Fast | ✅ Yes | Delivery to external parties, AR/VR distribution |

### Key Distinctions

**`.usd`** is a **generic extension** — USD examines the file header at load time and determines whether it is ASCII or binary. Renaming a `.usda` file to `.usd` is valid and USD will handle it correctly. Renaming `.usda` to `.usdc` is **not valid** — they have different internal formats.

**`.usdz`** is a **zip archive** that bundles the root USD file plus all its dependencies (textures, sublayers, referenced files). It is:
- The correct format for delivering assets to external studios
- The correct format for AR/VR distribution (Apple RealityKit, USDZ for web)
- Read-only — you cannot reference external files from inside a `.usdz`

### Command-Line Tools

```bash
# Convert between .usda and .usdc (format determined by output extension)
usdcat scene.usda -o scene.usdc

# Flatten all composition arcs into a single file
usdcat --flatten scene.usda -o flat.usda

# Print the composition arc graph for all prims
usdcat --print-composition scene.usda

# Create a .usdz package (bundles all dependencies)
usdzip -r delivery.usdz scene.usda

# List contents of a .usdz without extracting
usdzip -l delivery.usdz

# Validate a USD file against best practices
usdchecker scene.usda
```

---

## 7. Metadata

Metadata is scene-wide or prim-level configuration data stored **in the layer header or prim header** — separate from the prim properties. It is not rendered, not animated, and not composed the same way as properties.

### Stage-Level Metadata

```usda
#usda 1.0
(
    upAxis = "Y"               # Y-up coordinate system (industry standard)
    metersPerUnit = 0.01       # 1 unit = 1 centimetre
    timeCodesPerSecond = 24    # 24 fps animation
    startTimeCode = 1
    endTimeCode = 240
    defaultPrim = "World"      # which prim references should target by default
    
    subLayers = [
        @./anim.usda@,
        @./layout.usda@
    ]
)
```

### Python API — Stage Metadata

```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateInMemory()

# Coordinate system
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)    # Y-up
UsdGeom.SetStageMetersPerUnit(stage, 0.01)          # 1 unit = 1 cm

# Read coordinate system
up_axis = UsdGeom.GetStageUpAxis(stage)             # UsdGeom.Tokens.y
mpu     = UsdGeom.GetStageMetersPerUnit(stage)      # 0.01

# Animation range
stage.SetMetadata("timeCodesPerSecond", 24)
stage.SetMetadata("startTimeCode", 1)
stage.SetMetadata("endTimeCode", 240)

# defaultPrim — critical for references to work correctly
root_prim = stage.DefinePrim("/World", "Xform")
stage.SetDefaultPrim(root_prim)
# Now any file that references this asset will target /World automatically

# Custom pipeline metadata
stage.GetRootLayer().customLayerData = {
    "pipeline:schemaVersion": "2.0",
    "pipeline:studio":        "AcmeStudios",
    "pipeline:exportTool":    "MayaExporter_v2",
}

# Read custom metadata
custom  = stage.GetRootLayer().customLayerData
version = custom.get("pipeline:schemaVersion", "unknown")
```

> **`defaultPrim`** is one of the most commonly tested metadata fields. When asset A references asset B, USD needs to know which prim in B to bring in. If `defaultPrim` is not set on B, the reference fails. Always set `defaultPrim` to the root prim of every published asset.

---

## 8. Time Samples and Animation

USD represents animation through **time samples** — a dictionary mapping time codes (frame numbers) to values. An attribute can have:

- A **default value** — a single value with no time association, returned when no time samples are present or when `Usd.TimeCode.Default()` is requested
- **Time samples** — multiple values keyed by time code

```usda
def Xform "Ball" {
    double3 xformOp:translate.timeSamples = {
        1:  (0, 0, 0),
        24: (5, 0, 0),
        48: (10, 0, 0)
    }
    uniform token[] xformOpOrder = ["xformOp:translate"]
}
```

USD **interpolates** between time samples automatically. Between frames 1 and 24, the ball is linearly interpolated from `(0,0,0)` to `(5,0,0)`.

### Python API — Time Samples

```python
from pxr import Usd, UsdGeom, Gf

stage = Usd.Stage.CreateInMemory()
stage.SetMetadata("timeCodesPerSecond", 24)
stage.SetMetadata("startTimeCode", 1)
stage.SetMetadata("endTimeCode", 48)

ball = UsdGeom.Sphere.Define(stage, "/World/Ball")
attr = ball.GetPrim().CreateAttribute(
    "xformOp:translate", Sdf.ValueTypeNames.Double3
)

# Author time samples by passing `time=` to Set()
attr.Set(Gf.Vec3d(0, 0, 0),  time=1)
attr.Set(Gf.Vec3d(5, 0, 0),  time=24)
attr.Set(Gf.Vec3d(10, 0, 0), time=48)

# Read value at a specific time
value = attr.Get(time=24)    # Gf.Vec3d(5, 0, 0)

# Read default value (no time association)
default = attr.Get()                        # None if only time samples exist
default = attr.Get(Usd.TimeCode.Default())  # equivalent

# Inspect all time samples
samples = attr.GetTimeSamples()   # [1.0, 24.0, 48.0]

# Check authoring status
attr.HasAuthoredValue()    # True if any value (default or time sample) was Set()

# GetPropertyStack — find which layers contributed opinions at time=24
# Signature: attr.GetPropertyStack(timeCode: Usd.TimeCode) -> list[SdfPropertySpec]
# Parameter is REQUIRED — there is no default argument
stack = attr.GetPropertyStack(Usd.TimeCode(24))
# Note: Usd.TimeCode.Default() ≠ Usd.TimeCode(0)
# TimeCode.Default() = "the plain authored default" (no time association)
# TimeCode(0)        = "the value at frame 0" (a real point in time)
# Shorthand: attr.GetPropertyStack(24) == attr.GetPropertyStack(Usd.TimeCode(24))
```

### `Usd.TimeCode` — Critical Distinction

| Expression | Meaning |
|------------|---------|
| `Usd.TimeCode.Default()` | The plain authored default value — no time association |
| `Usd.TimeCode(24)` or just `24` | The value at time code 24 (frame 24) |
| `Usd.TimeCode(0)` or just `0` | The value at time code 0 — **NOT the same as Default()** |

`TimeCode.Default()` has no numeric shorthand — it must always be written in full.

---

## 9. Key Takeaways

| Concept | What to Remember |
|---------|-----------------|
| **Stage** | In-memory composition of layers. Not a file. |
| **Layer** | A physical USD file or in-memory buffer. |
| **Prim** | Every node in the scene graph. Has a path, a type, properties. |
| **`def`** | Creates a prim. Claims ownership. Has a type. |
| **`over`** | Overrides an existing prim. No type. No effect without a `def`. |
| **`class`** | Abstract template. Used with `inherits`. Never rendered. |
| **Attribute** | Stores typed values on a prim. Can be time-sampled. |
| **Relationship** | Stores a path to another prim. Used for material binding. |
| **SdfPath** | Unique address of every prim and property. Case-sensitive. |
| **`.usda`** | ASCII text — human-readable, slow, good for debugging |
| **`.usdc`** | Binary crate — fast, compact, production format |
| **`.usdz`** | Zip archive — self-contained, for delivery and AR/VR |
| **`defaultPrim`** | Must be set on every published asset for references to work |
| **`upAxis`** | Always set explicitly — `Y` for DCC, `Z` for engineering tools |
| **`metersPerUnit`** | Always set explicitly — `0.01` = centimetres (common in DCC) |
| **Time samples** | Animation keyframes. `Set(value, time=n)` creates one. |
| **`TimeCode.Default()`** | The plain default — distinct from `TimeCode(0)` (frame 0) |

---

*Next: [Day 2 — Composition Arcs Part 1](day-02-composition-arcs-part-1.md)*
