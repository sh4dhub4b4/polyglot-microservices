#pragma once
#include "BaseStrategy.hpp"

class GoStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/main.go"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"sh", "-c", "export HOME=/tmp && export GOCACHE=/tmp/.gocache && export GO111MODULE=auto && export CGO_ENABLED=0 && cd /tmp && ([ -f go.mod ] || /usr/local/go/bin/go mod init app) && /usr/local/go/bin/go build -ldflags=\"-s -w\" -o /tmp/program_go ."};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"/tmp/program_go"};
    }

    void setup_environment() const override {
        // Handled via inline exports for compilation to ensure correct propagation.
    }

    std::string get_compiled_binary_path() const override { return "/tmp/program_go"; }
};