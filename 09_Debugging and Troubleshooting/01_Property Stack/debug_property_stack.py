"""
Debug Exercise — PropertyStack
================================
Find which layer is winning a value and why.

TOPIC: attr.GetPropertyStack()
WHEN TO USE: A property shows the wrong value. You need to find
             which layer is responsible.

THE RULE: PropertyStack returns specs ordered strongest → weakest.
          The FIRST spec in the list is the winner.
          Its value is what attr.Get() returns.

Run: python debug_property_stack.py
"""

from pxr import Usd, UsdGeom, Sdf, Gf
import os

SEP = "=" * 65

# ── BUILD A STAGE WITH TWO LAYERS ──────────────────────────────────
root         = Sdf.Layer.CreateAnonymous("root.usda")
strong_layer = Sdf.Layer.CreateAnonymous("strong_override.usda")
weak_layer   = Sdf.Layer.CreateAnonymous("weak_layout.usda")

root.subLayerPaths = [strong_layer.identifier, weak_layer.identifier]
stage = Usd.Stage.Open(root)

# ── AUTHOR DIRECTLY INTO EACH LAYER VIA SdfLayer API ────────────────
# Weak layer: DEF a Sphere so the prim actually exists and shows in usdview
# Over-only prims have no type and no geometry — invisible in usdview
with Sdf.ChangeBlock():
    # /World must be a def Xform so the hierarchy shows in usdview
    world_spec = Sdf.CreatePrimInLayer(weak_layer, "/World")
    world_spec.specifier = Sdf.SpecifierDef
    world_spec.typeName  = "Xform"
    weak_prim_spec = Sdf.CreatePrimInLayer(weak_layer, "/World/Chair")
    weak_prim_spec.specifier = Sdf.SpecifierDef   # def = owns the prim
    weak_prim_spec.typeName  = "Sphere"            # gives visible geometry
    attr_spec_weak = Sdf.AttributeSpec(
        weak_prim_spec, "chair:brightness", Sdf.ValueTypeNames.Float
    )
    attr_spec_weak.default = 0.5

# Strong layer: OVER — sparse override on top of the def
with Sdf.ChangeBlock():
    strong_prim_spec = Sdf.CreatePrimInLayer(strong_layer, "/World/Chair")
    strong_prim_spec.specifier = Sdf.SpecifierOver  # over = overrides without owning
    attr_spec_strong = Sdf.AttributeSpec(
        strong_prim_spec, "chair:brightness", Sdf.ValueTypeNames.Float
    )
    attr_spec_strong.default = 99.0

    ###Solution: Either remove the opinion from strong_override.usda or update it to the correct value 0.5.

# ── VERIFY BOTH LAYERS HAVE THE SPEC ────────────────────────────────
print(SEP)
print("  STEP 0 — Verify both layers have the attribute spec")
print(SEP)
for layer in [strong_layer, weak_layer]:
    spec = layer.GetAttributeAtPath("/World/Chair.chair:brightness")
    name = os.path.basename(layer.identifier)
    val  = spec.default if spec else "NOT FOUND"
    print(f"  {name:<35} spec default = {val}")

# ── STEP 1: OBSERVE THE PROBLEM ─────────────────────────────────────
print()
print(SEP)
print("  STEP 1 — Observe the wrong value")
print(SEP)

prim = stage.GetPrimAtPath("/World/Chair")
attr = prim.GetAttribute("chair:brightness")
print(f"\n  prim.GetTypeName() = '{prim.GetTypeName()}'  (Sphere — visible in usdview)")
print(f"\n  attr.Get()  = {attr.Get()}")
print(f"  Expected      0.5")
print(f"  Something is wrong. Let's find which layer is responsible.\n")

# ── STEP 2: PROPERTYSTACK ────────────────────────────────────────────
print(SEP)
print("  STEP 2 — Call GetPropertyStack()")
print(SEP)

stack = attr.GetPropertyStack(Usd.TimeCode.Default())

print(f"\n  Number of specs in PropertyStack: {len(stack)}")
print(f"\n  PropertyStack (strongest → weakest):\n")
print(f"  {'Index':<7} {'Layer':<35} {'Value':<12} Note")
print("  " + "-" * 78)

for i, spec in enumerate(stack):
    layer_name = os.path.basename(spec.layer.identifier)
    note = "<── WINNER (this is what Get() returns)" if i == 0 else ""
    print(f"  [{i}]    {layer_name:<35} {str(spec.default):<12} {note}")

print(f"""
  RESULT:
  Index 0 = strong_override.usda  value=99.0  ← WINNER  (over spec)
  Index 1 = weak_layout.usda      value=0.5   ← overridden  (def spec)

  strong_override is at index 0 = strongest position.
  Its value 99.0 wins over weak_layout's 0.5.
  Note: the PrimStack would show weak_layout as 'def' and
        strong_override as 'over' — over beats def when it's stronger.

  FIX: Remove the opinion from strong_override.usda
       OR update it to the correct value 0.5.
""")

# ── STEP 3: NOTE ON TRANSFORM ATTRIBUTES ────────────────────────────
print(SEP)
print("  STEP 3 — Note on transform / time-sampled attributes")
print(SEP)
print("""
  This exercise used a plain float attribute so spec.default prints
  cleanly. Transform attributes (xformOp:translate etc.) set via
  XformCommonAPI store as TIME SAMPLES, not a default value.

  For time-sampled attributes:
    spec.default                 → None  (no plain default)
    spec.GetInfo("timeSamples")  → {time: value} dict

  The PropertyStack itself works the same way — strongest spec
  at index 0 still wins. You just read the value differently:

    for i, spec in enumerate(stack):
        default = spec.default
        ts      = spec.GetInfo("timeSamples")
        value   = default if default is not None else ts
        print(f"[{i}] {value}")
""")

# ── STEP 4: HasAuthoredValue ─────────────────────────────────────────
print(SEP)
print("  STEP 4 — HasAuthoredValue()")
print(SEP)
print(f"""
  attr.HasAuthoredValue() = {attr.HasAuthoredValue()}
  True  = someone explicitly Set() this — intentional value
  False = value comes from schema fallback — nobody touched it

  Critical for: "is this 0.0 because someone set it,
  or because 0.0 is just the schema default?"
""")

# ── STEP 5: THE FULL PATTERN ─────────────────────────────────────────
print(SEP)
print("  STEP 5 — The debugging pattern to memorise")
print(SEP)
print("""
  When a property has the wrong value:

  1.  attr.Get()
      → What is the composed (winning) value?

  2.  attr.GetPropertyStack(Usd.TimeCode.Default())
      → Which layers have opinions? Who is at index 0?

  3.  stack[0].layer.identifier
      → That is the culprit layer.

  4.  attr.HasAuthoredValue()
      → Was this explicitly Set() or just a schema fallback?

  5.  If culprit is the session layer:
      stage.GetSessionLayer().Clear()
      → Removes all session layer opinions
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How to debug this same issue visually")
print(SEP)
print("""
  The Python PropertyStack maps directly to the usdview LayerStack tab.
  Here is the exact usdview workflow for this scenario:

  1. Open usdview:
     .\\scripts\\usdview.bat debug_property_stack.usda

  2. Click /World/Chair in the Scenegraph panel (left)
     You will see a SPHERE — it has geometry because weak_layout
     defined it as a Sphere (def Sphere). strong_override only
     adds an over on top, it doesn't own the geometry.

  3. In the Properties panel find 'chair:brightness'
     You will see: 99.0  ← the wrong value

  4. Open the Metadata/Composition panel → LayerStack tab
     You will see:

     [0] strong_override.usda   chair:brightness = 99.0  ← WINNER
     [1] weak_layout.usda       chair:brightness = 0.5

     This is the VISUAL equivalent of GetPropertyStack().
     The first row = stack[0] = the culprit.

  5. Open the Layers panel (View → Layers)
     Toggle strong_override.usda OFF
     Watch chair:brightness change to 0.5 in the Properties panel
     This is the VISUAL equivalent of stage.MuteLayer().
     When the wrong value disappears → that layer is the culprit.
""")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── SAVE EACH LAYER AS A REAL FILE ───────────────────────────────────
# stage.Export() flattens everything into ONE layer — sublayer structure
# is lost and usdview would only show one layer in the LayerStack tab.
# Instead we save each layer as its own file and wire them via subLayerPaths
# so usdview sees all three layers independently.

path_strong = os.path.join(SCRIPT_DIR, "debug_ps_strong_override.usda")
path_weak   = os.path.join(SCRIPT_DIR, "debug_ps_weak_layout.usda")
path_root   = os.path.join(SCRIPT_DIR, "debug_property_stack.usda")

# Delete existing files first — Sdf.Layer.CreateNew returns None if file exists
for p in [path_strong, path_weak, path_root]:
    if os.path.exists(p):
        os.remove(p)

strong_layer.Export(path_strong)
weak_layer.Export(path_weak)

# Build a new root layer that sublayers the two saved files
# subLayerPaths must use just filenames so they resolve relative to root
root_out = Sdf.Layer.CreateNew(path_root)
root_out.subLayerPaths = [
    os.path.basename(path_strong),
    os.path.basename(path_weak),
]
root_out.Save()

print(f"  Saved layers:")
print(f"    {path_root}         (root — open this in usdview)")
print(f"    {path_strong}")
print(f"    {path_weak}")
print(f"  Open in usdview:")
print(f"    .\\scripts\\usdview.bat {path_root}")
print(f"\n  In usdview:")
print(f"    1. Press F to frame the sphere")
print(f"    2. Click /World/Chair in Scenegraph")
print(f"    3. Properties panel → chair:brightness = 99.0 (wrong)")
print(f"    4. Metadata/Composition → LayerStack tab")
print(f"       → See strong_override at top")
print(f"    5. View → Layers → toggle strong_override off")
print(f"       → Watch value change to 0.5")