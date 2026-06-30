"""
UsdLux — All 7 Light Types Demo
=================================
Demonstrates all UsdLux light types including the cone/spot light.

LIGHT TYPES:
  1. DistantLight              — sun, parallel rays, infinite distance
  2. SphereLight               — point light from sphere volume
  3. RectLight                 — rectangular softbox area light
  4. DiskLight                 — circular area light
  5. CylinderLight             — tube/neon light along its length
  6. SphereLight + ShapingAPI  — cone / spot light
  7. DomeLight                 — wraps entire scene (separate file)

WHY DOME IS A SEPARATE FILE:
  DomeLight lights the whole scene equally.
  In a scene with 6 other bright lights you cannot see its effect
  on any specific sphere. To see DomeLight properly you need to
  turn all other lights OFF — so this script creates two files:

  lighting_demo.usda      — 6 directional/area lights + cone
  lighting_dome_only.usda — ONLY the DomeLight so you can see it

Run: python lighting_demo.py

Open the main scene:
  .\\scripts\\usdview.bat lighting_demo.usda
  Press F to frame. Click each sphere to see its light.

Open the dome-only scene to see DomeLight:
  .\\scripts\\usdview.bat lighting_dome_only.usda
  Press F — ALL spheres get the same ambient blue wash from the dome
"""

import os
from pxr import Usd, UsdGeom, UsdLux, UsdShade, Gf, Sdf

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── shared material for all spheres ─────────────────────────────────
def build_grey_material(stage):
    mat = UsdShade.Material.Define(stage, "/Looks/GreyMat")
    pbr = UsdShade.Shader.Define(stage, "/Looks/GreyMat/Surface")
    pbr.CreateIdAttr("UsdPreviewSurface")
    pbr.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.7, 0.7, 0.7))
    pbr.CreateInput("roughness",    Sdf.ValueTypeNames.Float).Set(0.4)
    mat.CreateSurfaceOutput().ConnectToSource(pbr.ConnectableAPI(), "surface")
    return mat

# ── helper: create a labelled sphere ────────────────────────────────
def make_sphere(stage, path, x_pos, mat):
    s = UsdGeom.Sphere.Define(stage, path)
    s.GetRadiusAttr().Set(2.0)
    UsdGeom.XformCommonAPI(s).SetTranslate(Gf.Vec3d(x_pos, 0, 0))
    s.GetDisplayColorAttr().Set([(0.7, 0.7, 0.7)])
    UsdShade.MaterialBindingAPI.Apply(s.GetPrim()).Bind(mat)
    return s

# ── helper: ground plane ─────────────────────────────────────────────
def make_ground(stage, mat):
    g = UsdGeom.Cube.Define(stage, "/World/Ground")
    g.GetSizeAttr().Set(1.0)
    UsdGeom.XformCommonAPI(g).SetTranslate(Gf.Vec3d(0, -3, 0))
    UsdGeom.XformCommonAPI(g).SetScale(Gf.Vec3f(140, 0.2, 20))
    g.GetDisplayColorAttr().Set([(0.3, 0.3, 0.3)])
    UsdShade.MaterialBindingAPI.Apply(g.GetPrim()).Bind(mat)


# ═══════════════════════════════════════════════════════════════════════
# FILE 1: lighting_demo.usda
# 6 light types + cone/spot — one sphere per light
# Spheres spaced 20 units apart
# ═══════════════════════════════════════════════════════════════════════
s1 = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(s1, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(s1, 0.01)

mat1 = build_grey_material(s1)
make_ground(s1, mat1)

# Seven spheres — one per light type
positions = [-60, -40, -20, 0, 20, 40, 60]
labels    = ["Distant", "Sphere", "Rect", "Disk", "Cylinder", "Cone", "Dome_ref"]
for label, x in zip(labels, positions):
    make_sphere(s1, f"/World/Sphere_{label}", x, mat1)

lights1 = s1.DefinePrim("/Lights", "Scope")


# ── 1. DistantLight ──────────────────────────────────────────────────
# Sun-like — only rotation matters, position is irrelevant
# Emits along -Z, rotate to aim
distant = UsdLux.DistantLight.Define(s1, "/Lights/DistantLight")
distant.CreateIntensityAttr().Set(5000.0)
distant.CreateAngleAttr().Set(0.53)        # angular size — 0.53 = real sun
distant.CreateColorAttr().Set(Gf.Vec3f(1.0, 0.95, 0.85))  # warm white
UsdGeom.XformCommonAPI(distant).SetTranslate(Gf.Vec3d(-60, 20, 10))
UsdGeom.XformCommonAPI(distant).SetRotate(Gf.Vec3f(-45, 0, 0))
print("1. DistantLight   — parallel rays, only rotation matters")


# ── 2. SphereLight ───────────────────────────────────────────────────
# Point light from a physical sphere — emits in ALL directions
# High intensity needed because it falls off with distance squared
sphere_l = UsdLux.SphereLight.Define(s1, "/Lights/SphereLight")
sphere_l.CreateIntensityAttr().Set(80000.0)
sphere_l.CreateRadiusAttr().Set(0.5)       # small = hard shadows
sphere_l.CreateColorAttr().Set(Gf.Vec3f(1.0, 0.8, 0.6))  # warm bulb
UsdGeom.XformCommonAPI(sphere_l).SetTranslate(Gf.Vec3d(-40, 8, 5))
print("2. SphereLight    — point light, emits all directions, position matters")


# ── 3. RectLight ─────────────────────────────────────────────────────
# Rectangular softbox — emits along -Z
# Larger rectangle = softer more diffuse light
rect = UsdLux.RectLight.Define(s1, "/Lights/RectLight")
rect.CreateIntensityAttr().Set(8000.0)
rect.CreateWidthAttr().Set(6.0)
rect.CreateHeightAttr().Set(6.0)           # 6x6 large softbox
rect.CreateColorAttr().Set(Gf.Vec3f(0.9, 0.95, 1.0))  # cool white studio
UsdGeom.XformCommonAPI(rect).SetTranslate(Gf.Vec3d(-20, 10, 8))
UsdGeom.XformCommonAPI(rect).SetRotate(Gf.Vec3f(-40, 0, 0))
print("3. RectLight      — rectangular area light, emits along -Z")


# ── 4. DiskLight ─────────────────────────────────────────────────────
# Circular area light — like a ring light or circular softbox
# Also emits along -Z
disk = UsdLux.DiskLight.Define(s1, "/Lights/DiskLight")
disk.CreateIntensityAttr().Set(8000.0)
disk.CreateRadiusAttr().Set(3.0)           # radius of the disk
disk.CreateColorAttr().Set(Gf.Vec3f(0.8, 1.0, 0.9))  # slightly green
UsdGeom.XformCommonAPI(disk).SetTranslate(Gf.Vec3d(0, 12, 6))
UsdGeom.XformCommonAPI(disk).SetRotate(Gf.Vec3f(-50, 0, 0))
print("4. DiskLight      — circular area light, emits along -Z")


# ── 5. CylinderLight ─────────────────────────────────────────────────
# Tube/neon strip — emits along its LENGTH not -Z
# This is the EXCEPTION — all other lights emit along -Z
cylinder = UsdLux.CylinderLight.Define(s1, "/Lights/CylinderLight")
cylinder.CreateIntensityAttr().Set(15000.0)
cylinder.CreateLengthAttr().Set(10.0)      # length of the tube
cylinder.CreateRadiusAttr().Set(0.3)       # thickness of the tube
cylinder.CreateColorAttr().Set(Gf.Vec3f(1.0, 0.5, 0.2))  # orange neon
UsdGeom.XformCommonAPI(cylinder).SetTranslate(Gf.Vec3d(20, 8, 0))
print("5. CylinderLight  — tube light, emits along LENGTH (not -Z)")


# ── 6. ConeLight / SpotLight (SphereLight + ShapingAPI) ──────────────
# There is NO separate ConeLight prim type in UsdLux
# A spot/cone light = SphereLight with ShapingAPI applied
# ShapingAPI constrains the emission to a cone shape
cone = UsdLux.SphereLight.Define(s1, "/Lights/ConeLight")
cone.CreateIntensityAttr().Set(100000.0)   # high — constrained to small cone
cone.CreateRadiusAttr().Set(0.3)
cone.CreateColorAttr().Set(Gf.Vec3f(1.0, 1.0, 0.7))  # yellow stage spot

# Apply ShapingAPI — this is what makes it a cone/spot light
shaping = UsdLux.ShapingAPI.Apply(cone.GetPrim())
shaping.CreateShapingConeAngleAttr().Set(20.0)
# half-angle of the cone in degrees
# 20 = tight 40-degree total spread — like a stage spotlight
shaping.CreateShapingConeSoftnessAttr().Set(0.1)
# 0 = hard edge, 1 = very soft gradual falloff
shaping.CreateShapingFocusAttr().Set(5.0)
# concentrates light toward cone centre — higher = more focused beam

# Position above and rotate to aim DOWN at the sphere
UsdGeom.XformCommonAPI(cone).SetTranslate(Gf.Vec3d(40, 15, 0))
UsdGeom.XformCommonAPI(cone).SetRotate(Gf.Vec3f(-90, 0, 0))
# -90 on X = pointing straight down

print("6. ConeLight      — SphereLight + ShapingAPI, cone angle=20 deg")
print("   NOTE: no ConeLight prim exists — ShapingAPI makes the cone")


# ── 7. DomeLight reference sphere ────────────────────────────────────
# Adding a DomeLight here too but low intensity
# The 7th sphere labelled Dome_ref shows ambient contribution
dome_ref = UsdLux.DomeLight.Define(s1, "/Lights/DomeLight_ambient")
dome_ref.CreateIntensityAttr().Set(0.3)    # very low — just ambient fill
dome_ref.CreateColorAttr().Set(Gf.Vec3f(0.4, 0.5, 0.8))  # blue sky
print("7. DomeLight      — low intensity ambient fill for the whole scene")

# Save file 1
path1 = os.path.join(SCRIPT_DIR, "lighting_demo.usda")
s1.Export(path1)
print(f"\nFile 1 saved → {path1}")


# ═══════════════════════════════════════════════════════════════════════
# FILE 2: lighting_dome_only.usda
# ONLY a DomeLight — no other lights
# This shows the DomeLight effect clearly
# All spheres get the SAME ambient light from the dome
# This is how you would see it in a real production scene
# ═══════════════════════════════════════════════════════════════════════
s2 = Usd.Stage.CreateInMemory()
UsdGeom.SetStageUpAxis(s2, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(s2, 0.01)

mat2 = build_grey_material(s2)
make_ground(s2, mat2)

# Three spheres spread out — DomeLight will light them all equally
for label, x in [("Left", -10), ("Centre", 0), ("Right", 10)]:
    make_sphere(s2, f"/World/Sphere_{label}", x, mat2)

# THE ONLY LIGHT — DomeLight wraps the entire scene
dome_only = UsdLux.DomeLight.Define(s2, "/Lights/DomeLight")
dome_only.CreateIntensityAttr().Set(1.0)   # full intensity
dome_only.CreateColorAttr().Set(Gf.Vec3f(0.3, 0.5, 1.0))  # blue sky
# In production: dome_only.CreateTextureFileAttr().Set("./hdri/sky.exr")
# The texture wraps around the entire scene providing realistic IBL

print("\nDomeLight properties:")
print(f"  intensity = {dome_only.GetIntensityAttr().Get()}")
print(f"  color     = {dome_only.GetColorAttr().Get()}")
print("  Lights the ENTIRE scene equally from all directions")
print("  All three spheres get identical ambient blue lighting")
print("  In production: connect an HDRI texture for realistic reflections")

path2 = os.path.join(SCRIPT_DIR, "lighting_dome_only.usda")
s2.Export(path2)
print(f"\nFile 2 saved → {path2}")


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 65)
print("LIGHT TYPE REFERENCE")
print("=" * 65)
print("""
  Type              Prim                  Emits          Position
  ────────────────────────────────────────────────────────────────
  Distant (sun)     DistantLight          Along -Z       IGNORED
  Point             SphereLight           All directions  Matters
  Rectangular       RectLight             Along -Z        Matters
  Circular          DiskLight             Along -Z        Matters
  Tube / neon       CylinderLight         Along LENGTH    Matters
  Cone / spot       SphereLight+Shaping   Cone shape      Matters
  Environment       DomeLight             Entire scene    IGNORED

  ShapingAPI inputs (cone/spot):
    shaping:cone:angle     — half-angle in degrees (smaller = tighter beam)
    shaping:cone:softness  — edge hardness (0=hard, 1=soft)
    shaping:focus          — beam concentration toward centre

  Shared inputs on ALL light types:
    inputs:intensity        — brightness
    inputs:color            — colour tint
    inputs:exposure         — EV exposure (2^exposure × intensity)
""")
print(f"OPEN IN USDVIEW:")
print(f"  6 lights:  .\\scripts\\usdview.bat {path1}")
print(f"  Dome only: .\\scripts\\usdview.bat {path2}")
print()
print("TIP: In the dome-only file press F then look at all three spheres")
print("     They all receive identical ambient lighting from every direction")
print("     That is the key difference — DomeLight has no single direction")