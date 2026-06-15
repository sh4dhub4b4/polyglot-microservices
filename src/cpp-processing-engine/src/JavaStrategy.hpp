#pragma once
#include "BaseStrategy.hpp"

class JavaStrategy : public BaseStrategy
{
protected:
    std::string get_source_file_path() const override { return "/tmp/Main.java"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"javac", "-J-Xmx128m", "-J-Xms32m", "-J-XX:MaxMetaspaceSize=64m", "-J-XX:CompressedClassSpaceSize=32m", "-J-Xss256k", "-J-XX:MaxDirectMemorySize=10m", "/tmp/Main.java"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"java", "-Xmx128m", "-Xms32m", "-XX:MaxMetaspaceSize=64m", "-XX:CompressedClassSpaceSize=32m", "-XX:ReservedCodeCacheSize=32m", "-XX:+UseSerialGC", "-Xss256k", "-XX:MaxDirectMemorySize=10m", "-cp", "/tmp", "Main"};
    }
};