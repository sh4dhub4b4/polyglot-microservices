#pragma once
#include "BaseStrategy.hpp"

class PythonStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/sandbox_exec.py"; }
    
    std::vector<std::string> get_compile_command() const override { return {}; } // No compilation
    
    std::vector<std::string> get_execute_command() const override {
        return {"python3", "-u", "/tmp/sandbox_exec.py"};
    }
};