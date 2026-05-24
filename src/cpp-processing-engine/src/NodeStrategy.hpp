#pragma once
#include "BaseStrategy.hpp"

class NodeStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/main.js"; }

    std::vector<std::string> get_compile_command() const override { 
        return {"node", "--check", "/tmp/main.js"}; 
    }

    std::vector<std::string> get_execute_command() const override {
        return {"node", "/tmp/main.js"};
    }

    void setup_environment() const override {
        setenv("HOME", "/tmp", 1);
        setenv("NODE_OPTIONS", "--max-old-space-size=512", 1);
    }
};