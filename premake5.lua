project "dasimgui"
    kind "StaticLib"
    language "C++"
    cppdialect "C++17"
    staticruntime "Off"

    targetdir ("bin/" .. outputdir .. "/%{prj.name}")
    objdir ("bin-int/" .. outputdir .. "/%{prj.name}")

    files {
        "src/**.h",
        "src/**.cpp",
        "src/**.inc",
    }

    -- Don't compile .inc files
    filter "files:**.inc"
        buildaction "None"
    filter {}

    -- Don't compile .das files
    filter "files:**.das"
        buildaction "None"
    filter {}

    includedirs {
        "src",
    }

    externalincludedirs {
        DASIMGUI_IMGUI_INCLUDE or "",
        DASIMGUI_DASLANG_INCLUDE or "",
    }

    defines {
        "IMGUI_DISABLE_OBSOLETE_FUNCTIONS",
        "DAS_ENABLE_EXCEPTIONS=1",
        "DAS_SMART_PTR_DEBUG=1",
        "DAS_ENABLE_DLL=1",
        "DAS_MOD_EXPORTS",
    }

    filter "system:windows"
        systemversion "latest"

    filter "action:vs*"
        buildoptions {
            "/utf-8",
            '/Zc:__cplusplus',
            '/Zc:preprocessor',
            '/bigobj'
        } 

    filter "configurations:Debug"
        runtime "Debug"
        symbols "on"

    filter "configurations:Release"
        runtime "Release"
        optimize "on"

    filter "configurations:Dist"
        runtime "Release"
        optimize "on"
