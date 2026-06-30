# Day 5 — Schemas and Data Modeling

> **OpenUSD NCP Certification Study Notes**  
> *USD Schemas, Schema Types, usdGenSchema, Custom Schemas, SdfFileFormat*

---

## Table of Contents

1. [What is a Schema?](#1-what-is-a-schema)
2. [IsA Schemas vs API Schemas](#2-isa-schemas-vs-api-schemas)
3. [Schema Inheritance Hierarchy](#3-schema-inheritance-hierarchy)
4. [Creating Custom Schemas](#4-creating-custom-schemas)
5. [The usdGenSchema Workflow](#5-the-usdgenschema-workflow)
6. [TfType Registration](#6-tftype-registration)
7. [Custom File Format Plugins — SdfFileFormat](#7-custom-file-format-plugins--sdffileformat)
8. [Custom Model Kinds — UsdModelKindRegistry](#8-custom-model-kinds--usdmodelkindregistry)
9. [Key Takeaways](#9-key-takeaways)

---

## 1. What is a Schema?

A **schema** is a formal definition of a prim type — what attributes it has, what their types and default values are, and how it participates in USD's type system. Schemas are what make `UsdGeom.Sphere` a sphere and `UsdLux.DistantLight` a directional light.

USD ships with built-in schemas for common 3D concepts (`Mesh`, `Camera`, `Material`, `DistantLight`). When your pipeline needs a type that doesn't exist in USD — a `TemperatureSensor`, a `ConveyorBelt`, a `ShotCamera` — you create a **custom schema**.

### Why Custom Schemas (vs plain attributes)?

| With custom schema | Without (plain attributes) |
|-------------------|---------------------------|
| `prim.IsA(TemperatureSensor)` works | No type checking |
| Schema fallback values work | No defaults |
| Generated Python and C++ API | Manual attribute access |
| Full usdview introspection | Just arbitrary data |
| Validates at authoring time | Silent errors |

---

## 2. IsA Schemas vs API Schemas

USD has two fundamentally different schema types:

### IsA Schemas (Typed Schemas)

An IsA schema **defines the type of a prim**. It sets the `typeName` metadata. A prim has exactly **one** IsA schema — it IS a Mesh, or it IS a Sphere, not both.

```usda
def Mesh "Chair" {     # typeName = "Mesh" — this prim IS a Mesh
    ...
}
```

```python
prim.IsA(UsdGeom.Mesh)       # True — prim is of type Mesh
prim.GetTypeName()            # "Mesh"
```

### API Schemas

An API schema **augments a prim** with additional properties and behaviours without changing its type. A prim can have **multiple** API schemas applied simultaneously. They are listed in `apiSchemas` metadata.

```usda
def Mesh "Character" (
    prepend apiSchemas = ["PhysicsRigidBodyAPI", "MotionAPI"]
    # Still a Mesh — but with physics and motion APIs applied
) { }
```

```python
prim.HasAPI(UsdPhysics.RigidBodyAPI)   # True
prim.IsA(UsdGeom.Mesh)                 # Still True
```

| Property | IsA Schema | API Schema |
|----------|-----------|-----------|
| Sets `typeName` | ✅ Yes | ❌ No |
| Number per prim | Exactly 1 | Multiple |
| Checking | `prim.IsA()` | `prim.HasAPI()` |
| Declaration in USDA | `def TypeName "name"` | `prepend apiSchemas = [...]` |

---

## 3. Schema Inheritance Hierarchy

All USD schemas ultimately inherit from `UsdSchemaBase`. The hierarchy determines what capabilities a schema inherits.

```
UsdSchemaBase                    ← root of ALL schemas
├── UsdTyped                     ← base for all IsA (typed) schemas
│   ├── UsdGeomImageable         ← all renderable prims (visibility, purpose)
│   │   ├── UsdGeomXformable     ← all transformable prims
│   │   │   ├── UsdGeomGprim     ← all geometric primitives
│   │   │   │   ├── UsdGeomMesh
│   │   │   │   ├── UsdGeomSphere
│   │   │   │   └── ...
│   │   │   ├── UsdGeomCamera
│   │   │   └── UsdLuxLight      ← all lights
│   │   └── ...
│   └── UsdShadeMaterial
└── UsdAPISchemaBase             ← base for all API schemas
    ├── UsdGeomMotionAPI
    ├── UsdPhysicsRigidBodyAPI
    └── ...
```

### Choosing the Right Base Class for Custom Schemas

| Base Class | Use when |
|------------|---------|
| `UsdSchemaBase` | ❌ Almost never — requires implementing everything manually |
| `UsdTyped` | ✅ Standard IsA schema that is a new prim type |
| `UsdGeomImageable` | ✅ Custom renderable object that needs visibility and purpose |
| `UsdGeomXformable` | ✅ Custom object that needs transforms |

> **Exam trap:** "Inherit directly from UsdSchemaBase" is typically the wrong answer. The correct base is `UsdTyped` for standard custom IsA schemas, or `UsdGeomImageable` if the schema is a renderable object.

---

## 4. Creating Custom Schemas

Custom schemas are defined in a `schema.usda` file that describes the schema's class, what it inherits from, and what attributes it provides with their types and default values.

### `schema.usda` File Structure

```usda
#usda 1.0
(
    subLayers = [
        @usd/schema.usda@       # inherit from base USD schemas
    ]
)

over "GLOBAL" (
    customData = {
        string libraryName   = "acmeSensors"    # library name
        string libraryPrefix = "AcmeSensor"     # C++ class prefix
    }
) {}

# Custom IsA schema — inherits from Xform (which is a UsdTyped)
class Xform "TemperatureSensor" (
    customData = {
        string className = "TemperatureSensor"
    }
    doc = """A prim representing a physical temperature sensor."""
    inherits = </Xform>
) {
    float  sensor:temperature = 20.0      # default = 20°C
    float  sensor:minRange    = -40.0
    float  sensor:maxRange    = 125.0
    string sensor:serialNumber = ""
}
```

---

## 5. The usdGenSchema Workflow

`usdGenSchema` is the code generation tool that transforms a `schema.usda` definition into compilable C++ code and Python bindings.

```
STEP 1: Write schema.usda
        Define schema class, base class, attributes + defaults

STEP 2: Run usdGenSchema
        usdGenSchema schema.usda
        Generates:
          - C++ header and source files
          - Python bindings
          - plugInfo.json (for plugin discovery)

STEP 3: Compile the generated C++ into a shared library
        cmake + make → acmeSensors.so / acmeSensors.dll

STEP 4: Deploy the plugin
        Place .so + plugInfo.json where USD can discover it
        PXR_PLUGINPATH_NAME=/path/to/acmeSensors

STEP 5: Use like any built-in schema
        from pxr import AcmeSensors
        sensor = AcmeSensors.TemperatureSensor.Define(stage, "/Factory/S01")
        sensor.GetTemperatureAttr().Get()   # 20.0 (schema fallback)
```

### Why Not Python-Only?

Python-only schemas do **not** provide:
- Full USD type system integration
- Schema fallback values
- `prim.IsA()` working correctly  
- C++ performance code paths

Full custom schemas require C++ code generation via `usdGenSchema`. Python-only approaches are limited and are marked incorrect on the exam.

---

## 6. TfType Registration

**TfType** is USD's runtime type identification system. Registration is what makes `prim.IsA()`, `prim.HasAPI()`, and schema discovery work.

Without TfType registration:
```python
prim.IsA(TemperatureSensor)   # ERROR or always False
prim.GetTypeName()             # "TemperatureSensor" (just a string, no type knowledge)
sensor.GetTemperatureAttr().Get()  # returns None (no schema fallback)
```

With TfType registration (via `usdGenSchema`-generated `plugInfo.json`):
```python
prim.IsA(TemperatureSensor)    # True ✅
prim.IsA(UsdGeomXform)         # True ✅ (inheritance chain known)
sensor.GetTemperatureAttr().Get()  # 20.0 ✅ (schema fallback works)
```

TfType registration happens automatically when `usdGenSchema` generates `plugInfo.json` and the plugin is deployed to a path in `PXR_PLUGINPATH_NAME`. USD loads `plugInfo.json` at startup and registers all described types.

> **Exam trap:** "Register the custom model kind token in the TfType system without any schema or API linkage" is **WRONG**. Token registration alone provides no inheritance chain, no fallback values, and no API. The schema definition itself must be linked.

---

## 7. Custom File Format Plugins — SdfFileFormat

A **file format plugin** teaches USD to read and write a new file type (`.abc`, `.fbx`, `.myformat`). This is completely separate from custom schemas — schemas define what prim types mean; file format plugins define how data is read and written from files.

```
UsdSchema   = defines what scene data IS (prim types, attributes, meaning)
SdfFileFormat = defines how data is READ and WRITTEN to/from a file format
```

### Implementation Steps

```
1. Create a C++ class inheriting from SdfFileFormat
   class MyFormatPlugin : public SdfFileFormat { ... }

2. Implement required methods:
   bool Read(SdfLayer*, const string& resolvedPath, bool metadataOnly)
   bool WriteToFile(const SdfLayer&, const string& filePath, ...)

3. Register with TfType:
   TF_REGISTRY_FUNCTION(TfType) {
       TfType::Define<MyFormatPlugin,
                      TfType::Bases<SdfFileFormat>>();
   }

4. Declare in plugInfo.json for automatic discovery

5. When USD opens a .myformat file:
   → Looks up registered SdfFileFormat plugins
   → Finds MyFormatPlugin (registered for .myformat)
   → Calls MyFormatPlugin.Read() to translate to SdfLayer
   → Stage composes normally from that point
```

### Wrong Approaches

| Wrong approach | Why it's wrong |
|----------------|----------------|
| Override `UsdStage::Open()` | Static method, not designed for this |
| Modify USD core source | Defeats modularity, breaks compatibility |
| Create a UsdSchema for the format | Schemas define data types, not file I/O |

---

## 8. Custom Model Kinds — UsdModelKindRegistry

USD has a built-in hierarchy of **model kinds** that classify prims by their role in the scene:

```
assembly       ← top-level published collection of assets
  group        ← organisational container
    component  ← leaf reusable asset (a chair, a tree, a building)
      subcomponent ← important internal node within a component
```

### Creating Custom Model Kinds

To add a new kind (`factory_unit`) to this hierarchy:

**Step 1 — Define and register with `UsdModelKindRegistry`**

The kind must be registered with the registry so USD recognises it as valid.

**Step 2 — Set the kind on prims using `Usd.ModelAPI`**

```python
from pxr import Usd

prim = stage.DefinePrim("/Factory/Unit_A", "Xform")

# Set the kind using UsdModelAPI
model_api = Usd.ModelAPI(prim)
model_api.SetKind("factory_unit")

# Read the kind
print(model_api.GetKind())   # "factory_unit"
```

**Step 3 — Implement a schema plugin that INHERITS (not overrides) UsdModelAPI**

```
EXTEND UsdModelAPI   ← adds behaviour for the new kind
OVERRIDE UsdModelAPI ← WRONG — replaces existing behaviour, breaks standard kinds
```

**Step 4 — Extend the `Validate()` method for domain-specific rules**

Custom validation ensures `factory_unit` prims always have the required structure.

### Wrong Approaches

| Wrong approach | Why |
|----------------|-----|
| Override (not extend) UsdModelAPI | Replaces existing behaviour — breaks standard kinds |
| Register token in TfType without schema linkage | Provides a name but no behaviour, API, or validation |
| Use variants within the model kind | Variants = content variation. Model kinds = classification. Separate concerns. |
| Modify USD core source | USD's plugin and registry system exists to avoid this |

---

## 9. Key Takeaways

| Concept | What to Remember |
|---------|-----------------|
| **IsA schema** | Defines a prim type. Sets `typeName`. One per prim. Check with `prim.IsA()` |
| **API schema** | Augments a prim. No `typeName`. Multiple per prim. Check with `prim.HasAPI()` |
| **Custom schema base** | `UsdTyped` for standard schemas. `UsdGeomImageable` for renderable. NOT `UsdSchemaBase` directly |
| **usdGenSchema** | Generates C++ and Python from `schema.usda`. Required for full integration |
| **TfType registration** | Makes `IsA()`, `HasAPI()`, fallback values work. Done via `plugInfo.json` |
| **Python-only schemas** | Limited — no full type system integration. NOT correct for production schemas |
| **SdfFileFormat** | For teaching USD to read/write new file formats. Independent of schemas |
| **UsdModelKindRegistry** | Register custom model kinds here. Use `Usd.ModelAPI.SetKind()` to apply |
| **Extend vs Override** | Always EXTEND UsdModelAPI — never override. Override breaks existing kinds |
| **Schema file format separation** | Schema = what data IS. SdfFileFormat = how data is STORED. Independent. |

---

*Previous: [Day 4 — Advanced Composition Concepts](day-04-advanced-composition.md)*  
*Next: [Day 6 — Visualization](day-06-visualization.md)*
