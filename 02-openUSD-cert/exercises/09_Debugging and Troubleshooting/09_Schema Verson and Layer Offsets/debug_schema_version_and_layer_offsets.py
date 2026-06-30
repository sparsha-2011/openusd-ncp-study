"""
Debug Exercise — Schema Version Validation + Layer Offsets
============================================================
Two advanced debugging topics from the real exam.

TOPIC 1: Schema version mismatches across layers
TOPIC 2: Layer offsets affecting time-based composition

WHEN TO USE:
  Schema versions: Unexpected attribute behaviour when layers come from
                   different pipeline versions or USD releases.
  Layer offsets:   Animation appears at the wrong time code after referencing.

Run: python debug_schema_version_and_layer_offsets.py
"""

from pxr import Usd, UsdGeom, Sdf, Gf
import os

SEP = "=" * 65

# ══════════════════════════════════════════════════════════════════
# TOPIC 1 — SCHEMA VERSION VALIDATION
# ══════════════════════════════════════════════════════════════════
print(SEP)
print("  TOPIC 1 — Schema Version Validation")
print(SEP)
print("""
  SCENARIO:
  Two layers were authored with different pipeline schema versions.
  Old version used attribute name "shader:roughness".
  New version renamed it to "inputs:roughness".
  When composed, the layers don't agree on attribute names.
  The result is unexpected or missing values.
""")

# Use real files — anonymous layers cannot be saved or used as references
import os as _os
_SD = _os.path.dirname(_os.path.abspath(__file__))
_old_path = _os.path.join(_SD, "debug_sv_old_pipeline_v1.usda")
_new_path = _os.path.join(_SD, "debug_sv_new_pipeline_v2.usda")
for _p in [_old_path, _new_path]:
    if _os.path.exists(_p): _os.remove(_p)

# Simulate old-schema layer — predates version tagging, no customLayerData
old_stage = Usd.Stage.CreateNew(_old_path)
shader_old = old_stage.DefinePrim("/Looks/Mat/Shader")
shader_old.CreateAttribute(
    "shader:roughness", Sdf.ValueTypeNames.Float).Set(0.3)
# customLayerData deliberately NOT set — this layer was authored before
# the pipeline adopted version tagging. We have no way to know its version
# from metadata alone — must inspect attribute names manually.
old_stage.GetRootLayer().Save()
old_layer = old_stage.GetRootLayer()

# Simulate new-schema layer — properly tagged with version metadata
new_stage = Usd.Stage.CreateNew(_new_path)
shader_new = new_stage.DefinePrim("/Looks/Mat/Shader")
shader_new.CreateAttribute(
    "inputs:roughness", Sdf.ValueTypeNames.Float).Set(0.5)
# customLayerData is a dict stored in the layer metadata block
# In USDA it appears at the top:
#   #usda 1.0
#   (
#       customLayerData = {
#           string "pipeline:schemaVersion" = "2.0"
#           string "pipeline:studio" = "AcmeStudios"
#       }
#   )
# Set it via Python:
new_stage.GetRootLayer().customLayerData = {
    "pipeline:schemaVersion": "2.0",
    "pipeline:studio":        "AcmeStudios",
    "pipeline:exportTool":    "MayaExporter_v2",
}
new_stage.GetRootLayer().Save()
new_layer = new_stage.GetRootLayer()

# Compose them via a root layer with sublayers
root = Sdf.Layer.CreateAnonymous("shot.usda")
root.subLayerPaths = [_new_path, _old_path]
stage = Usd.Stage.Open(root)

shader = stage.GetPrimAtPath("/Looks/Mat/Shader")

print(f"  Attributes on composed shader prim:")
for prop in shader.GetProperties():
    val = prop.Get() if hasattr(prop, 'Get') else '(relationship)'
    print(f"    {prop.GetName():<30} = {val}")

print(f"""
  RESULT: BOTH attributes exist on the prim simultaneously.
  'shader:roughness'  = 0.3   (old schema name)
  'inputs:roughness'  = 0.5   (new schema name)
  The renderer uses ONE of these — likely 'inputs:roughness'.
  The old value (0.3) silently has no effect.

  HOW TO CHECK SCHEMA VERSIONS:
""")

# ── READ customLayerData from each layer ────────────────────────────
# customLayerData is a plain Python dict — use .get() with a default
# to safely read keys that may not exist on older layers
print(f"  {'Layer':<35} {'SchemaVersion':<25} {'Studio':<20} {'Tool'}")
print("  " + "-" * 90)
for layer in [new_layer, old_layer]:
    lname   = os.path.basename(layer.identifier)
    custom  = layer.customLayerData   # returns {} if nothing was set
    version = custom.get("pipeline:schemaVersion",
                         "NOT SET — predates version tracking")
    studio  = custom.get("pipeline:studio",     "NOT SET")
    tool    = custom.get("pipeline:exportTool", "NOT SET")
    print(f"  {lname:<35} {version:<25} {studio:<20} {tool}")

print(f"""
  WHAT THIS TELLS YOU:
  new_pipeline_v2.usda → version=2.0, studio known, tool known
    → This layer was authored with a compliant pipeline tool.
    → You know exactly what naming conventions to expect.

  old_pipeline_v1.usda → ALL "NOT SET"
    → This layer predates version tagging.
    → You cannot determine its schema version from metadata alone.
    → Must inspect attribute names manually to detect the old convention.
    → Example: seeing 'shader:roughness' instead of 'inputs:roughness'
      tells you this is a v1 layer even without metadata.

  HOW TO SET customLayerData WHEN AUTHORING:
    layer.customLayerData = {{
        "pipeline:schemaVersion": "2.0",
        "pipeline:studio":        "AcmeStudios",
        "pipeline:exportTool":    "MayaExporter_v2",
    }}
  Set this on EVERY layer your pipeline authors so future
  debugging can identify the layer's origin and version.

  HOW TO READ IT:
    custom  = layer.customLayerData       # returns {{}} if nothing set
    version = custom.get("pipeline:schemaVersion", "unknown")
    # .get() is safe — never throws KeyError even on old layers
""")

print(f"""
  PREVENTION:
  1. Set pipeline version in customLayerData at authoring time:
     layer.customLayerData = {{"pipeline:schemaVersion": "2.0"}}

  2. Run usdchecker across all layers before delivery:
     usdchecker scene.usda
     [WARNING] Layer uses deprecated attribute names

  3. Write migration scripts when renaming schema attributes:
     scan all layers, find old names, rename to new names
""")


# ══════════════════════════════════════════════════════════════════
# TOPIC 2 — LAYER OFFSETS AND TIME COMPOSITION
# ══════════════════════════════════════════════════════════════════
print(SEP)
print("  TOPIC 2 — Layer Offsets Affecting Time-Based Composition")
print(SEP)
print("""
  SCENARIO:
  You reference an animation. Its keyframe is at time=10.
  But in the composed stage it appears at time=120.
  The layer offset on the reference is transforming the time.

  FORMULA: composed_time = (source_time × scale) + offset
""")

# Build the referenced animation
# Must use a real file path — anonymous layers cannot be saved to disk
import os as _os
SCRIPT_DIR_ANIM = _os.path.dirname(_os.path.abspath(__file__))
anim_path = _os.path.join(SCRIPT_DIR_ANIM, "debug_lo_walk_cycle.usda")
if _os.path.exists(anim_path):
    _os.remove(anim_path)

anim_stage = Usd.Stage.CreateNew(anim_path)
char = UsdGeom.Xform.Define(anim_stage, "/Character").GetPrim()

# Keyframe at source time 10
translate_attr = char.CreateAttribute(
    "xformOp:translate", Sdf.ValueTypeNames.Double3)
char.CreateAttribute(
    "xformOpOrder", Sdf.ValueTypeNames.TokenArray).Set(["xformOp:translate"])
translate_attr.Set(Gf.Vec3d(0, 0, 0),  time=1)
translate_attr.Set(Gf.Vec3d(5, 0, 0),  time=10)
translate_attr.Set(Gf.Vec3d(10, 0, 0), time=20)
anim_stage.GetRootLayer().Save()

# Build the shot that references the animation WITH an offset
shot_stage = Usd.Stage.CreateInMemory()
shot_stage.SetMetadata("timeCodesPerSecond", 24)

char_in_shot = shot_stage.DefinePrim("/World/Character")

# Reference with offset=100, scale=2.0
# composed_time = (source_time * 2.0) + 100
ref_with_offset = Sdf.Reference(
    assetPath=anim_path,           # real file path — not anonymous identifier
    primPath=Sdf.Path("/Character"),
    layerOffset=Sdf.LayerOffset(offset=100.0, scale=2.0)
)
char_in_shot.GetReferences().AddReference(ref_with_offset)

# Check where the keyframe appears in the composed stage
composed_char = shot_stage.GetPrimAtPath("/World/Character")
attr_composed = composed_char.GetAttribute("xformOp:translate")

# The source keyframe was at time=10
# With offset=100, scale=2.0: composed = (10 × 2.0) + 100 = 120
source_time = 10.0
offset = 100.0
scale = 2.0
expected_composed_time = (source_time * scale) + offset

print(f"  Source animation keyframe at:     time = {source_time}")
print(f"  Layer offset: offset={offset}, scale={scale}")
print(f"  Formula: ({source_time} × {scale}) + {offset} = {expected_composed_time}")
print(f"  Expected composed time:           time = {expected_composed_time}")

time_samples = attr_composed.GetTimeSamples()
print(f"\n  Actual time samples in composed stage: {time_samples}")

# Show values at various composed times
print(f"\n  Values at key times in composed stage:")
for t in [100, 120, 140]:
    val = attr_composed.Get(time=t)
    print(f"    time={t:<6} → {val}")

print(f"""
  RESULT:
  The keyframe from time=10 in the source appears at time=120
  in the composed stage — exactly as the formula predicts.

  BUG PATTERN:
  "Animation appears at the wrong time" →
  First thing to check: layer offset on the reference arc.

  HOW TO CHECK LAYER OFFSETS:
  Look at the prim's PrimStack:
    for spec in prim.GetPrimStack():
        print(spec.layer.identifier)
  The layer offset is stored on the reference arc itself.
  Inspect the USDA — look for:
    prepend references = @./walk_cycle.usda@  (offset = 100, scale = 2)

  EXAM KEY POINT:
  "Ignoring layer offsets as they do not affect composition" → WRONG
  Layer offsets DO affect time-varying data composition.
  Always check layer offsets when debugging animation timing issues.
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How to spot schema version and layer offset issues")
print(SEP)
print("""
  SCHEMA VERSION MISMATCH in usdview:

  1. .\\scripts\\usdview.bat debug_schema_version.usda

  2. Click /Looks/Mat/Shader in Scenegraph

  3. Properties panel — you will see BOTH attribute names:
     shader:roughness  = 0.3   (old schema name)
     inputs:roughness  = 0.5   (new schema name)
     Both exist simultaneously on the same prim.
     The renderer will use 'inputs:roughness' and ignore the old one.
     The old value (0.3) has no effect — silently wrong.

  4. This is the visual equivalent of checking all property names
     via prim.GetProperties() in Python.
     When you see two attributes that look like duplicates
     with different naming conventions — schema version mismatch.

  LAYER OFFSET (ANIMATION TIMING) in usdview:

  5. .\\scripts\\usdview.bat debug_layer_offset.usda

  6. Open the Timeline (View → Timeline or bottom panel)
     Press PLAY — watch the character move.

  7. The animation starts at time=100 not time=1
     (because layer offset=100 shifted everything forward)

  8. Scrub to time=120 — character is at maximum travel position
     (source keyframe at time=10, composed at (10×2)+100=120)

  9. In the Properties panel scrub the timeline:
     time=100 → translate = (0,0,0)   source time=1 after offset
     time=120 → translate = (5,0,0)   source time=10 after offset
     time=140 → translate = (10,0,0)  source time=20 after offset

  If you expected the keyframe at time=10 but see it at time=120:
  → Check the USDA file for layer offset values on the reference arc:
    prepend references = @./walk_cycle.usda@ (offset=100, scale=2)
""")

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Export schema version stage — save with sublayer structure intact
# root layer just points to the two real layer files
out_schema = os.path.join(SCRIPT_DIR, "debug_schema_version.usda")
if os.path.exists(out_schema): os.remove(out_schema)
schema_root = Sdf.Layer.CreateNew(out_schema)
schema_root.subLayerPaths = [
    os.path.basename(_new_path),
    os.path.basename(_old_path),
]
schema_root.Save()
print(f"  Schema version stage saved → {out_schema}")

# Export layer offset stage — shot_stage references the real walk cycle file
# Export flattens but that is fine here — we just want to see the animation
out_offset = os.path.join(SCRIPT_DIR, "debug_layer_offset.usda")
if os.path.exists(out_offset): os.remove(out_offset)
shot_stage.Export(out_offset)
print(f"  Layer offset stage saved → {out_offset}")
print(f"  (walk cycle source: {anim_path})")

print(f"""
  Open in usdview:
    .\\scripts\\usdview.bat {out_schema}
    → Click /Looks/Mat/Shader → Properties panel
    → See both 'shader:roughness' and 'inputs:roughness' coexisting

    .\\scripts\\usdview.bat {out_offset}
    → Open Timeline → Press Play
    → Animation starts at time=100 not time=1
    → Scrub to time=120 to see the keyframe from source time=10
""")