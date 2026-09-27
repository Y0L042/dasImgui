#include "module_imgui.h"

// Compiled builtin DAS modules
#include "scripts/imgui_base.das.inc"
#include "scripts/imgui_boost.das.inc"

// Generated enum and annotation class definitions
#include "generated/module_imgui_enums.inc"
#include "generated/module_imgui_annotations.inc"

namespace das {
struct DasImguiInputText;
struct DasImGuiSizeConstraints;
struct ImGuiComboGetter;
struct ImGuiPlotGetter;

void imgui_Text(const char *txt);
void imgui_LabelText(const char *lab, const char *txt);
void imgui_TextWrapped(const char *txt);
void imgui_TextDisabled(const char *txt);
void imgui_TextColored(const ImVec4 &col, const char *txt);
void imgui_LogText(const char *txt);
bool imgui_TreeNode_Str(const char *id, const char *txt);
bool imgui_TreeNodeEx_Str(const char *id, ImGuiTreeNodeFlags flags, const char *txt);
bool imgui_TreeNodeEx_Ptr(const void *id, ImGuiTreeNodeFlags flags, const char *txt);
void imgui_TextUnformatted(const char *txt);
void imgui_BulletText(const char *txt);
void imgui_SetTooltip(const char *txt);

int imgui_InputTextCallback(ImGuiInputTextCallbackData *data);
bool imgui_InputTextMultiline(vec4f vdiit, const char *label, const ImVec2 &size, ImGuiInputTextFlags flags,
                              LineInfoArg *at, Context *context);
bool imgui_InputText(vec4f vdiit, const char *label, ImGuiInputTextFlags flags, LineInfoArg *at, Context *context);
bool imgui_InputTextWithHint(vec4f vdiit, const char *label, const char *hint, ImGuiInputTextFlags flags,
                             LineInfoArg *at, Context *context);

bool imgui_PassFilter(ImGuiTextFilter &filter, const char *text);
char *imgui_text_range_string(ImGuiTextFilter::ImGuiTextRange &r, Context *context, LineInfoArg *at);
void imgui_AddText(ImDrawList &drawList, const ImVec2 &pos, ImU32 col, const char *text);
void imgui_AddText2(ImDrawList &drawList, ImFont *font, float font_size, const ImVec2 &pos, ImU32 col,
                    const char *text_begin, float wrap_width, const ImVec4 *cpu_fine_clip_rect);
ImColor imgui_HSV(float h, float s, float v, float a);

void imgui_GTB_Append(ImGuiTextBuffer &buf, const char *txt);
int imgui_GTB_At(ImGuiTextBuffer &buf, int32_t index);
void imgui_GTB_SetAt(ImGuiTextBuffer &buf, int32_t index, int32_t value);
char *imgui_GTB_Slice(ImGuiTextBuffer &buf, int32_t head, int32_t tail, Context *context, LineInfoArg *at);
void imgui_InsertChars(ImGuiInputTextCallbackData &data, int pos, const char *text);

void imgui_SizeConstraintsCallback(ImGuiSizeCallbackData *data);
void imgui_SetNextWindowSizeConstraints(vec4f snwscc, const ImVec2 &size_min, const ImVec2 &size_max,
                                        Context *context, LineInfoArg *at);
void imgui_SetNextWindowSizeConstraintsNoCallback(const ImVec2 &size_min, const ImVec2 &size_max);
ImGuiSortDirection imgui_SortDirection(const ImGuiTableColumnSortSpecs &specs);
ImVec2 imgui_CalcTextSize(const char *text, bool hide_text_after_double_hash, float wrap_width);

const char *imgui_ComboGetterCallback(void *data, int idx);
bool imgui_Combo(vec4f cg, const char *label, int *current_item, int items_count, int popup_max_height_in_items,
                 Context *ctx, LineInfoArg *at);

float imgui_PlotLinesCallback(void *data, int idx);
void imgui_PlotLines(vec4f igpg, const char *label, int values_count, int values_offset, const char *overlay_text,
                     float scale_min, float scale_max, ImVec2 graph_size, Context *ctx, LineInfoArg *at);
void imgui_PlotHistogram(vec4f igpg, const char *label, int values_count, int values_offset,
                         const char *overlay_text, float scale_min, float scale_max, ImVec2 graph_size,
                         Context *ctx, LineInfoArg *at);
}

// ─── Hand-written C++ helper wrappers ───────────────────────────────────────
// These wrap ImGui functions that can't be auto-generated (variadic, callbacks, etc.)

// --- Format-string safety wrappers ---
void das::imgui_Text(const char *txt)
{
    ImGui::Text("%s", txt);
}

void das::imgui_LabelText(const char *lab, const char *txt)
{
    ImGui::LabelText(lab, "%s", txt ? txt : "");
}

void das::imgui_TextWrapped(const char *txt)
{
    ImGui::TextWrapped("%s", txt ? txt : "");
}

void das::imgui_TextDisabled(const char *txt)
{
    ImGui::TextDisabled("%s", txt ? txt : "");
}

void das::imgui_TextColored(const ImVec4 &col, const char *txt)
{
    ImGui::TextColored(col, "%s", txt ? txt : "");
}

void das::imgui_LogText(const char *txt)
{
    ImGui::LogText("%s", txt ? txt : "");
}

bool das::imgui_TreeNode_Str(const char *id, const char *txt)
{
    return ImGui::TreeNode(id, "%s", txt ? txt : "");
}

bool das::imgui_TreeNodeEx_Str(const char *id, ImGuiTreeNodeFlags flags, const char *txt)
{
    return ImGui::TreeNodeEx(id, flags, "%s", txt ? txt : "");
}

bool das::imgui_TreeNodeEx_Ptr(const void *id, ImGuiTreeNodeFlags flags, const char *txt)
{
    return ImGui::TreeNodeEx(id, flags, "%s", txt ? txt : "");
}

void das::imgui_TextUnformatted(const char *txt)
{
    ImGui::TextUnformatted(txt ? txt : "", nullptr);
}

void das::imgui_BulletText(const char *txt)
{
    ImGui::BulletText("%s", txt ? txt : "");
}

void das::imgui_SetTooltip(const char *txt)
{
    ImGui::SetTooltip("%s", txt ? txt : "");
}

// --- InputText callback trampolines ---
struct das::DasImguiInputText
{
    Context *context;
    TLambda<void, DasImguiInputText *, ImGuiInputTextCallbackData *> callback;
    TArray<uint8_t> buffer;
    LineInfo *at;
};

int das::imgui_InputTextCallback(ImGuiInputTextCallbackData *data)
{
    auto diit = (DasImguiInputText *)data->UserData;
    DAS_VERIFY(diit->context && "context is always specified");
    if (!diit->callback.capture)
    {
        diit->context->throw_error("ImguiTextCallback: missing capture");
    }
    return das_invoke_lambda<int>::invoke<DasImguiInputText *, ImGuiInputTextCallbackData *>(
        diit->context, diit->at, diit->callback, diit, data);
}

bool das::imgui_InputTextMultiline(vec4f vdiit, const char *label, const ImVec2 &size, ImGuiInputTextFlags flags,
                                   LineInfoArg *at, Context *context)
{
    auto diit = cast<DasImguiInputText *>::to(vdiit);
    if (diit->buffer.size == 0)
    {
        builtin_array_resize(diit->buffer, 256, 1, context, at);
    }
    if (diit->callback.capture)
    {
        diit->context = context;
        diit->at = at;
        return ImGui::InputTextMultiline(label, diit->buffer.data, diit->buffer.size, size, flags,
                                         &imgui_InputTextCallback, diit);
    }
    else
    {
        return ImGui::InputTextMultiline(label, diit->buffer.data, diit->buffer.size, size, flags);
    }
}

bool das::imgui_InputText(vec4f vdiit, const char *label, ImGuiInputTextFlags flags, LineInfoArg *at,
                          Context *context)
{
    auto diit = cast<DasImguiInputText *>::to(vdiit);
    if (diit->buffer.size == 0)
    {
        builtin_array_resize(diit->buffer, 256, 1, context, at);
    }
    if (diit->callback.capture)
    {
        diit->context = context;
        diit->at = at;
        return ImGui::InputText(label, diit->buffer.data, diit->buffer.size, flags, &imgui_InputTextCallback, diit);
    }
    else
    {
        return ImGui::InputText(label, diit->buffer.data, diit->buffer.size, flags);
    }
}

bool das::imgui_InputTextWithHint(vec4f vdiit, const char *label, const char *hint, ImGuiInputTextFlags flags,
                                  LineInfoArg *at, Context *context)
{
    auto diit = cast<DasImguiInputText *>::to(vdiit);
    if (diit->buffer.size == 0)
    {
        builtin_array_resize(diit->buffer, 256, 1, context, at);
    }
    if (diit->callback.capture)
    {
        diit->context = context;
        diit->at = at;
        return ImGui::InputTextWithHint(label, hint, diit->buffer.data, diit->buffer.size, flags,
                                        &imgui_InputTextCallback, diit);
    }
    else
    {
        return ImGui::InputTextWithHint(label, hint, diit->buffer.data, diit->buffer.size, flags);
    }
}

// --- ImGuiTextFilter ---
bool das::imgui_PassFilter(ImGuiTextFilter &filter, const char *text)
{
    return filter.PassFilter(text, nullptr);
}

char *das::imgui_text_range_string(ImGuiTextFilter::ImGuiTextRange &r, Context *context, LineInfoArg *at)
{
    return context->allocateString(r.b, uint32_t(r.e - r.b), at);
}

// --- ImDrawList text wrappers ---
void das::imgui_AddText(ImDrawList &drawList, const ImVec2 &pos, ImU32 col, const char *text)
{
    drawList.AddText(pos, col, text);
}

void das::imgui_AddText2(ImDrawList &drawList, ImFont *font, float font_size, const ImVec2 &pos, ImU32 col,
                         const char *text_begin, float wrap_width, const ImVec4 *cpu_fine_clip_rect)
{
    drawList.AddText(font, font_size, pos, col, text_begin, nullptr, wrap_width, cpu_fine_clip_rect);
}

// --- ImColor ---
ImColor das::imgui_HSV(float h, float s, float v, float a)
{
    return ImColor::HSV(h, s, v, a);
}

// --- ImGuiTextBuffer ---
void das::imgui_GTB_Append(ImGuiTextBuffer &buf, const char *txt)
{
    buf.append(txt, nullptr);
}

int das::imgui_GTB_At(ImGuiTextBuffer &buf, int32_t index)
{
    return buf[index];
}

void das::imgui_GTB_SetAt(ImGuiTextBuffer &buf, int32_t index, int32_t value)
{
    buf.Buf[index] = (char)value;
}

char *das::imgui_GTB_Slice(ImGuiTextBuffer &buf, int32_t head, int32_t tail, Context *context, LineInfoArg *at)
{
    if (head > tail)
    {
        context->throw_error_at(at, "can't get slice of ImGuiTextBuffer, head > tail");
    }
    int32_t len = tail - head;
    if (len > buf.size())
    {
        context->throw_error_at(at, "can't get slice of ImGuiTextBuffer, slice too big");
    }
    return context->allocateString(buf.begin() + head, len + 1, at);
}

// --- ImGuiInputTextCallbackData ---
void das::imgui_InsertChars(ImGuiInputTextCallbackData &data, int pos, const char *text)
{
    data.InsertChars(pos, text);
}

// --- SetNextWindowSizeConstraints ---
struct das::DasImGuiSizeConstraints
{
    Context *context;
    Lambda lambda;
    LineInfo *at;
};

void das::imgui_SizeConstraintsCallback(ImGuiSizeCallbackData *data)
{
    DasImGuiSizeConstraints *temp = (DasImGuiSizeConstraints *)data->UserData;
    if (!temp->lambda.capture)
    {
        temp->context->throw_error_at(temp->at, "expecting lambda");
    }
    das_invoke_lambda<void>::invoke<ImGuiSizeCallbackData *>(temp->context, temp->at, temp->lambda, data);
}

void das::imgui_SetNextWindowSizeConstraints(vec4f snwscc, const ImVec2 &size_min, const ImVec2 &size_max,
                                             Context *context, LineInfoArg *at)
{
    DasImGuiSizeConstraints *temp = cast<DasImGuiSizeConstraints *>::to(snwscc);
    temp->context = context;
    temp->at = at;
    ImGui::SetNextWindowSizeConstraints(size_min, size_max, &imgui_SizeConstraintsCallback, temp);
}

void das::imgui_SetNextWindowSizeConstraintsNoCallback(const ImVec2 &size_min, const ImVec2 &size_max)
{
    ImGui::SetNextWindowSizeConstraints(size_min, size_max);
}

// --- ImGuiTableColumnSortSpecs ---
ImGuiSortDirection das::imgui_SortDirection(const ImGuiTableColumnSortSpecs &specs)
{
    return (ImGuiSortDirection)specs.SortDirection;
}

// --- CalcTextSize ---
ImVec2 das::imgui_CalcTextSize(const char *text, bool hide_text_after_double_hash, float wrap_width)
{
    return ImGui::CalcTextSize(text, nullptr, hide_text_after_double_hash, wrap_width);
}

// --- Combo with accessor ---
struct das::ImGuiComboGetter
{
    Context *context;
    Lambda lambda;
    LineInfo *at;
};

const char *das::imgui_ComboGetterCallback(void *data, int idx)
{
    ImGuiComboGetter *getter = (ImGuiComboGetter *)data;
    if (!getter->lambda.capture)
    {
        getter->context->throw_error_at(getter->at, "expecting lambda");
    }
    const char *out_text = nullptr;
    das_invoke_lambda<bool>::invoke<int, char **>(getter->context, getter->at, getter->lambda, idx, (char **)&out_text);
    if (out_text == nullptr)
        out_text = "";
    return out_text;
}

bool das::imgui_Combo(vec4f cg, const char *label, int *current_item, int items_count, int popup_max_height_in_items,
                      Context *ctx, LineInfoArg *at)
{
    ImGuiComboGetter *getter = cast<ImGuiComboGetter *>::to(cg);
    getter->context = ctx;
    getter->at = at;
    return ImGui::Combo(label, current_item, &imgui_ComboGetterCallback, getter, items_count,
                        popup_max_height_in_items);
}

// --- PlotLines / PlotHistogram with getter ---
struct das::ImGuiPlotGetter
{
    Context *context;
    Lambda lambda;
    LineInfo *at;
};

float das::imgui_PlotLinesCallback(void *data, int idx)
{
    ImGuiPlotGetter *getter = (ImGuiPlotGetter *)data;
    if (!getter->lambda.capture)
    {
        getter->context->throw_error_at(getter->at, "expecting lambda");
    }
    return das_invoke_lambda<float>::invoke<int>(getter->context, getter->at, getter->lambda, idx);
}

void das::imgui_PlotLines(vec4f igpg, const char *label, int values_count, int values_offset, const char *overlay_text,
                          float scale_min, float scale_max, ImVec2 graph_size, Context *ctx, LineInfoArg *at)
{
    ImGuiPlotGetter *getter = cast<ImGuiPlotGetter *>::to(igpg);
    getter->context = ctx;
    getter->at = at;
    ImGui::PlotLines(label, &imgui_PlotLinesCallback, getter, values_count, values_offset, overlay_text, scale_min,
                     scale_max, graph_size);
}

void das::imgui_PlotHistogram(vec4f igpg, const char *label, int values_count, int values_offset,
                              const char *overlay_text, float scale_min, float scale_max, ImVec2 graph_size,
                              Context *ctx, LineInfoArg *at)
{
    ImGuiPlotGetter *getter = cast<ImGuiPlotGetter *>::to(igpg);
    getter->context = ctx;
    getter->at = at;
    ImGui::PlotHistogram(label, &imgui_PlotLinesCallback, getter, values_count, values_offset, overlay_text, scale_min,
                         scale_max, graph_size);
}

// ─── Module implementation ──────────────────────────────────────────────────

das::Module_imgui::Module_imgui() : Module("imgui_core")
{
}

void das::Module_imgui::initAotAlias()
{
    addAlias(typeFactory<ImVec2>::make(lib));
    addAlias(typeFactory<ImVec4>::make(lib));
    addAlias(typeFactory<ImColor>::make(lib));
}

bool das::Module_imgui::initDependencies()
{
    if (initialized)
        return true;
    initialized = true;

    lib.addModule(this);
    lib.addBuiltInModule();

    initAotAlias();

// Generated registrations
#include "generated/module_imgui_constants.inc"
#include "generated/module_imgui_register.inc"

    // Hand-written helper registrations
    initMain();

    // Compile embedded DAS modules
      compileBuiltinModule(this, "imgui_base.das", imgui_base_das, sizeof(imgui_base_das));
    //  compileBuiltinModule("imgui_boost.das", imgui_boost_das, sizeof(imgui_boost_das));

    return true;
}

void das::Module_imgui::initMain()
{
    // --- Format-string text functions ---
    addExtern<DAS_BIND_FUN(das::imgui_Text)>(*this, lib, "Text", SideEffects::worstDefault, "das::imgui_Text");
    addExtern<DAS_BIND_FUN(das::imgui_TextWrapped)>(*this, lib, "TextWrapped", SideEffects::worstDefault,
                                                    "das::imgui_TextWrapped");
    addExtern<DAS_BIND_FUN(das::imgui_TextDisabled)>(*this, lib, "TextDisabled", SideEffects::worstDefault,
                                                     "das::imgui_TextDisabled");
    addExtern<DAS_BIND_FUN(das::imgui_TextColored), SimNode_ExtFuncCall, imguiTempFn>(
        *this, lib, "TextColored", SideEffects::worstDefault, "das::imgui_TextColored");
    addExtern<DAS_BIND_FUN(das::imgui_LabelText)>(*this, lib, "LabelText", SideEffects::worstDefault,
                                                  "das::imgui_LabelText");
    addExtern<DAS_BIND_FUN(das::imgui_LogText)>(*this, lib, "LogText", SideEffects::worstDefault, "das::imgui_LogText");
    addExtern<DAS_BIND_FUN(das::imgui_TreeNode_Str)>(*this, lib, "TreeNode", SideEffects::worstDefault,
                                                     "das::imgui_TreeNode_Str");
    addExtern<DAS_BIND_FUN(das::imgui_TreeNodeEx_Str)>(*this, lib, "TreeNodeEx", SideEffects::worstDefault,
                                                       "das::imgui_TreeNodeEx_Str");
    addExtern<DAS_BIND_FUN(das::imgui_TreeNodeEx_Ptr)>(*this, lib, "TreeNodeEx", SideEffects::worstDefault,
                                                       "das::imgui_TreeNodeEx_Ptr");
    addExtern<DAS_BIND_FUN(das::imgui_BulletText)>(*this, lib, "BulletText", SideEffects::worstDefault,
                                                   "das::imgui_BulletText");
    addExtern<DAS_BIND_FUN(das::imgui_SetTooltip)>(*this, lib, "SetTooltip", SideEffects::worstDefault,
                                                   "das::imgui_SetTooltip");
    addExtern<DAS_BIND_FUN(das::imgui_TextUnformatted)>(*this, lib, "TextUnformatted", SideEffects::worstDefault,
                                                        "das::imgui_TextUnformatted")
        ->arg("text");

    // --- InputText ---
    addExtern<DAS_BIND_FUN(das::imgui_InputText)>(*this, lib, "_builtin_InputText", SideEffects::worstDefault,
                                                  "das::imgui_InputText");
    addExtern<DAS_BIND_FUN(das::imgui_InputTextWithHint)>(*this, lib, "_builtin_InputTextWithHint",
                                                          SideEffects::worstDefault, "das::imgui_InputTextWithHint");
    addExtern<DAS_BIND_FUN(das::imgui_InputTextMultiline), SimNode_ExtFuncCall, imguiTempFn>(
        *this, lib, "_builtin_InputTextMultiline", SideEffects::worstDefault, "das::imgui_InputTextMultiline");

    // --- ImGuiTextFilter ---
    addExtern<DAS_BIND_FUN(das::imgui_PassFilter)>(*this, lib, "PassFilter", SideEffects::worstDefault,
                                                   "das::imgui_PassFilter");
    addExtern<DAS_BIND_FUN(das::imgui_text_range_string)>(*this, lib, "string", SideEffects::worstDefault,
                                                          "das::imgui_text_range_string");

    // --- ImColor ---
    addExtern<DAS_BIND_FUN(das::imgui_HSV)>(*this, lib, "HSV", SideEffects::none, "das::imgui_HSV")
        ->args({"h", "s", "v", "a"})
        ->arg_init(3, new ExprConstFloat(1.0f));

    // --- ImDrawList text ---
    addExtern<DAS_BIND_FUN(das::imgui_AddText), SimNode_ExtFuncCall, imguiTempFn>(
        *this, lib, "AddText", SideEffects::worstDefault, "das::imgui_AddText");
    addExtern<DAS_BIND_FUN(das::imgui_AddText2), SimNode_ExtFuncCall, imguiTempFn>(
        *this, lib, "AddText", SideEffects::worstDefault, "das::imgui_AddText2")
        ->args({"drawList", "font", "font_size", "pos", "col", "text", "wrap_width", "cpu_fine_clip_rect"})
        ->arg_init(6, new ExprConstFloat(0.0f))
        ->arg_init(7, new ExprConstPtr());

    // --- ImGuiTextBuffer ---
    addExtern<DAS_BIND_FUN(das::imgui_GTB_Append)>(*this, lib, "append", SideEffects::worstDefault,
                                                   "das::imgui_GTB_Append");
    addExtern<DAS_BIND_FUN(das::imgui_GTB_At)>(*this, lib, "at", SideEffects::worstDefault, "das::imgui_GTB_At");
    addExtern<DAS_BIND_FUN(das::imgui_GTB_SetAt)>(*this, lib, "set_at", SideEffects::worstDefault,
                                                  "das::imgui_GTB_SetAt");
    addExtern<DAS_BIND_FUN(das::imgui_GTB_Slice)>(*this, lib, "slice", SideEffects::worstDefault,
                                                  "das::imgui_GTB_Slice");

    // --- ImGuiInputTextCallbackData ---
    addExtern<DAS_BIND_FUN(das::imgui_InsertChars)>(*this, lib, "InsertChars", SideEffects::worstDefault,
                                                    "das::imgui_InsertChars");

    // --- SetNextWindowSizeConstraints ---
    addExtern<DAS_BIND_FUN(das::imgui_SetNextWindowSizeConstraints), SimNode_ExtFuncCall, imguiTempFn>(
        *this, lib, "_builtin_SetNextWindowSizeConstraints", SideEffects::worstDefault,
        "das::imgui_SetNextWindowSizeConstraints");
    addExtern<DAS_BIND_FUN(das::imgui_SetNextWindowSizeConstraintsNoCallback), SimNode_ExtFuncCall, imguiTempFn>(
        *this, lib, "SetNextWindowSizeConstraints", SideEffects::worstDefault,
        "das::imgui_SetNextWindowSizeConstraintsNoCallback")
        ->args({"size_min", "size_max"});

    // --- ImGuiTableColumnSortSpecs ---
    addExtern<DAS_BIND_FUN(das::imgui_SortDirection)>(*this, lib, "SortDirection", SideEffects::none,
                                                      "das::imgui_SortDirection");

    // --- CalcTextSize ---
    addExtern<DAS_BIND_FUN(das::imgui_CalcTextSize)>(*this, lib, "CalcTextSize", SideEffects::worstDefault,
                                                     "das::imgui_CalcTextSize")
        ->args({"text", "hide_text_after_double_hash", "wrap_width"})
        ->arg_init(1, new ExprConstBool(false))
        ->arg_init(2, new ExprConstFloat(-1.0f));

    // --- Combo ---
    addExtern<DAS_BIND_FUN(das::imgui_Combo)>(*this, lib, "_builtin_Combo", SideEffects::worstDefault,
                                              "das::imgui_Combo");

    // --- PlotLines / PlotHistogram ---
    addExtern<DAS_BIND_FUN(das::imgui_PlotLines)>(*this, lib, "_builtin_PlotLines", SideEffects::worstDefault,
                                                  "das::imgui_PlotLines");
    addExtern<DAS_BIND_FUN(das::imgui_PlotHistogram)>(*this, lib, "_builtin_PlotHistogram", SideEffects::worstDefault,
                                                      "das::imgui_PlotHistogram");

    // --- Additional default value fixups ---
    // These fix defaults that the generator couldn't handle automatically
    auto fixDefault = [&](const char *name, int argIdx, auto expr) {
        auto fns = findUniqueFunction(name);
        if (fns)
        {
            fns->arg_init(argIdx, expr);
        }
    };

    // Fix const ImVec2& defaults that use ImVec2(0,0)
    // Note: these may already be set by the generator, but we ensure correctness
}

das::ModuleAotType das::Module_imgui::aotRequire(das::TextWriter &tw) const
{
    tw << "#include \"../modules/dasimgui/src/imgui_stub.h\"\n";
    tw << "#include \"daScript/simulate/bind_enum.h\"\n";
    return das::ModuleAotType::cpp;
}

REGISTER_MODULE_IN_NAMESPACE(Module_imgui, das);

