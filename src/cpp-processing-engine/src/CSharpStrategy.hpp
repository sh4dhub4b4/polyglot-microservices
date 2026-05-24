#pragma once
#include "BaseStrategy.hpp"

class CSharpStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/Program.cs"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"mcs", "-out:/tmp/Program.exe", "/tmp/Program.cs"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"mono", "/tmp/Program.exe"};
    }

    std::string get_compiled_binary_path() const override { return "/tmp/Program.exe"; }
};