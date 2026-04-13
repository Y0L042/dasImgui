#pragma once

#include "imgui_das.h"

#include "daScript/misc/platform.h"
#include "daScript/ast/ast.h"
#include "daScript/ast/ast_interop.h"
#include "daScript/ast/ast_handle.h"
#include "daScript/ast/ast_typefactory_bind.h"
#include "daScript/simulate/bind_enum.h"

namespace das {
class Module_imgui;
}

class das::Module_imgui : public das::Module {
public:
    Module_imgui();

protected:
    virtual bool initDependencies() override;
    void initMain();
    void initAotAlias();
    virtual das::ModuleAotType aotRequire(das::TextWriter &tw) const override;

public:
    das::ModuleLibrary lib;
    bool initialized = false;
};
