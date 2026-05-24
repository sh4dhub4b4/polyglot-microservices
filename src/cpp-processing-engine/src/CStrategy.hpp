#pragma once
#include "BaseStrategy.hpp"

class CStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/main.c"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"gcc", "-O2", "/tmp/main.c", "-o", "/tmp/program_c"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"/tmp/program_c"};
    }

    std::string get_compiled_binary_path() const override { return "/tmp/program_c"; }
};