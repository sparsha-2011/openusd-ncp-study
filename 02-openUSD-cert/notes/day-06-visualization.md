# Day 6 — Visualization

> **OpenUSD NCP Certification Study Notes**  
> *UsdGeomMesh, UsdGeomCamera, UsdShadeMaterial, Lights, Primvars, Visibility*

---

## Table of Contents

1. [UsdGeomImageable — Visibility and Purpose](#1-usdgeomimageable--visibility-and-purpose)
2. [UsdGeomMesh — Polygon Geometry](#2-usdgeommesh--polygon-geometry)
3. [Primvars — Per-Element Data](#3-primvars--per-element-data)
4. [UsdShadeMaterial and UsdShadeShader](#4-usdshadmaterial-and-usdshadereshader)
5. [UsdPreviewSurface and the Texture Chain](#5-usdpreviewsurface-and-the-texture-chain)
6. [UsdLux — Lights](#6-usdlux--lights)
7. [UsdGeomCamera — Complete Reference](#7-usdgeomcamera--complete-reference)
8. [Key Takeaways](#8-key-takeaways)

---

## 1. UsdGeomImageable — Visibility and Purpose

`UsdGeomImageable` is the base class for **all renderable prims** in USD. It provides exactly two things — nothing more:

1. `visibility` — whether the prim is rendered
2. `purpose` — which rendering context the prim appears in

### Visibility

```python
from pxr import UsdGeom

imageable = UsdGeom.Imageable(prim)

# Make invisible
imageable.MakeInvisible()
# Sets visibility = "invisible" on this prim

# Make visible
imageable.MakeVisible()
# Sets visibility = "inherited" on this prim

# Compute resolved visibility (walks up hierarchy)
computed = imageable.ComputeVisibility()
# Returns "inherited" or "invisible"
# A parent set to invisible makes ALL children invisible
# regardless of their own visibility setting
```

> **Visibility inherits down the hierarchy.** If a parent prim is invisible, all its children are invisible even if they have `visibility = "inherited"`. `ComputeVisibility()` resolves this by walking up the prim hierarchy.

### Purpose Tokens

| Purpose | Who sees it | Use case |
|---------|-------------|---------|
| `"render"` | Final render passes only | Full-resolution production geometry |
| `"proxy"` | Viewport stand-in | Low-poly representation for interactive use |
| `"guide"` | Rigging context only — NEVER rendered | Rig controls, helper geometry, bones |
| `"default"` | All contexts (fallback) | General objects with no special context |

```python
imageable.GetPurposeAttr().Set(UsdGeom.Tokens.render)
imageable.GetPurposeAttr().Set(UsdGeom.Tokens.proxy)
imageable.GetPurposeAttr().Set(UsdGeom.Tokens.guide)
imageable.GetPurposeAttr().Set(UsdGeom.Tokens.default_)

# Compute resolved purpose (inherits from parents)
purpose = imageable.ComputePurpose()
```

---

## 2. UsdGeomMesh — Polygon Geometry

`UsdGeomMesh` is the schema for polygonal geometry. Every 3D mesh in a USD scene is represented by three required attributes working together.

### The Three Required Attributes

**`points`** — the 3D positions of every vertex, in the prim's local coordinate space:

```usda
point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]
#                   corner 0  corner 1  corner 2  corner 3
```

**`faceVertexCounts`** — how many vertices each face has:

```usda
int[] faceVertexCounts = [4, 4, 3]
#                          ↑    ↑   ↑
#                         quad quad triangle  (3 faces)
```

**`faceVertexIndices`** — which vertices (by index into `points`) form each face, all faces concatenated:

```usda
int[] faceVertexIndices = [0,1,2,3,  4,5,6,7,  0,1,5]
#                          face 0    face 1     face 2
```

> **Critical:** `faceVertexIndices.length` = **SUM of faceVertexCounts**. Not the number of points. Not the number of faces.
>
> For the above: `4 + 4 + 3 = 11` — the indices array has 11 elements.

### Additional Mesh Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `subdivisionScheme` | `token` | `"none"` (flat), `"catmullClark"` (smooth), `"loop"`, `"bilinear"` |
| `holeIndices` | `int[]` | Face indices to treat as holes — geometry exists but is NOT rendered |
| `doubleSided` | `bool` | Whether to render back faces |
| `extent` | `float3[2]` | Axis-aligned bounding box — required for correct viewport display |

### Python API

```python
from pxr import UsdGeom, Vt, Gf

stage = Usd.Stage.CreateInMemory()
mesh  = UsdGeom.Mesh.Define(stage, "/World/Chair")

# Set geometry
mesh.GetPointsAttr().Set(Vt.Vec3fArray([
    Gf.Vec3f(-1, 0, -1), Gf.Vec3f(1, 0, -1),
    Gf.Vec3f(1, 0, 1),   Gf.Vec3f(-1, 0, 1),
]))

mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([4]))
mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2, 3]))

# Subdivision
mesh.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.catmullClark)

# Holes — face index 2 is a hole (exists in topology, not rendered)
mesh.GetHoleIndicesAttr().Set(Vt.IntArray([2]))

# Extent — required for viewport correctness
mesh.GetExtentAttr().Set(Vt.Vec3fArray([
    Gf.Vec3f(-1, 0, -1), Gf.Vec3f(1, 0, 1)
]))
```

> **UVs are NEVER auto-generated.** UV coordinates must be explicitly authored as `primvars:st`. The exam specifically tests this.

---

## 3. Primvars — Per-Element Data

**Primvars** (Primitive Variables) are attributes in the `primvars:` namespace that carry per-element data — colours, UVs, normals — from geometry to shaders.

### Interpolation Modes

The `interpolation` metadata on a primvar determines how many values are needed and how they map to geometry:

| Interpolation | Values needed | Maps to |
|---------------|--------------|---------|
| `constant` | 1 | Entire prim — one value for everything |
| `uniform` | 1 per face | Each face has its own value |
| `vertex` | 1 per point | Each vertex has a value, interpolated across faces |
| `faceVarying` | 1 per face-vertex | Most precise — one per entry in `faceVertexIndices` |

> **`faceVarying` is used for UVs** because the same 3D vertex can have different UV coordinates on different faces (at seams). `faceVarying` count = `faceVertexIndices.length` = sum of `faceVertexCounts`.

### Primvar Key Facts

- Primvars are **NOT** always uniform interpolation — they have four distinct modes
- Primvars are authored on specific prims — they do **not** need to be on the root prim
- Primvars with `constant` interpolation inherit down the hierarchy
- Primvars **do not have a built-in fallback value mechanism**
- Primvars **can** be time-sampled (animated UVs, animated colours)
- `"indexed"` is **not** an interpolation type — primvars can be indexed but interpolation and indexing are separate concepts

### Python API — `UsdGeom.PrimvarsAPI`

```python
from pxr import UsdGeom, Sdf, Vt, Gf

primvar_api = UsdGeom.PrimvarsAPI(mesh.GetPrim())

# Create a UV primvar (faceVarying — most common for UVs)
st = primvar_api.CreatePrimvar(
    "st",
    Sdf.ValueTypeNames.TexCoord2fArray,
    UsdGeom.Tokens.faceVarying
)
st.Set(Vt.Vec2fArray([
    Gf.Vec2f(0, 0), Gf.Vec2f(1, 0),
    Gf.Vec2f(1, 1), Gf.Vec2f(0, 1),
]))

# Create a displayColor primvar (constant — whole prim is red)
color = primvar_api.CreatePrimvar(
    "displayColor",
    Sdf.ValueTypeNames.Color3fArray,
    UsdGeom.Tokens.constant
)
color.Set(Vt.Vec3fArray([Gf.Vec3f(1.0, 0.0, 0.0)]))
```

---

## 4. UsdShadeMaterial and UsdShadeShader

### The Material Hierarchy

```
/World/Looks/WoodMat                ← UsdShadeMaterial (the CONTAINER)
  └── /World/Looks/WoodMat/Shader   ← UsdShadeShader (the computation node)
```

The **Material** is a container that exposes outputs to the renderer. The **Shader** nodes inside it do the actual shading computation. They connect via outputs.

### `inputs:` and `outputs:`

Every `UsdShadeShader` has:

- **`inputs:`** — parameters the shader **accepts** (colour, roughness, texture coordinates, etc.)
- **`outputs:`** — data the shader **produces** (the surface result, colour values, etc.)

```
geometry.primvars:st
        ↓
PrimvarReader.inputs:varname = "st"
PrimvarReader.outputs:result (float2)
        ↓
UVTexture.inputs:st ← connected from PrimvarReader.outputs:result
UVTexture.inputs:file = "./textures/wood.png"
UVTexture.outputs:rgb (color3f)
        ↓
PreviewSurface.inputs:diffuseColor ← connected from UVTexture.outputs:rgb
PreviewSurface.inputs:roughness = 0.5
PreviewSurface.outputs:surface (token)
        ↓
Material.outputs:surface ← connected from PreviewSurface.outputs:surface
```

> **Exam traps:**
> - `inputs:` and `outputs:` are **NOT deprecated** — they are fundamental to UsdShade
> - `inputs:` can hold any data type — not just textures
> - A Shader does NOT contain Materials — it's the reverse: Material contains Shaders

### Python API

```python
from pxr import UsdShade, Sdf

stage = Usd.Stage.CreateInMemory()

# Create the Material container
mat    = UsdShade.Material.Define(stage, "/World/Looks/WoodMat")

# Create the Shader node inside it
shader = UsdShade.Shader.Define(stage, "/World/Looks/WoodMat/Shader")
shader.CreateIdAttr("UsdPreviewSurface")

# Author inputs (parameters going IN)
shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f
).Set(Gf.Vec3f(0.6, 0.4, 0.2))
shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)

# Create the surface output (data coming OUT)
surf_out = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)

# Connect Material output → Shader output
mat.CreateSurfaceOutput().ConnectToSource(surf_out)

# Bind the material to a mesh
# MaterialBindingAPI must be Applied BEFORE Bind() is called
binding_api = UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
binding_api.Bind(mat)
```

---

## 5. UsdPreviewSurface and the Texture Chain

`UsdPreviewSurface` is the standard physically-based shader built into USD. It works in all USD-compliant renderers.

### Key Inputs

| Input | Type | Description |
|-------|------|-------------|
| `diffuseColor` | `color3f` | Base surface colour |
| `roughness` | `float` | 0 = mirror smooth, 1 = completely rough |
| `metallic` | `float` | 0 = dielectric, 1 = full metal |
| `opacity` | `float` | 1 = opaque, 0 = transparent |
| `normal` | `normal3f` | Normal map (tangent space) |
| `emissiveColor` | `color3f` | Self-illumination colour |

### Reading a Texture — Three-Node Chain

```python
# Node 1 — UsdPrimvarReader_float2
# Reads the UV primvar (primvars:st) from the mesh geometry
reader = UsdShade.Shader.Define(stage, "/Looks/Mat/Reader")
reader.CreateIdAttr("UsdPrimvarReader_float2")
reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
# "st" — NOT "primvars:st" — the primvars: prefix is OMITTED in varname
reader_out = reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)

# Node 2 — UsdUVTexture
# Samples an image texture using the UV coordinates
tex = UsdShade.Shader.Define(stage, "/Looks/Mat/Texture")
tex.CreateIdAttr("UsdUVTexture")
tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set("./wood.png")
tex_st = tex.CreateInput("st", Sdf.ValueTypeNames.Float2)
tex_st.ConnectToSource(reader_out)     # connect UV from reader
tex_rgb = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

# Node 3 — UsdPreviewSurface
# Uses the texture colour as diffuseColor
surface = UsdShade.Shader.Define(stage, "/Looks/Mat/Surface")
surface.CreateIdAttr("UsdPreviewSurface")
diff_in = surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
diff_in.ConnectToSource(tex_rgb)       # connect texture to diffuseColor
surf_out = surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)

# Wire Material
mat.CreateSurfaceOutput().ConnectToSource(surf_out)
```

---

## 6. UsdLux — Lights

All UsdLux lights inherit from `UsdGeomXformable` — they are **transformable and animatable** like any other prim.

### Common Attributes Across All Lights

| Attribute | Type | Description |
|-----------|------|-------------|
| `intensity` | `float` | Brightness in lumens |
| `exposure` | `float` | Photographic stops: `final = intensity × 2^exposure` |
| `color` | `color3f` | Emitted colour tint |
| `falloffRadius` | `float` | Maximum distance the light affects the scene |

> **`falloffRadius` limits the light's effective range** — geometry beyond this radius receives no contribution. Used to optimise rendering by culling distant light calculations.

### Shadows Are NOT Automatic

Shadow casting requires **explicit configuration** via shadow attributes. Lights do not cast shadows by default.

### Light Types

| Schema | Analogy | Key attribute |
|--------|---------|---------------|
| `UsdLuxDistantLight` | Directional sun | `angle` (angular size of sun disk) |
| `UsdLuxSphereLight` | Point light with size | `radius` — controls shadow softness |
| `UsdLuxRectLight` | Studio softbox | `width`, `height` |
| `UsdLuxDomeLight` | HDRI environment | `textureFile` (path to .exr/.hdr) |
| `UsdLuxConeLight` | Spotlight | `shaping:cone:angle`, `shaping:cone:softness` |

### SphereLight Radius — Critical Exam Topic

`radius` on `UsdLuxSphereLight` controls the **angular spread and shadow softness** — NOT brightness.

```
Small radius → small light source → hard sharp shadows
Large radius → large light source → soft diffuse shadows

intensity  = brightness (lumens)
exposure   = brightness adjustment in photographic stops
radius     = shadow softness and light spread (SphereLight only)
color      = colour tint of emitted light
```

---

## 7. UsdGeomCamera — Complete Reference

`UsdGeomCamera` represents a camera in USD. It is **Xformable** — positioned, rotated, and animated using xformOp transforms. Animation requires **explicit time samples** — no auto-update.

### Projection Types — ONLY Two

```python
camera.GetProjectionAttr().Set(UsdGeom.Tokens.perspective)
camera.GetProjectionAttr().Set(UsdGeom.Tokens.orthographic)
# No fisheye, cylindrical, or spherical — only these two exist
```

| Projection | Behaviour | Use case |
|------------|-----------|---------|
| `perspective` | Objects farther away appear smaller | Film, games, visualisation |
| `orthographic` | All objects same size at any distance | CAD, technical drawings, isometric |

### Complete Attribute Reference

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `projection` | `token` | `"perspective"` | Only `perspective` or `orthographic` |
| `focalLength` | `float` | `50.0 mm` | Lens-to-image-plane distance. Controls FOV. |
| `horizontalAperture` | `float` | `20.955 mm` | Sensor width **in millimetres** (NOT inches) |
| `verticalAperture` | `float` | `15.291 mm` | Sensor height in millimetres |
| `horizontalApertureOffset` | `float` | `0.0` | Horizontal lens shift (tilt-shift effect) |
| `verticalApertureOffset` | `float` | `0.0` | Vertical lens shift |
| `clippingRange` | `float2` | `(1, 1000000)` | Near and far clip planes **— IS in the schema** |
| `fStop` | `float` | `0.0` | Aperture f-number — controls depth of field |
| `focusDistance` | `float` | `0.0` | Distance to in-focus plane |

### Focal Length and Field of View

Focal length and aperture work **together** to determine field of view:

```
FOV = 2 × atan(horizontalAperture / (2 × focalLength))

18mm focal length + 24mm sensor → wide angle ~67° FOV
85mm focal length + 24mm sensor → telephoto ~16° FOV
```

### Python API

```python
from pxr import UsdGeom, Gf

camera = UsdGeom.Camera.Define(stage, "/World/MainCamera")

# Position using xformOp (camera is Xformable)
UsdGeom.XformCommonAPI(camera).SetTranslate(Gf.Vec3d(0, 5, 20))
UsdGeom.XformCommonAPI(camera).SetRotate(Gf.Vec3f(-15, 0, 0))

# Lens properties
camera.GetProjectionAttr().Set(UsdGeom.Tokens.perspective)
camera.GetFocalLengthAttr().Set(35.0)
camera.GetHorizontalApertureAttr().Set(24.0)    # mm, not inches
camera.GetVerticalApertureAttr().Set(13.5)      # 16:9 aspect ratio

# Clipping (IS in the schema — not handled externally)
camera.GetClippingRangeAttr().Set(Gf.Vec2f(0.1, 10000))

# Depth of field
camera.GetFocusDistanceAttr().Set(8.0)   # focus at 8 units
camera.GetFStopAttr().Set(2.8)           # shallow DOF

# Animate the camera — EXPLICIT time samples required
UsdGeom.XformCommonAPI(camera).SetTranslate(Gf.Vec3d(0, 5, 20), time=1)
UsdGeom.XformCommonAPI(camera).SetTranslate(Gf.Vec3d(10, 5, 15), time=48)
```

### Exam Traps

| Wrong statement | Correct fact |
|-----------------|-------------|
| "Sensor size is in inches" | Sensor size is in **millimetres** |
| "clippingRange is handled externally by the renderer" | `clippingRange` IS in the schema |
| "fStop controls exposure time" | `fStop` controls **depth of field** only |
| "Camera auto-updates from animation clips" | Requires **explicit time samples** |
| "Only perspective is supported" | Both **perspective and orthographic** exist |

---

## 8. Key Takeaways

| Concept | What to Remember |
|---------|-----------------|
| **UsdGeomImageable** | Base class for all renderable prims. Provides visibility and purpose ONLY. |
| **Purpose tokens** | render, proxy, guide, default. Guide = NEVER rendered. |
| **Visibility inheritance** | Parent invisible → all children invisible, regardless of their own setting |
| **faceVertexIndices length** | = SUM of faceVertexCounts. Not point count. Not face count. |
| **holeIndices** | Marks faces as holes — exist in topology, NOT rendered |
| **UVs not auto-generated** | Must author `primvars:st` explicitly |
| **Primvar interpolation** | constant, uniform, vertex, faceVarying. NOT "indexed". |
| **inputs: and outputs:** | NOT deprecated. inputs = data IN. outputs = data OUT. Any type. |
| **MaterialBindingAPI** | Must `Apply()` before `Bind()` — both steps required |
| **falloffRadius** | Controls max light range. NOT brightness. |
| **SphereLight radius** | Controls shadow softness and spread. NOT brightness. |
| **Shadows not automatic** | Requires explicit shadow attribute configuration |
| **Camera projections** | Only `perspective` and `orthographic`. No others. |
| **Sensor size** | Always in millimetres. Never inches. |
| **clippingRange** | IS in UsdGeomCamera schema. NOT handled externally. |
| **fStop** | Controls depth of field only. NOT exposure time. |

---

*Previous: [Day 5 — Schemas and Data Modeling](day-05-schemas-and-data-modeling.md)*  
*Next: [Day 7 — Pipeline Development and Data Exchange](day-07-pipeline-and-data-exchange.md)*
