#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEN_IMGUI_PY="$SCRIPT_DIR/tools/gen_imgui_bindings.py"
GENERATE_XXD="$SCRIPT_DIR/tools/generate_xxd.py"
GENERATED_DIR="$SCRIPT_DIR/src/generated"
SCRIPTS_DIR="$SCRIPT_DIR/src/scripts"

# Resolve imgui.h from Duin's external directory
IMGUI_H="$SCRIPT_DIR/../../src/external/imgui.h"
IMGUI_BASE_DAS="$SCRIPTS_DIR/imgui_base.das"

usage() {
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  codegen        Run full codegen pipeline (gen-bindings + gen-inc)"
    echo "  gen-bindings   Parse imgui.h and generate C++ binding fragments"
    echo "  gen-inc        Convert .das files to hex-encoded .das.inc"
    echo "  fmt <file>     Format a .das file"
    echo "  help           Show this help"
}

cmd_gen_bindings() {
    echo "==> Parsing imgui.h and generating C++ binding fragments..."
    python3 "$GEN_IMGUI_PY" "$IMGUI_H" "$GENERATED_DIR" "$IMGUI_BASE_DAS"
}

cmd_gen_inc() {
    echo "==> Converting .das files to .das.inc..."
    for f in "$SCRIPTS_DIR"/*.das; do
        [ -f "$f" ] || continue
        echo "  ${f##*/} -> ${f##*/}.inc"
        python3 "$GENERATE_XXD" "$f" "${f}.inc"
    done
}

cmd_codegen() {
    cmd_gen_bindings
    cmd_gen_inc
    echo "==> Codegen complete."
}

cmd_fmt() {
    if [ $# -lt 1 ]; then
        echo "Usage: $0 fmt <file.das>"
        exit 1
    fi
    local file="$1"
    echo "Formatting $file ..."
    # Use daslang formatter if available
    local daslang_fmt="${SCRIPT_DIR}/../../vendor/daslang/install/bin/daslang_fmt"
    if [ -x "$daslang_fmt" ]; then
        "$daslang_fmt" "$file"
    else
        echo "Warning: daslang_fmt not found at $daslang_fmt"
    fi
}

case "${1:-help}" in
    codegen)       cmd_codegen ;;
    gen-bindings)  cmd_gen_bindings ;;
    gen-inc)       cmd_gen_inc ;;
    fmt)           shift; cmd_fmt "$@" ;;
    help|--help|-h) usage ;;
    *)             echo "Unknown command: $1"; usage; exit 1 ;;
esac
