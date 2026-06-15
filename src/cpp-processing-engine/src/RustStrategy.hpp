#pragma once
#include "BaseStrategy.hpp"

class RustStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/main.rs"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"sh", "-c", "export PATH=$PATH:/usr/local/cargo/bin && rustc -o /tmp/program_rust /tmp/main.rs"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"/tmp/program_rust"};
    }

    void setup_environment() const override {
        setenv("HOME", "/tmp", 1);
        setenv("CARGO_HOME", "/tmp/.cargo", 1);
        setenv("RUSTFLAGS", "-C target-cpu=generic -C opt-level=2", 1);
    }

    std::string get_compiled_binary_path() const override { return "/tmp/program_rust"; }
};