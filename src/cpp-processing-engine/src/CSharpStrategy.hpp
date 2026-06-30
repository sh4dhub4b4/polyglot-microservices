#pragma once
#include "BaseStrategy.hpp"

class CSharpStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/Program.cs"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"sh", "-c", "export HOME=/tmp && export DOTNET_CLI_HOME=/tmp && cd /tmp && dotnet new console -n App --force > /dev/null && cp *.cs App/ && cd App && dotnet build -c Release -o /tmp/AppBin"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"dotnet", "/tmp/AppBin/App.dll"};
    }

    void setup_environment() const override {
        setenv("DOTNET_SYSTEM_CONSOLE_UNBUFFERED", "1", 1); // ponytail: .NET bypasses C stdio, stdbuf has no effect
    }

    std::string get_compiled_binary_path() const override { return ""; }
};