"""
Debug Exercise — PrimStack
============================
Inspect all layers contributing to a prim — type, specifier, layer.

TOPIC: prim.GetPrimStack()
WHEN TO USE: A prim is missing, has the wrong type, uses the wrong
             specifier, or you need to know which layer "owns" it.

THE RULE: PrimStack returns all SdfPrimSpecs ordered strongest → weakest.
          Each spec shows: which layer, what specifier (def/over/class),
          and what typeName that layer claims.

Run: python debug_prim_stack.py
"""

from pxr import Usd, UsdGeom, Sdf
import os

SEP = "=" * 65

# ── BUILD A STAGE WITH OVERLAPPING LAYER CONTRIBUTIONS ─────────────
root          = Sdf.Layer.CreateAnonymous("root.usda")
override_layer = Sdf.Layer.CreateAnonymous("dept_override.usda")
base_layer    = Sdf.Layer.CreateAnonymous("model_base.usda")

root.subLayerPaths = [override_layer.identifier, base_layer.identifier]
stage = Usd.Stage.Open(root)

# Define /World as Xform so hierarchy is visible in usdview
stage.SetEditTarget(base_layer)
UsdGeom.Xform.Define(stage, "/World")

# Base layer DEFINES the prim — owns it, sets the type
stage.SetEditTarget(base_layer)
UsdGeom.Xform.Define(stage, "/World/Chair")

# Override layer adds a SPARSE OVERRIDE — does not claim ownership
stage.SetEditTarget(override_layer)
stage.OverridePrim("/World/Chair")
prim = stage.GetPrimAtPath("/World/Chair")
# Add a custom attribute via the override
prim.CreateAttribute("pipeline:shotId",
                     Sdf.ValueTypeNames.String).Set("SHOT_042")

stage.SetEditTarget(root)
prim = stage.GetPrimAtPath("/World/Chair")

# ── STEP 1: BASIC PRIM INFO ─────────────────────────────────────────
print(SEP)
print("  STEP 1 — Basic prim information")
print(SEP)
print(f"""
  prim.GetPath()     = {prim.GetPath()}
  prim.GetTypeName() = '{prim.GetTypeName()}'
  prim.IsValid()     = {prim.IsValid()}
  prim.IsDefined()   = {prim.IsDefined()}
  prim.IsActive()    = {prim.IsActive()}
""")

# ── STEP 2: PRIMSTACK ───────────────────────────────────────────────
print(SEP)
print("  STEP 2 — Call GetPrimStack()")
print(SEP)
print(f"\n  Number of specs: {len(prim.GetPrimStack())}\n")
print(f"  {'Index':<7} {'Layer':<32} {'Specifier':<12} {'TypeName':<12} Meaning")
print("  " + "-" * 80)

SPECIFIER_MEANING = {
    Sdf.SpecifierDef:   "owns this prim, sets the type",
    Sdf.SpecifierOver:  "sparse override, no type claim",
    Sdf.SpecifierClass: "abstract class template",
}

for i, spec in enumerate(prim.GetPrimStack()):
    layer_name = os.path.basename(spec.layer.identifier)
    meaning = SPECIFIER_MEANING.get(spec.specifier, "")
    print(f"  [{i}]    {layer_name:<32} {str(spec.specifier):<12} "
          f"'{spec.typeName}'        {meaning}")

print(f"""
  RESULT:
  [0] dept_override.usda  specifier=over  typeName=''
      → Sparse override. Adds data without claiming ownership.
      → typeName is empty — it lets base_layer be the authority.

  [1] model_base.usda     specifier=def   typeName='Xform'
      → Originally defined here. Owns the type definition.
""")

# ── STEP 3: WHAT PRIMSTACK CATCHES ─────────────────────────────────
print(SEP)
print("  STEP 3 — What PrimStack is useful for catching")
print(SEP)
print("""
  SCENARIO A — Unexpected type change:
    You expect typeName='Mesh' but get 'Xform'.
    PrimStack shows two specs: one says def Mesh, one says def Xform.
    The stronger layer (index 0) is wrongly redefining the type.

  SCENARIO B — Missing prim:
    prim.IsDefined() = False means no 'def' spec exists anywhere.
    PrimStack shows only 'over' specs — nobody defined the prim.
    Fix: ensure a 'def' spec exists in at least one layer.

  SCENARIO C — Namespace collision (two assets defining same path):
    PrimStack shows specs from two unrelated layers at the same path.
    Fix: reference each asset at a unique path in the namespace.

  SCENARIO D — Active/inactive:
    PrimStack shows a spec with active=False in a strong layer.
    The prim is deactivated by that layer — it won't appear in traversal.
""")

# ── STEP 4: DEMONSTRATE DEACTIVATION ───────────────────────────────
print(SEP)
print("  STEP 4 — Demonstrate prim deactivation detection")
print(SEP)

# Deactivate the prim via the override layer
stage.SetEditTarget(override_layer)
prim.SetActive(False)
stage.SetEditTarget(root)

prim = stage.GetPrimAtPath("/World/Chair")
print(f"\n  After SetActive(False) in override_layer:")
print(f"  prim.IsActive()    = {prim.IsActive()}")
print(f"  prim.IsValid()     = {prim.IsValid()}")
print(f"""
  A deactivated prim is invisible to stage.Traverse()
  but you can still get it with GetPrimAtPath().

  To find which layer deactivated it:
  Use GetPrimStack() and check spec.HasInfo('active')
  and spec.GetInfo('active') on each spec.
""")

## Troubleshooting: The strongest layer that sets active=False is the culprit.
print(f"  {'Index':<7} {'Layer':<44} {'HasActiveInfo':<12} {'TypeName':<12} ")
print("  " + "-" * 80)
for i, spec in enumerate(prim.GetPrimStack()):
  layer_name = os.path.basename(spec.layer.identifier)
  meaning = SPECIFIER_MEANING.get(spec.specifier, "")
  print(f"  [{i}]    {layer_name:<48} {str(spec.HasInfo('active')):<12} "
          f"'{spec.typeName}'      ")
print()

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How to debug this same issue visually")
print(SEP)
print("""
  The Python PrimStack maps to the usdview LayerStack tab
  AND the Composition tab. Here is the usdview workflow:

  1. Open usdview:
     .\\scripts\\usdview.bat debug_prim_stack.usda

  2. Click /World/Chair in the Scenegraph panel

  3. Metadata/Composition panel → Composition tab
     Shows the full composition arc graph for this prim.
     Every arc (reference, sublayer contribution, variant) is listed.
     This is the visual equivalent of prim.GetPrimIndex().DumpToString().

  4. Metadata/Composition panel → LayerStack tab
     Shows all layers contributing to this prim:

     [0] dept_override.usda   specifier=over  typeName=''
     [1] model_base.usda      specifier=def   typeName='Xform'

     This is the visual equivalent of prim.GetPrimStack().
     An 'over' without a typeName = sparse override (no ownership).
     A 'def' with a typeName = this layer owns the prim.

  5. Metadata/Composition panel → Metadata tab
     Shows all prim metadata: kind, active, instanceable etc.
     If active=false appears here → the prim is deactivated.
     The STRONGEST layer that sets active=false is the culprit.

  USE PRIMSTACK WHEN:
  - A prim is missing from the stage → check if any layer has a 'def'
  - Prim has wrong type → check which layer's 'def' is winning
  - Unexpected data on a prim → check which layers have specs
""")

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

path_override = os.path.join(SCRIPT_DIR, "debug_ps2_dept_override.usda")
path_base     = os.path.join(SCRIPT_DIR, "debug_ps2_model_base.usda")
path_root     = os.path.join(SCRIPT_DIR, "debug_prim_stack.usda")

for p in [path_override, path_base, path_root]:
    if os.path.exists(p): os.remove(p)

override_layer.Export(path_override)
base_layer.Export(path_base)

root_out = Sdf.Layer.CreateNew(path_root)
root_out.subLayerPaths = [
    os.path.basename(path_override),
    os.path.basename(path_base),
]
root_out.Save()

print(f"  Saved → {path_root} (open this in usdview)")
print(f"  Open in usdview:")
print(f"\n  In usdview:")
print(f"    1. Click /World/Chair in Scenegraph")
print(f"    2. Metadata/Composition → LayerStack tab")
print(f"       → See dept_override (over) and model_base (def Xform)")
print(f"    3. Metadata/Composition → Composition tab")
print(f"       → See the full arc graph")
print(f"    4. Metadata/Composition → Metadata tab")
print(f"       → See active=false (prim is deactivated)")