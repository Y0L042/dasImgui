#!/usr/bin/env python3
"""Generate Daslang bindings for Dear ImGui from imgui.h.

Usage:
    python3 gen_imgui_bindings.py <imgui.h> <out_dir> <imgui_base.das>

Outputs:
    <out_dir>/module_imgui_enums.inc        -- C++ Enumeration class definitions
    <out_dir>/module_imgui_annotations.inc  -- C++ struct annotation class definitions
    <out_dir>/module_imgui_register.inc     -- C++ registration calls (enums, annotations, externs)
    <out_dir>/module_imgui_constants.inc    -- C++ addConstant calls
    Updates <imgui_base.das> with typedefs and enum constants
"""

import re
import sys
import os

# ─── Configuration ───────────────────────────────────────────────────────────

# Structs aliased to daScript built-in types (handled in imgui_das.h)
ALIAS_STRUCTS = {"ImVec2", "ImVec4", "ImColor"}

# Structs to skip entirely
SKIP_STRUCTS = ALIAS_STRUCTS | {"ImNewWrapper", "ImVector", "ImGuiStoragePair"}

# --- Function handled by hand-written C++ wrappers in module_imgui.cpp
SKIP_FUNCTIONS = {
    # Variadic / format-string functions
    "Text", "TextV",
    "TextColored", "TextColoredV",
    "TextDisabled", "TextDisabledV",
    "TextWrapped", "TextWrappedV",
    "LabelText", "LabelTextV",
    "BulletText", "BulletTextV",
    "SetTooltip", "SetTooltipV",
    "SetItemTooltipV",
    "LogText", "LogTextV",
    "TreeNode",     # fmt overloads only (ptr overload kept)
    "TreeNodeEx",   # fmt overloads only
    "TreeNodeV", "TreeNodeExV",
    "TextUnformatted",
    # Callback-based (need lambda trampolines)
    "InputText", "InputTextMultiline", "InputTextWithHint",
    "SetNextWindowSizeConstraints",
    # Special handling
    "CalcTextSize",
    # Debug / internal
    "DebugLog", "DebugLogV",
    "DebugCheckVersionAndDataLayout",
    # Allocator
    "SetAllocatorFunctions", "GetAllocatorFunctions",
    # Text buffer / filter member access (hand-written)
}

# Functions where we skip specific overloads (by checking param patterns)
SKIP_FUNCTION_PATTERNS = {
    # Combo with getter callback
    ("Combo", r"\bgetter\b"),
    ("ListBox", r"\bgetter\b"),
    # PlotLines/PlotHistogram with getter callback
    ("PlotLines", r"values_getter"),
    ("PlotHistogram", r"values_getter"),
}

# Opaque forward-declared structs (no body visible in imgui.h)
KNOWN_OPAQUE_STRUCTS = {
    "ImGuiContext", "ImDrawListSharedData",
    "ImFontAtlasBuilder", "ImFontLoader",
}

# C primitive types safe for struct fields
PRIMITIVE_BASE_TYPES = {
    "void", "bool", "char", "int", "short", "long", "float", "double",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "size_t", "ptrdiff_t",
}

# ImGui scalar typedefs -> daScript types
IMGUI_SCALAR_TYPEDEFS = {
    "ImGuiID":  "uint",
    "ImS8":     "int8",
    "ImU8":     "uint8",
    "ImS16":    "int16",
    "ImU16":    "uint16",
    "ImS32":    "int",
    "ImU32":    "uint",
    "ImS64":    "int64",
    "ImU64":    "uint64",
    "ImWchar":  "uint",
    "ImWchar16": "uint16",
    "ImWchar32": "uint",
    "ImDrawIdx": "uint16",
    "ImTextureID": "uint64",
}

# ImGui flag/enum typedefs (typedef int ImGuiCol -> ImGuiCol_)
# These map the typedef name to the actual enum name
# Will be auto-detected from the header

# daScript reserved keywords that need field renaming
DAS_RESERVED_FIELD_RENAMES = {
    "type": "vtype",
    "delete": "vdelete",
    "new": "vnew",
    "var": "vvar",
    "def": "vdef",
    "let": "vlet",
    "module": "vmodule",
    "require": "vrequire",
    "options": "voptions",
    "override": "voverride",
    "struct": "vstruct",
    "class": "vclass",
    "enum": "venum",
    "finally": "vfinally",
    "label": "vlabel",
    "goto": "vgoto",
    "addr": "vaddr",
    "unsafe": "vunsafe",
    "pass": "vpass",
    "recover": "vrecover",
    "yield": "vyield",
    "generator": "vgenerator",
    "iterator": "viterator",
    "where": "vwhere",
    "shared": "vshared",
    "private": "vprivate",
    "public": "vpublic",
    "smart_ptr": "vsmart_ptr",
    "operator": "voperator",
    "cast": "vcast",
    "upcast": "vupcast",
    "reinterpret": "vreinterpret",
    "typeinfo": "vtypeinfo",
    "typedef": "vtypedef",
    "array": "varray",
    "table": "vtable",
    "block": "vblock",
    "lambda": "vlambda",
    "expect": "vexpect",
    "const": "vconst",
    "static": "vstatic",
    "abstract": "vabstract",
    "sealed": "vsealed",
    "inscope": "vinscope",
    "bitfield": "vbitfield",
    "range": "vrange",
    "urange": "vurange",
}

# ─── Comment stripping ───────────────────────────────────────────────────────

def strip_comments(text: str) -> str:
    """Remove C/C++ comments, preserving newlines for line-count fidelity."""
    result = []
    i = 0
    n = len(text)
    in_string = False
    string_char = None

    while i < n:
        # Track string literals to avoid stripping inside them
        if not in_string and text[i] in ('"', "'"):
            in_string = True
            string_char = text[i]
            result.append(text[i])
            i += 1
            continue
        if in_string:
            if text[i] == '\\' and i + 1 < n:
                result.append(text[i:i+2])
                i += 2
                continue
            if text[i] == string_char:
                in_string = False
            result.append(text[i])
            i += 1
            continue

        if text[i:i+2] == "//":
            while i < n and text[i] != "\n":
                result.append(" ")
                i += 1
        elif text[i:i+2] == "/*":
            result.append(" ")
            i += 2
            while i < n and text[i:i+2] != "*/":
                result.append("\n" if text[i] == "\n" else " ")
                i += 1
            result.append(" ")
            i += 2
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def strip_obsolete_blocks(text: str) -> str:
    """Remove #ifndef IMGUI_DISABLE_OBSOLETE_FUNCTIONS blocks."""
    result = []
    lines = text.split("\n")
    depth = 0
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped == "#ifndef IMGUI_DISABLE_OBSOLETE_FUNCTIONS":
            skip = True
            depth = 1
            continue
        if skip:
            if stripped.startswith("#if"):
                depth += 1
            elif stripped == "#endif":
                depth -= 1
                if depth == 0:
                    skip = False
                    continue
            continue
        result.append(line)
    return "\n".join(result)


# ─── Function pointer typedef detection ──────────────────────────────────────

def parse_fn_ptr_typedefs(text: str) -> set:
    """Return names of all typedef'd function pointer types."""
    pat = re.compile(r"typedef\s+[\w\s\*]+\(\s*\*\s*(\w+)\s*\)\s*\(")
    return {m.group(1) for m in pat.finditer(text)}


# ─── Enum parsing ────────────────────────────────────────────────────────────

def parse_enums(text: str) -> list:
    """Parse all ImGui enums. Returns [(enum_name, [(member_name, value_expr), ...])]."""
    results = []
    # Match both: enum Name_ { ... }; and enum Name : Type { ... };
    pat = re.compile(
        r"enum\s+(\w+)\s*(?::\s*\w+)?\s*\{([^}]*)\}\s*;",
        re.DOTALL
    )
    for m in pat.finditer(text):
        enum_name = m.group(1)
        body = m.group(2)

        # Skip if it looks like it's inside a struct or class (ImDrawCallback etc)
        if not enum_name.startswith(("ImGui", "ImDraw", "ImFont", "ImTexture")):
            continue

        members = []
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Remove trailing comma
            line = line.rstrip(",").strip()
            if not line:
                continue
            # Split at = to get name and optional value
            if "=" in line:
                name_part, val_part = line.split("=", 1)
                name = name_part.strip()
                val = val_part.strip()
            else:
                name = line.strip()
                val = None

            # Validate name
            if not name or not re.match(r"^[A-Za-z_]\w*$", name):
                continue

            members.append((name, val))

        if members:
            results.append((enum_name, members))

    return results


def enum_das_name(enum_name: str) -> str:
    """Convert C++ enum name to DAS-facing name (strip trailing _)."""
    if enum_name.endswith("_"):
        return enum_name[:-1]
    return enum_name


# ─── Typedef parsing ─────────────────────────────────────────────────────────

def parse_typed_enum_fwd_decls(text: str) -> dict:
    """Parse 'enum Name : Type;' forward declarations.
    Returns {enum_name: underlying_c_type} for enums that are NOT already
    covered by a 'typedef int Name;' alias.  These enum types cannot appear
    directly in daScript extern signatures because there is no typeFactory
    for them; they must be replaced with their underlying integer type."""
    pat = re.compile(r"^\s*enum\s+(\w+)\s*:\s*(\w+)\s*;", re.MULTILINE)
    result = {}
    for m in pat.finditer(text):
        name = m.group(1)
        underlying = m.group(2)
        # Map ImGui scalar typedefs to plain C types
        c_type = {"ImU8": "uint8_t", "ImS8": "int8_t",
                  "ImU16": "uint16_t", "ImS16": "int16_t",
                  "ImU32": "uint32_t", "ImS32": "int32_t",
                  "ImU64": "uint64_t", "ImS64": "int64_t"}.get(underlying, underlying)
        result[name] = c_type
    return result


def parse_flag_typedefs(text: str) -> dict:
    """Parse 'typedef int ImGuiCol;' style typedefs. Returns {typedef_name: enum_name}."""
    pat = re.compile(r"typedef\s+int\s+(Im\w+)\s*;")
    result = {}
    for m in pat.finditer(text):
        name = m.group(1)
        # The corresponding enum is name + "_"
        result[name] = name + "_"
    return result


# ─── Forward declaration / opaque struct parsing ─────────────────────────────

def parse_forward_decls(text: str) -> set:
    """Parse 'struct Name;' forward declarations."""
    pat = re.compile(r"^struct\s+(\w+)\s*;", re.MULTILINE)
    return {m.group(1) for m in pat.finditer(text)}


# ─── Struct parsing ──────────────────────────────────────────────────────────

def extract_brace_block(text: str, start: int):
    """Starting at '{', return (body_with_braces, end_pos) or (None, len)."""
    depth = 0
    i = start
    n = len(text)
    while i < n:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1], i + 1
        i += 1
    return None, n


def parse_struct_fields(body: str, safe_types: set, fn_ptr_types: set) -> list:
    """Extract bindable fields from a struct body. Returns [(field_name, c_type_str)]."""
    fields = []
    inner = body[1:-1]  # strip outer { }

    depth = 0
    token_start = 0
    i = 0
    n = len(inner)

    while i < n:
        c = inner[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == ";" and depth == 0:
            stmt = inner[token_start:i].strip()
            token_start = i + 1
            parsed = _try_parse_field(stmt, safe_types, fn_ptr_types)
            if parsed:
                fields.extend(parsed)
        i += 1
    return fields


def _try_parse_field(stmt: str, safe_types: set, fn_ptr_types: set):
    """Try to parse a field declaration. Returns list of (field_name, base_type) or None."""
    stmt = re.sub(r"\s+", " ", stmt).strip()
    if not stmt:
        return None

    # Skip preprocessor, inline keyword-only lines
    if stmt.startswith(("#", "//", "/*", "inline", "constexpr", "static",
                        "template", "explicit", "friend", "operator",
                        "IM_MSVC", "IMGUI")):
        return None

    # Skip if contains parens (constructors, methods, function pointers, etc.)
    if "(" in stmt or ")" in stmt:
        return None

    # Skip if contains braces (nested struct, lambda, etc.)
    if "{" in stmt or "}" in stmt:
        return None

    # Skip bitfield declarations (e.g. "ImGuiSortDirection SortDirection : 8")
    if re.search(r":\s*\d+\s*$", stmt):
        return None

    # Check for multi-field declarations like "float x, y;"
    # First, strip array dimensions
    stmt_no_arr = re.sub(r"\s*\[.*?\]", "", stmt).strip()
    if not stmt_no_arr:
        return None

    # Check for fixed-size arrays (skip them for now)
    if "[" in stmt:
        return None

    # Split into type tokens and field names
    # Handle "float x, y, z, w;" style
    parts = stmt_no_arr.split(",")
    if len(parts) > 1:
        # Multi-field: parse first part to get the type, then extract names
        first_part = parts[0].strip()
        tokens = first_part.replace("*", " * ").split()
        if len(tokens) < 2:
            return None

        first_field = tokens[-1].strip("*")
        type_tokens = tokens[:-1]
        # Reconstruct type
        base_type = " ".join(t for t in type_tokens if t != "const" and t != "*")

        if base_type not in safe_types:
            return None

        results = []
        # First field
        if _is_valid_field_name(first_field):
            results.append((first_field, base_type))
        # Remaining fields
        for p in parts[1:]:
            name = p.strip().strip("*").strip()
            if _is_valid_field_name(name):
                results.append((name, base_type))
        return results if results else None

    # Single field
    tokens = stmt_no_arr.replace("*", " * ").split()
    if len(tokens) < 2:
        return None

    field_name = tokens[-1]
    type_tokens = [t for t in tokens[:-1] if t not in ("const", "mutable", "volatile")]

    if not _is_valid_field_name(field_name):
        return None

    # Get base type (strip pointers)
    base_type = ""
    for t in type_tokens:
        if t != "*":
            base_type = t

    if not base_type:
        return None

    # Skip function pointer fields
    if base_type in fn_ptr_types:
        return None

    # Only include fields whose base type is known-safe
    if base_type not in safe_types:
        return None

    return [(field_name, base_type)]


def _is_valid_field_name(name: str) -> bool:
    """Check if a name is a valid, bindable field name."""
    if not name or not re.match(r"^[A-Za-z_]\w*$", name):
        return False
    if name.startswith("__"):
        return False
    # Skip names starting with _ (internal/private in ImGui convention)
    if name.startswith("_") and len(name) > 1:
        return False
    return True


# def parse_structs(text: str, fn_ptr_types: set, safe_types: set) -> list:
#     """Parse struct definitions. Returns [(struct_name, [(field_name, base_type)])]."""
#     results = []
#     seen = set()

#     pat = re.compile(r"\bstruct\s+(\w+)\s*\{")
#     for m in pat.finditer(text):
#         struct_name = m.group(1)
#         if struct_name in seen or struct_name in SKIP_STRUCTS:
#             continue

#         body, end = extract_brace_block(text, m.end() - 1)
#         if not body:
#             continue

#         seen.add(struct_name)
#         fields = parse_struct_fields(body, safe_types, fn_ptr_types)
#         results.append((struct_name, fields))

#     return results

def parse_structs(text: str, fn_ptr_types: set, safe_types: set) -> list:
    """Parse struct definitions, including nested structs.
    Returns [(das_name, cpp_name, [(field_name, base_type)])]."""
    results = []
    seen = set()

    pat = re.compile(r"\bstruct\s+(\w+)\s*\{")

    # First pass: collect top-level structs and their bodies
    top_level = []  # (struct_name, body, match)
    for m in pat.finditer(text):
        struct_name = m.group(1)

        prefix = text[:m.start()]
        is_nested = prefix.count("{") != prefix.count("}")

        if is_nested:
            continue

        if struct_name in seen or struct_name in SKIP_STRUCTS:
            continue

        body, end = extract_brace_block(text, m.end() - 1)
        if not body:
            continue

        seen.add(struct_name)
        top_level.append((struct_name, body))

    # Second pass: scan each top-level struct body for nested structs
    nested_results = []
    for parent_name, parent_body in top_level:
        inner = parent_body[1:-1]  # strip outer { }
        for nm in pat.finditer(inner):
            nested_name = nm.group(1)
            qualified = f"{parent_name}::{nested_name}"
            if nested_name in seen or nested_name in SKIP_STRUCTS:
                continue
            nested_body, _ = extract_brace_block(inner, nm.end() - 1)
            if not nested_body:
                continue
            seen.add(nested_name)
            fields = parse_struct_fields(nested_body, safe_types, fn_ptr_types)
            nested_results.append((nested_name, qualified, fields))

    # Nested structs come first so they are registered before their parents
    for das_name, cpp_name, fields in nested_results:
        results.append((das_name, cpp_name, fields))

    for struct_name, body in top_level:
        fields = parse_struct_fields(body, safe_types, fn_ptr_types)
        results.append((struct_name, struct_name, fields))

    return results


# ─── Function parsing ────────────────────────────────────────────────────────

def extract_namespace_imgui(text: str) -> str:
    """Extract the content of 'namespace ImGui { ... }'."""
    pat = re.compile(r"namespace\s+ImGui\s*\{")
    m = pat.search(text)
    if not m:
        return ""

    body, _ = extract_brace_block(text, m.end() - 1)
    if not body:
        return ""
    return body[1:-1]  # strip outer braces


def parse_imgui_functions(ns_body: str) -> list:
    """Parse IMGUI_API function declarations from namespace ImGui body.
    Returns [(ret_type, func_name, params_str, is_variadic)]."""
    results = []
    # Find IMGUI_API declarations
    pos = 0
    n = len(ns_body)

    while pos < n:
        idx = ns_body.find("IMGUI_API", pos)
        if idx == -1:
            break
        pos = idx + 9

        # Collect the full declaration up to the semicolon
        end = pos
        depth = 0
        while end < n:
            c = ns_body[end]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == ";" and depth == 0:
                break
            elif c == "{":
                break  # inline body, not a decl
            end += 1

        if end >= n or ns_body[end] != ";":
            continue

        decl = ns_body[idx:end + 1]
        parsed = _parse_func_decl(decl)
        if parsed:
            results.append(parsed)

    return results


def _parse_func_decl(decl: str):
    """Parse a single IMGUI_API function declaration.
    Returns (ret_type, func_name, params_str, is_variadic) or None."""
    text = re.sub(r"^IMGUI_API\s*", "", decl.strip())
    text = re.sub(r"\s+", " ", text).strip().rstrip(";")

    # Find opening paren of parameter list
    paren_start = text.find("(")
    if paren_start == -1:
        return None

    before_paren = text[:paren_start].strip()

    # Function name is the last word before '('
    name_m = re.search(r"\b(\w+)\s*$", before_paren)
    if not name_m:
        return None

    func_name = name_m.group(1)
    ret_type = before_paren[:name_m.start()].strip()

    # Find matching close paren
    paren_end = text.rfind(")")
    if paren_end == -1:
        return None

    params = text[paren_start + 1:paren_end].strip()
    is_variadic = "..." in params

    return ret_type, func_name, params, is_variadic


def parse_param_list(params_str: str) -> list:
    """Parse parameter string into list of (type_str, param_name, default_value_or_None)."""
    if not params_str or params_str.strip() in ("void", ""):
        return []

    params = []
    depth = 0
    current = ""
    for c in params_str:
        if c in ("(", "<"):
            depth += 1
            current += c
        elif c in (")", ">"):
            depth -= 1
            current += c
        elif c == "," and depth == 0:
            params.append(current.strip())
            current = ""
        else:
            current += c
    if current.strip():
        params.append(current.strip())

    result = []
    for p in params:
        p = p.strip()
        if p == "..." or not p:
            continue

        # Split off default value
        default = None
        if "=" in p:
            # Find the = that's not inside parens/angle brackets
            eq_depth = 0
            eq_pos = -1
            for i, c in enumerate(p):
                if c in ("(", "<"):
                    eq_depth += 1
                elif c in (")", ">"):
                    eq_depth -= 1
                elif c == "=" and eq_depth == 0:
                    eq_pos = i
                    break
            if eq_pos >= 0:
                default = p[eq_pos + 1:].strip()
                p = p[:eq_pos].strip()

        # Preserve array parameters as pointers in generated C++ signatures
        has_array_decl = "[" in p

        # Remove array dimensions
        p = re.sub(r"\s*\[.*?\]", "", p).strip()
        tokens = p.replace("*", " * ").replace("&", " & ").split()
        if not tokens:
            continue

        param_name = tokens[-1]
        if param_name in ("*", "&"):
            param_name = f"arg{len(result)}"
            type_str = p
        else:
            type_str = " ".join(tokens[:-1]).strip()

        # Arrays decay to pointers in function parameters
        if has_array_decl and type_str and not type_str.endswith("*"):
            type_str = f"{type_str} *"

        type_str = re.sub(r"\s+", " ", type_str).strip()

        result.append((type_str, param_name, default))

    return result


def should_skip_function(func_name: str, params_str: str) -> bool:
    """Check if a function should be skipped."""
    if func_name in SKIP_FUNCTIONS:
        return True

    for skip_name, skip_pattern in SKIP_FUNCTION_PATTERNS:
        if func_name == skip_name and re.search(skip_pattern, params_str):
            return True

    return False


def classify_return_type(ret_type: str, managed_structs: set, opaque_structs: set) -> str:
    """Classify return type as 'plain', 'copy_or_move', or 'skip'."""
    ret_clean = re.sub(r"\s+", " ", ret_type).strip()
    is_pointer = "*" in ret_clean
    is_ref = "&" in ret_clean
    base = re.sub(r"[*&\s]|const", "", ret_clean).strip()

    if is_pointer or is_ref:
        return "plain"
    if base in ("void", "bool", "int", "float", "double", "char",
                "ImGuiID", "ImU32", "ImS32", "ImU64", "ImS64",
                "ImU8", "ImS8", "ImU16", "ImS16",
                "ImWchar", "ImTextureID", "ImDrawIdx"):
        return "plain"
    if base in ("ImVec2", "ImVec4", "ImColor"):
        return "plain"  # aliased to float2/float4
    if base in managed_structs:
        return "copy_or_move"
    if base in opaque_structs:
        return "skip"
    # Unknown - be conservative
    return "plain"


# ─── Default value generation ────────────────────────────────────────────────

def gen_default_value_expr(default_str: str, param_type: str) -> str:
    """Generate C++ expression for arg_init() from a default value string.
    Returns the C++ code or None if we can't handle it."""
    if default_str is None:
        return None

    d = default_str.strip()

    # NULL / nullptr
    if d in ("NULL", "nullptr", "0") and "*" in param_type:
        return "make_smart<ExprConstPtr>()"

    # Boolean
    if d == "true":
        return "make_smart<ExprConstBool>(true)"
    if d == "false":
        return "make_smart<ExprConstBool>(false)"

    # Integer zero
    if d == "0" and "*" not in param_type:
        return "make_smart<ExprConstInt>(0)"

    # Negative integer
    m = re.match(r"^-?\d+$", d)
    if m:
        return f"make_smart<ExprConstInt>({d})"

    # Float literals
    m = re.match(r"^-?[\d.]+f$", d)
    if m:
        return f"make_smart<ExprConstFloat>({d})"

    m = re.match(r"^-?[\d.]+$", d)
    if m and ("float" in param_type or param_type.strip() in ("ImVec2", "ImVec4")):
        return f"make_smart<ExprConstFloat>({d}f)"

    # FLT_MAX, FLT_MIN
    if d == "FLT_MAX":
        return "make_smart<ExprConstFloat>(FLT_MAX)"
    if d == "FLT_MIN":
        return "make_smart<ExprConstFloat>(FLT_MIN)"
    if d == "-FLT_MAX":
        return "make_smart<ExprConstFloat>(-FLT_MAX)"
    if d == "-FLT_MIN":
        return "make_smart<ExprConstFloat>(-FLT_MIN)"

    # ImVec2(0,0) or ImVec2(0.0f, 0.0f) -> ExprCall
    if d.startswith("ImVec2("):
        return 'make_smart<ExprCall>(LineInfo(), "ImVec2")'

    # ImVec4(0,0,0,0) -> ExprCall
    if d.startswith("ImVec4("):
        return 'make_smart<ExprCall>(LineInfo(), "ImVec4")'

    # sizeof(float) and similar
    m = re.match(r"^sizeof\((\w+)\)$", d)
    if m:
        return f"make_smart<ExprConstInt>(int32_t(sizeof({m.group(1)})))"

    # Can't handle this default
    return None


# ─── Code generation ─────────────────────────────────────────────────────────

_HEADER = """\
// GENERATED by gen_imgui_bindings.py - do not edit manually.
// Regenerate with: bash manage.sh codegen
"""


def gen_enums_inc(enums: list) -> str:
    """Generate module_imgui_enums.inc - Enumeration class definitions."""
    lines = [_HEADER]

    for enum_name, members in enums:
        das_name = enum_das_name(enum_name)
        cls_name = f"Enumeration_{enum_name}"

        lines.append(f"class {cls_name} : public das::Enumeration {{")
        lines.append(f"public:")
        lines.append(f"    {cls_name}() : das::Enumeration(\"{das_name}\") {{")
        lines.append(f"        external = true;")
        lines.append(f'        cppName = "{enum_name}";')
        lines.append(f"        baseType = (das::Type) das::ToBasicType<int>::type;")

        for member_name, _ in members:
            lines.append(
                f'        addIEx("{member_name}", "{member_name}",'
                f" int64_t({member_name}), das::LineInfo());"
            )

        lines.append(f"    }}")
        lines.append(f"}};")
        lines.append(f"")

    return "\n".join(lines)


def gen_annotations_inc(opaque_structs: list, managed_structs: list,
                        typed_enum_bindings: list = None) -> str:
    """Generate module_imgui_annotations.inc - struct annotation classes."""
    lines = [_HEADER]

    # Typed enum bindings (enums used directly in function signatures
    # that don't have a 'typedef int' alias)
    if typed_enum_bindings:
        lines.append("// --- Typed enum cast + factory (for enums used by value in extern signatures) ---")
        lines.append("")
        for enum_name, das_name in typed_enum_bindings:
            lines.append(f"DAS_BIND_ENUM_CAST({enum_name});")
            lines.append(f'DAS_BASE_BIND_ENUM_GEN({enum_name}, {das_name});')
        lines.append("")

    # Opaque types
    if opaque_structs:
        lines.append("// --- Opaque types (DummyTypeAnnotation) ---")
        lines.append("")

    for name in opaque_structs:
        cls = f"{name}Annotation"
        lines.append(f"MAKE_TYPE_FACTORY({name}, {name});")
        lines.append(f"struct {cls} : das::DummyTypeAnnotation {{")
        lines.append(f"    {cls}()")
        lines.append(
            f'        : DummyTypeAnnotation("{name}", "{name}",'
            f" sizeof(void*), alignof(void*)) {{}}"
        )
        lines.append(f"}};")
        lines.append(f"")

    # Managed structs
    if managed_structs:
        lines.append("// --- Managed structs (ManagedStructureAnnotation) ---")
        lines.append("")

    for das_name, cpp_name, fields in managed_structs:
        cls = f"{das_name}Annotation"
        lines.append(f"MAKE_TYPE_FACTORY({das_name}, {cpp_name});")
        lines.append(
            f"struct {cls} : das::ManagedStructureAnnotation<{cpp_name}, false> {{"
        )
        lines.append(
            f"    {cls}(das::ModuleLibrary &ml)"
            f' : ManagedStructureAnnotation("{das_name}", ml) {{'
        )
        for field_name, _ in fields:
            field_das_name = DAS_RESERVED_FIELD_RENAMES.get(field_name, field_name)
            lines.append(
                f'        addField<DAS_BIND_MANAGED_FIELD({field_name})>'
                f'("{field_das_name}", "{field_name}");'
            )
        lines.append(f"    }}")
        lines.append(f"}};")
        lines.append(f"")

    return "\n".join(lines)


def gen_register_inc(
    enums: list,
    opaque_structs: list,
    managed_structs: list,
    functions: list,
) -> str:
    """Generate module_imgui_register.inc - all registration calls."""
    lines = [_HEADER]

    # Enum registrations
    lines.append("// --- Enum registrations ---")
    lines.append("")
    for enum_name, _ in enums:
        cls = f"Enumeration_{enum_name}"
        lines.append(f"addEnumeration(das::make_smart<{cls}>());")
    lines.append("")

    # Opaque type registrations
    lines.append("// --- Opaque type registrations ---")
    lines.append("")
    for name in opaque_structs:
        cls = f"{name}Annotation"
        lines.append(f"addAnnotation(das::make_smart<{cls}>());")
    lines.append("")

    # Managed struct registrations
    lines.append("// --- Managed struct registrations ---")
    lines.append("")
    for das_name, cpp_name, _ in managed_structs:
        cls = f"{das_name}Annotation"
        lines.append(f"addAnnotation(das::make_smart<{cls}>(lib));")
    lines.append("")

    # Function registrations
    lines.append("// --- Function registrations ---")
    lines.append("")

    # Track overload counts for unique naming
    name_counts = {}
    for ret_type, func_name, params_str, classification, _ in functions:
        if classification == "skip":
            continue
        count = name_counts.get(func_name, 0)
        name_counts[func_name] = count + 1

    # Reset for actual generation
    name_seen = {}

    for ret_type, func_name, params_str, classification, is_variadic in functions:
        if classification == "skip":
            lines.append(f"// SKIPPED: ImGui::{func_name} (unsupported return type)")
            continue

        # Generate unique DAS name for overloads
        seen_count = name_seen.get(func_name, 0)
        name_seen[func_name] = seen_count + 1
        das_func_name = func_name if seen_count == 0 else f"{func_name}{seen_count + 1}"

        # Build the C++ function pointer type for overload disambiguation
        params = parse_param_list(params_str)
        param_types = []
        for ptype, pname, pdefault in params:
            param_types.append(ptype)

        # Build function pointer type string
        clean_ret = ret_type.strip()
        param_type_str = ", ".join(param_types) if param_types else "void"

        # Determine if we need copy_or_move SimNode
        if classification == "copy_or_move":
            sim_node = "das::SimNode_ExtFuncCallAndCopyOrMove"
            lines.append(
                f"das::makeExtern<{clean_ret}(*)({param_type_str}),"
                f" ImGui::{func_name},"
                f" {sim_node}, imguiTempFn>"
                f'(lib, "{das_func_name}", "ImGui::{func_name}")'
            )
        else:
            lines.append(
                f"das::makeExtern<{clean_ret}(*)({param_type_str}),"
                f" ImGui::{func_name},"
                f" das::SimNode_ExtFuncCall, imguiTempFn>"
                f'(lib, "{das_func_name}", "ImGui::{func_name}")'
            )

        # Add argument names
        arg_names = [p[1] for p in params]
        if arg_names:
            arg_str = ", ".join(f'"{n}"' for n in arg_names)
            lines.append(f"    ->args({{{arg_str}}})")

        # Add default values
        for i, (ptype, pname, pdefault) in enumerate(params):
            if pdefault is not None:
                expr = gen_default_value_expr(pdefault, ptype)
                if expr:
                    lines.append(f"    ->arg_init({i}, {expr})")

        lines.append(f"    ->addToModule(*this, das::SideEffects::worstDefault);")
        lines.append(f"")

    return "\n".join(lines)


def gen_constants_inc() -> str:
    """Generate module_imgui_constants.inc."""
    lines = [_HEADER]
    lines.append('addConstant(*this, "IMGUI_VERSION", IMGUI_VERSION);')
    lines.append('addConstant(*this, "IMGUI_VERSION_NUM", int32_t(IMGUI_VERSION_NUM));')
    return "\n".join(lines)


def gen_imgui_base_das(enums: list, scalar_typedefs: dict) -> str:
    """Generate imgui_base.das content."""
    lines = [
        "options gen2",
        "",
        "module imgui_base shared public",
        "",
        "require imgui_core public",
        "",
        "// --- Scalar typedefs ---",
    ]

    for c_name, das_type in sorted(scalar_typedefs.items()):
        lines.append(f"typedef {c_name} = {das_type}")

    lines.append("")
    lines.append("// --- Enum constants (for use as int values) ---")

    for enum_name, members in enums:
        das_name = enum_das_name(enum_name)
        lines.append(f"")
        lines.append(f"// {das_name}")

    lines.append("")

    return "\n".join(lines) + "\n"


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <imgui.h> <out_dir> <imgui_base.das>")
        sys.exit(1)

    header_path, out_dir, das_path = sys.argv[1], sys.argv[2], sys.argv[3]

    print(f"Reading {header_path} ...")
    with open(header_path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    text = strip_comments(raw)
    text = strip_obsolete_blocks(text)

    # ── Parse ────────────────────────────────────────────────────────────
    fn_ptr_types = parse_fn_ptr_typedefs(text)
    forward_decls = parse_forward_decls(text)
    enums = parse_enums(text)
    flag_typedefs = parse_flag_typedefs(text)
    typed_enum_decls = parse_typed_enum_fwd_decls(text)

    # Typed enums that have no 'typedef int' alias need explicit
    # DAS_BIND_ENUM_CAST + DAS_BASE_BIND_ENUM_GEN so they can appear
    # directly in daScript extern function signatures.
    all_enum_names = {name for name, _ in enums}
    typed_enum_bindings = [
        (name, enum_das_name(name))
        for name in sorted(typed_enum_decls.keys())
        if name not in flag_typedefs and name in all_enum_names
    ]

    # Build set of all known types for struct field safety
    # NOTE: raw C++ enum types are intentionally excluded here because
    # DAS_BIND_MANAGED_FIELD requires a bound typeFactory/type alias.
    # ImGui enum-typed struct fields are not safely bindable without
    # explicit type support.
    safe_types = (
        PRIMITIVE_BASE_TYPES
        | set(IMGUI_SCALAR_TYPEDEFS.keys())
        | set(flag_typedefs.keys())
        | forward_decls
        | ALIAS_STRUCTS
    )

    # Parse structs
    all_parsed_structs = parse_structs(text, fn_ptr_types, safe_types)
    defined_struct_names = {das_name for das_name, _, _ in all_parsed_structs}

    # Add defined struct names to safe types for nested references
    safe_types |= defined_struct_names

    # Re-parse structs with expanded safe types to pick up more fields
    all_parsed_structs = parse_structs(text, fn_ptr_types, safe_types)

    # Separate opaque vs managed
    # Opaque = forward-declared but NOT defined with a body (minus skips)
    opaque_struct_names = sorted(
        (forward_decls | KNOWN_OPAQUE_STRUCTS) - SKIP_STRUCTS - defined_struct_names
    )
    # Managed = has a body definition (minus skips and truly-opaque-only)
    managed_structs = [
        (das_name, cpp_name, fields) for das_name, cpp_name, fields in all_parsed_structs
        if das_name not in SKIP_STRUCTS
    ]

    # ── Parse functions ──────────────────────────────────────────────────
    ns_body = extract_namespace_imgui(text)
    raw_funcs = parse_imgui_functions(ns_body)

    managed_names = {n for n, _, _ in managed_structs}
    opaque_names_set = set(opaque_struct_names)

    functions = []
    skipped = []

    for ret_type, func_name, params_str, is_variadic in raw_funcs:
        # Skip variadic
        if is_variadic:
            skipped.append((func_name, "variadic"))
            continue

        # Skip by name/pattern
        if should_skip_function(func_name, params_str):
            skipped.append((func_name, "skip list"))
            continue

        # Skip functions with function pointer parameters
        has_fn_ptr = False
        for ptype, _, _ in parse_param_list(params_str):
            base = re.sub(r"[*&\s]|const", "", ptype).strip()
            if base in fn_ptr_types:
                has_fn_ptr = True
                break
        if has_fn_ptr:
            skipped.append((func_name, "fn ptr param"))
            continue

        classification = classify_return_type(ret_type, managed_names, opaque_names_set)
        functions.append((ret_type, func_name, params_str, classification, is_variadic))

    # ── Report ───────────────────────────────────────────────────────────
    print(f"  Enums:           {len(enums)}")
    print(f"  Opaque structs:  {len(opaque_struct_names)}")
    print(f"  Managed structs: {len(managed_structs)}")
    print(f"  Functions:       {len(functions)}")
    print(f"  Skipped funcs:   {len(skipped)}")
    for name, reason in skipped:
        print(f"    - {name}: {reason}")
    skipped_ret = [(f, c) for _, f, _, c, _ in functions if c == "skip"]
    if skipped_ret:
        print(f"  Skipped (return type): {skipped_ret}")

    # ── Write outputs ────────────────────────────────────────────────────
    os.makedirs(out_dir, exist_ok=True)

    # Enums
    enums_path = os.path.join(out_dir, "module_imgui_enums.inc")
    with open(enums_path, "w", newline="\n") as f:
        f.write(gen_enums_inc(enums))
    print(f"  Wrote {enums_path}")

    # Annotations
    ann_path = os.path.join(out_dir, "module_imgui_annotations.inc")
    with open(ann_path, "w", newline="\n") as f:
        f.write(gen_annotations_inc(opaque_struct_names, managed_structs, typed_enum_bindings))
    print(f"  Wrote {ann_path}")

    # Register
    reg_path = os.path.join(out_dir, "module_imgui_register.inc")
    with open(reg_path, "w", newline="\n") as f:
        f.write(gen_register_inc(enums, opaque_struct_names, managed_structs, functions))
    print(f"  Wrote {reg_path}")

    # Constants
    const_path = os.path.join(out_dir, "module_imgui_constants.inc")
    with open(const_path, "w", newline="\n") as f:
        f.write(gen_constants_inc())
    print(f"  Wrote {const_path}")

    # DAS file
    with open(das_path, "w", newline="\n", encoding="utf-8") as f:
        f.write(gen_imgui_base_das(enums, IMGUI_SCALAR_TYPEDEFS))
    print(f"  Wrote {das_path}")

    print("Done.")


if __name__ == "__main__":
    main()
