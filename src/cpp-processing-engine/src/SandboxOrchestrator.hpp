#pragma once
#include "IExecutionStrategy.hpp"
#include "PythonStrategy.hpp"
#include "CppStrategy.hpp"
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
        bool compiled = strategy->compile(source_code, compile_errors); // 👈 Two-Phase Call

        if (!compiled)
        {
            // Compilation fail korle immediate return koro
            return {-1, "", compile_errors, 0.0, false, true};
        }
        return strategy->execute(source_code, stdin_data, 5000);
    }
};