"""
USD Shaders — Complete Runnable Example
=========================================
This script builds THREE materials of increasing complexity
so you can see exactly how shaders connect together.

  MATERIAL 1 — flat colour (simplest possible shader)
  MATERIAL 2 — PBR with roughness and metallic controls
  MATERIAL 3 — texture-driven (the full three-node chain)

All three are bound to separate spheres in one scene.
Open the output in usdview to see the difference.

KEY CONCEPTS:
  Shader    = a prim with info:id that identifies the shading function
  Material  = a container prim that holds the shader network
  inputs:   = the arguments fed INTO the shader
  outputs:  = the result coming OUT of the shader
  .connect  = a connection between two shader nodes

The chain for a textured material:
  UsdPrimvarReader → UsdUVTexture → UsdPreviewSurface → Material output

Run: python shader_demo.py
Then open in usdview: .\\scripts\\usdview.bat shader_demo.usda
Press F to frame geometry.
"""

import os
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "shader_demo.usda")

stage = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 0.01)

# A scope to hold all our materials — convention is /Looks
looks = stage.DefinePrim("/Looks", "Scope")


# ═══════════════════════════════════════════════════════════════════════
# MATERIAL 1 — Flat colour
# The absolute minimum shader setup
# One Material + one Shader. No textures. No readers.
# ═══════════════════════════════════════════════════════════════════════

# Step 1: Create the Material container
mat1 = UsdShade.Material.Define(stage, "/Looks/RedPlastic")
# Material is just a container — it holds the shader network
# The renderer looks at Material.outputs:surface to find the network

# Step 2: Create the surface Shader INSIDE the Material
# Convention: shaders always live as children of their Material
shader1 = UsdShade.Shader.Define(stage, "/Looks/RedPlastic/PBRShader")

# Step 3: Set info:id — this tells the renderer WHICH shader to use
shader1.CreateIdAttr("UsdPreviewSurface")
# "UsdPreviewSurface" is the standard PBR shader
# The renderer finds its implementation and runs it

# Step 4: Set shader inputs — these are the function arguments
shader1.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
    Gf.Vec3f(0.8, 0.1, 0.1)   # red
)
shader1.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
shader1.CreateInput("metallic",  Sdf.ValueTypeNames.Float).Set(0.0)
# Any input you DON'T set uses the schema fallback value
# diffuseColor default = (0.18, 0.18, 0.18) grey
# roughness default    = 0.5
# metallic default     = 0.0

# Step 5: Connect Material output → Shader output
# This tells the renderer "the surface shading comes from this shader"
mat1.CreateSurfaceOutput().ConnectToSource(
    shader1.ConnectableAPI(), "surface"
)
# In USDA this produces:
#   token outputs:surface.connect = </Looks/RedPlastic/PBRShader.outputs:surface>

print("Material 1 (RedPlastic) created")
print(f"  info:id      = {shader1.GetIdAttr().Get()}")
print(f"  diffuseColor = {shader1.GetInput('diffuseColor').Get()}")
print(f"  roughness    = {shader1.GetInput('roughness').Get()}")
print()


# ═══════════════════════════════════════════════════════════════════════
# MATERIAL 2 — PBR metallic sphere
# Same structure but different input values
# Shows how inputs completely change the surface appearance
# ═══════════════════════════════════════════════════════════════════════

mat2 = UsdShade.Material.Define(stage, "/Looks/GoldMetal")

shader2 = UsdShade.Shader.Define(stage, "/Looks/GoldMetal/PBRShader")
shader2.CreateIdAttr("UsdPreviewSurface")

# Same shader type — totally different look just from input values
shader2.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
    Gf.Vec3f(1.0, 0.75, 0.0)  # gold colour
)
shader2.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.1)
# low roughness = mirror-like surface
shader2.CreateInput("metallic",  Sdf.ValueTypeNames.Float).Set(1.0)
# metallic=1.0 = full metal — completely changes how light interacts

mat2.CreateSurfaceOutput().ConnectToSource(
    shader2.ConnectableAPI(), "surface"
)

print("Material 2 (GoldMetal) created")
print(f"  diffuseColor = {shader2.GetInput('diffuseColor').Get()}")
print(f"  roughness    = {shader2.GetInput('roughness').Get()}  (low = shiny)")
print(f"  metallic     = {shader2.GetInput('metallic').Get()}   (1.0 = full metal)")
print()


# ═══════════════════════════════════════════════════════════════════════
# MATERIAL 3 — Texture-driven (the full three-node chain)
# UsdPrimvarReader → UsdUVTexture → UsdPreviewSurface
#
# Note: this uses a procedural checkerboard texture via UsdPreviewSurface
# so it works without an actual image file on disk
# ═══════════════════════════════════════════════════════════════════════

mat3 = UsdShade.Material.Define(stage, "/Looks/CheckerMat")

# ── NODE 1: Surface shader (UsdPreviewSurface) ───────────────────────
# We create this first so we can connect to it last
surface3 = UsdShade.Shader.Define(stage, "/Looks/CheckerMat/Surface")
surface3.CreateIdAttr("UsdPreviewSurface")
surface3.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
surface3.CreateInput("metallic",  Sdf.ValueTypeNames.Float).Set(0.0)
# diffuseColor will be CONNECTED from the texture — not set directly

# ── NODE 2: Texture reader (UsdUVTexture) ────────────────────────────
# This node reads a texture file and outputs colour values
texture3 = UsdShade.Shader.Define(stage, "/Looks/CheckerMat/Texture")
texture3.CreateIdAttr("UsdUVTexture")

# The texture file — using a simple built-in pattern
# In a real pipeline this would be @./textures/wood.png@
texture3.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(
    "checker.png"
    # Note: this file doesn't need to exist for the USDA to be valid
    # In usdview it will just show the fallback colour
)
texture3.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
texture3.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")

# UsdUVTexture has three outputs: rgb, r, g, b, a
# We'll use the rgb output to drive diffuseColor
tex_rgb_output = texture3.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

# ── NODE 3: UV coordinate reader (UsdPrimvarReader_float2) ───────────
# This node reads the mesh's UV coordinates (primvars:st)
# and feeds them into the texture so it knows where to sample
uv_reader3 = UsdShade.Shader.Define(stage, "/Looks/CheckerMat/UVReader")
uv_reader3.CreateIdAttr("UsdPrimvarReader_float2")

# inputs:varname = which primvar to read (without the primvars: prefix)
uv_reader3.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
# This reads primvars:st from the mesh geometry
# "st" is the conventional name for UV coordinates in USD

uv_output = uv_reader3.CreateOutput("result", Sdf.ValueTypeNames.Float2)

# ── CONNECT THE NODES ────────────────────────────────────────────────
# Connection 1: UVReader.outputs:result → Texture.inputs:st
texture3.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(uv_output)
# "Give the texture these UV coordinates to use for sampling"

# Connection 2: Texture.outputs:rgb → Surface.inputs:diffuseColor
surface3.CreateInput(
    "diffuseColor", Sdf.ValueTypeNames.Color3f
).ConnectToSource(tex_rgb_output)
# "Use the texture colour as the surface base colour"

# ── CONNECT MATERIAL OUTPUT → SURFACE SHADER ────────────────────────
mat3.CreateSurfaceOutput().ConnectToSource(
    surface3.ConnectableAPI(), "surface"
)

print("Material 3 (CheckerMat) created — full three-node chain:")
print("  UVReader → Texture → Surface → Material")
print(f"  UVReader varname = {uv_reader3.GetInput('varname').Get()}")
print(f"  Texture wrapS    = {texture3.GetInput('wrapS').Get()}")
print(f"  Surface roughness= {surface3.GetInput('roughness').Get()}")
print()


# ═══════════════════════════════════════════════════════════════════════
# CREATE THREE SPHERES AND BIND EACH MATERIAL
# ═══════════════════════════════════════════════════════════════════════

def make_sphere(stage, path, position, radius=2.0):
    """Helper — create a sphere with UV coordinates for texturing."""
    sphere = UsdGeom.Sphere.Define(stage, path)
    sphere.GetRadiusAttr().Set(radius)
    UsdGeom.XformCommonAPI(sphere).SetTranslate(position)
    return sphere

# Sphere 1 — Red plastic (left)
sphere1 = make_sphere(stage, "/World/Sphere_RedPlastic",  Gf.Vec3d(-7, 0, 0))
UsdShade.MaterialBindingAPI.Apply(sphere1.GetPrim()).Bind(mat1)
# Apply() applies the MaterialBindingAPI schema to the prim
# Bind() creates:  rel material:binding = </Looks/RedPlastic>

# Sphere 2 — Gold metal (centre)
sphere2 = make_sphere(stage, "/World/Sphere_GoldMetal",   Gf.Vec3d(0, 0, 0))
UsdShade.MaterialBindingAPI.Apply(sphere2.GetPrim()).Bind(mat2)

# Sphere 3 — Checker texture (right)
sphere3 = make_sphere(stage, "/World/Sphere_CheckerMat",  Gf.Vec3d(7, 0, 0))
UsdShade.MaterialBindingAPI.Apply(sphere3.GetPrim()).Bind(mat3)

print("Three spheres created and materials bound:")
print("  LEFT   /World/Sphere_RedPlastic  → /Looks/RedPlastic")
print("  CENTRE /World/Sphere_GoldMetal   → /Looks/GoldMetal")
print("  RIGHT  /World/Sphere_CheckerMat  → /Looks/CheckerMat")
print()


# ═══════════════════════════════════════════════════════════════════════
# VERIFY MATERIAL BINDINGS
# ═══════════════════════════════════════════════════════════════════════
print("=== VERIFYING MATERIAL BINDINGS ===")
for path in ["/World/Sphere_RedPlastic",
             "/World/Sphere_GoldMetal",
             "/World/Sphere_CheckerMat"]:
    prim = stage.GetPrimAtPath(path)
    bound_mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    print(f"  {path}")
    print(f"    → bound to: {bound_mat.GetPath()}")
print()


# ═══════════════════════════════════════════════════════════════════════
# PRINT THE USDA — read the shader network structure
# Look for:
#   uniform token info:id = "UsdPreviewSurface"
#   uniform token info:id = "UsdUVTexture"
#   uniform token info:id = "UsdPrimvarReader_float2"
#   inputs:diffuseColor = (...)        ← hardcoded value
#   color3f inputs:diffuseColor.connect ← connected from texture
#   token outputs:surface.connect       ← Material wired to Shader
# ═══════════════════════════════════════════════════════════════════════
print("=== USDA OUTPUT — read the shader structure ===")
print(stage.ExportToString(addSourceFileComment=False))


# ═══════════════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════════════
stage.Export(OUTPUT)
print(f"✅ Saved → {OUTPUT}")
print()
print("OPEN IN USDVIEW:")
print(f"  .\\scripts\\usdview.bat {OUTPUT}")
print("  Press F to frame all three spheres")
print("  LEFT  = red plastic  (flat colour, roughness=0.4)")
print("  MID   = gold metal   (metallic=1.0, roughness=0.1)")
print("  RIGHT = checker      (texture-driven diffuseColor)")
print()
print("In usdview click a sphere then check the Properties panel")
print("to see the material:binding relationship.")