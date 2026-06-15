#pragma once
#include "IExecutionStrategy.hpp"
#include "JavaStrategy.hpp"
#include "CSharpStrategy.hpp"
#include "PythonStrategy.hpp"
#include "CppStrategy.hpp"
#include "RustStrategy.hpp"
#include "NodeStrategy.hpp"
// 🚀 NEW: Import the new strategies
#include "CStrategy.hpp"
#include "GoStrategy.hpp"
#include "WasmStrategy.hpp"
#include "WasmRustStrategy.hpp"
#include "WasmGoStrategy.hpp"
#include <memory>
#include <stdexcept>

class SandboxOrchestrator
{
private:
    std::unique_ptr<IExecutionStrategy> strategy;

public:
    void set_language(const std::string &language)
    {
        if (language == "python" || language == "python-ds")
        {
            strategy = std::make_unique<PythonStrategy>();
        }
        else if (language == "cpp" || language == "c++" || language == "cpp-basic")
        {
            strategy = std::make_unique<CppStrategy>();
        }
        // 🚀 NEW: WASM Routing
        else if (language == "wasm-cpp")
        {
            strategy = std::make_unique<WasmStrategy>();
        } // 🚀 NEW: JVM Routing
        else if (language == "java" || language == "kotlin" || language == "java-basic")
        {
            strategy = std::make_unique<JavaStrategy>();
        }
        // 🚀 NEW: .NET Routing
        else if (language == "csharp" || language == "c#" || language == "csharp-dotnet")
        {
            strategy = std::make_unique<CSharpStrategy>();
        }
        // 🚀 NEW: C Routing
        else if (language == "c")
        {
            strategy = std::make_unique<CStrategy>();
        }
        // 🚀 NEW: Golang Routing
        else if (language == "go" || language == "golang" || language == "go-sys")
        {
            strategy = std::make_unique<GoStrategy>();
        }
        // 🚀 NEW: Node.js Routing
        else if (language == "node" || language == "npm" || language == "nodejs" || language == "javascript" || language == "node-js")
        {
            strategy = std::make_unique<NodeStrategy>();
        }
        // 🚀 NEW: Rust Routing
        else if (language == "rust" || language == "rustc" || language == "rust-sys")
        {
            strategy = std::make_unique<RustStrategy>();
        }
        else if (language == "gui-opengl")
        {
            // GUI can use CppStrategy for basic execution or a specialized one
            strategy = std::make_unique<CppStrategy>();
        }
        else if (language == "wasm-rust")
        {
            strategy = std::make_unique<WasmRustStrategy>();
        }
        else if (language == "wasm-go")
        {
            strategy = std::make_unique<WasmGoStrategy>();
        }
        else
        {
            throw std::invalid_argument("Unsupported runtime environment: " + language);
        }
    }

    ExecutionResult run(const std::string &source_code, const std::string &stdin_data)
    {
        if (!strategy)
            throw std::runtime_error("Strategy not set.");

        std::string compile_errors;
        // Phase 1: Compile
        bool compiled = strategy->compile(source_code, compile_errors);

        if (!compiled)
        {
            // Immediate return if compiler (gcc/go/g++) fails
            return {-1, "", compile_errors, 0.0, false, true};
        }

        // Phase 2: Execute (Orchestrator asks the strategy HOW to run itself)
        return strategy->execute(source_code, stdin_data, 5000);
    }

    // ═══════════════════════════════════════════════════════════════
    // Interactive Mode Accessors (Used by InteractiveSession)
    // ═══════════════════════════════════════════════════════════════

    ExecutionResult execute_only(const std::string &source_code, const std::string &stdin_data)
    {
        if (!strategy) throw std::runtime_error("Strategy not set.");
        return strategy->execute(source_code, stdin_data, 5000);
    }

    /** @brief Compile-only (Phase 1 for interactive mode). */
    bool compile_only(const std::string &source_code, std::string &compile_errors)
    {
        if (!strategy) throw std::runtime_error("Strategy not set.");
        return strategy->compile(source_code, compile_errors);
    }

    /** @brief Returns the execution command from the active strategy. */
    std::vector<std::string> get_execute_command() const
    {
        if (!strategy) throw std::runtime_error("Strategy not set.");
        return strategy->get_execute_command_public();
    }

    /** @brief Returns the source file path the strategy expects. */
    std::string get_source_file_path() const
    {
        if (!strategy) throw std::runtime_error("Strategy not set.");
        return strategy->get_source_file_path_public();
    }

    /** @brief Returns true if the strategy is for an interpreted language. */
    bool is_interpreted() const
    {
        if (!strategy) throw std::runtime_error("Strategy not set.");
        return strategy->is_interpreted();
    }

    /** @brief Returns the environment setup function from the strategy. */
    std::function<void()> get_setup_environment_fn() const
    {
        if (!strategy) throw std::runtime_error("Strategy not set.");
        return strategy->get_setup_environment_fn();
    }
};