#pragma once
#include "BaseStrategy.hpp"

class CppStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/main.cpp"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"sh", "-c", "cd /tmp && g++ -O2 -std=c++17 *.cpp -o student_exec"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"/tmp/student_exec"};
    }

    std::string get_compiled_binary_path() const override { return "/tmp/student_exec"; }
};