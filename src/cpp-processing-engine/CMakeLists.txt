cmake_minimum_required(VERSION 3.10)
project(cpp_engine)

# Tell CMake to compile main.cpp into an executable named 'engine_binary'
add_executable(engine_binary src/main.cpp)
# Add this line at the bottom of your CMakeLists.txt
target_link_libraries(engine_binary seccomp) 