#pragma once
#include "BaseStrategy.hpp"

class GoStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/main.go"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"go", "build", "-ldflags", "-s -w", "-o", "/tmp/program_go", "/tmp/main.go"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"/tmp/program_go"};
    }

    void setup_environment() const override {
        setenv("HOME", "/tmp", 1);
        setenv("GOCACHE", "/tmp/.gocache", 1);
        setenv("GO111MODULE", "off", 1);
        setenv("CGO_ENABLED", "0", 1);
    }

    std::string get_compiled_binary_path() const override { return "/tmp/program_go"; }
};