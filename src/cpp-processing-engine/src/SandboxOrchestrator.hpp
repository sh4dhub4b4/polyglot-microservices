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
#include <memory>
#include <stdexcept>

class SandboxOrchestrator
{
private:
    std::unique_ptr<IExecutionStrategy> strategy;

public:
    void set_language(const std::string &language)
    {
        if (language == "python")
        {
            strategy = std::make_unique<PythonStrategy>();
        }
        else if (language == "cpp" || language == "c++")
        {
            strategy = std::make_unique<CppStrategy>();
        } // 🚀 NEW: JVM Routing
        else if (language == "java" || language == "kotlin")
        {
            strategy = std::make_unique<JavaStrategy>();
        }
        // 🚀 NEW: .NET Routing
        else if (language == "csharp" || language == "c#")
        {
            strategy = std::make_unique<CSharpStrategy>();
        }
        // 🚀 NEW: C Routing
        else if (language == "c")
        {
            strategy = std::make_unique<CStrategy>();
        }
        // 🚀 NEW: Golang Routing
        else if (language == "go" || language == "golang")
        {
            strategy = std::make_unique<GoStrategy>();
        }
        // 🚀 NEW: Golang Routing
        else if (language == "node" || language == "npm" || language == "nodejs" || language == "javascript")
        {
            strategy = std::make_unique<NodeStrategy>();
        }
        // 🚀 NEW: Golang Routing
        else if (language == "rust" || language == "rustc")
        {
            strategy = std::make_unique<RustStrategy>();
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
};