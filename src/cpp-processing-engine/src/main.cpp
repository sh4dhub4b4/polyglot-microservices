#include "httplib.h"
#include "json.hpp"
#include "SandboxOrchestrator.hpp"
#include "InteractiveSession.hpp"
#include "WasmStrategy.hpp"
#include "CppStrategy.hpp"
#include "PythonStrategy.hpp"
#include "JavaStrategy.hpp"
#include "CSharpStrategy.hpp"
#include "NodeStrategy.hpp"
#include "RustStrategy.hpp"
#include "GoStrategy.hpp"
#include "CStrategy.hpp"
#include "WasmRustStrategy.hpp"
#include "WasmGoStrategy.hpp"
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <mutex>
#include <atomic>

using namespace httplib;
using json = nlohmann::json;

// Factory function to get the right strategy based on environment
std::unique_ptr<IExecutionStrategy> get_strategy(const std::string& env_type) {
    std::unique_ptr<IExecutionStrategy> strategy;

    if (env_type == "cpp-basic" || env_type == "cpp-sys") {
        strategy = std::make_unique<CppStrategy>();
    } else if (env_type == "wasm-cpp") {
        strategy = std::make_unique<WasmStrategy>();
    } else if (env_type == "wasm-rust") {
        strategy = std::make_unique<WasmRustStrategy>();
    } else if (env_type == "wasm-go") {
        strategy = std::make_unique<WasmGoStrategy>();
    } else if (env_type == "rust-sys") {
        strategy = std::make_unique<RustStrategy>();
    } else if (env_type == "python-ds" || env_type == "python-ml") {
        strategy = std::make_unique<PythonStrategy>();
    } else if (env_type == "java-basic" || env_type == "java-spring") {
        strategy = std::make_unique<JavaStrategy>();
    } else if (env_type == "csharp-dotnet") {
        strategy = std::make_unique<CSharpStrategy>();
    } else if (env_type == "node-js" || env_type == "node-express") {
        strategy = std::make_unique<NodeStrategy>();
    } else if (env_type == "go-sys" || env_type == "go-web") {
        strategy = std::make_unique<GoStrategy>();
    } else if (env_type == "c-sys") {
        strategy = std::make_unique<CStrategy>();
    }
    
    return strategy;
}

// Writes all files from the "files" map to /tmp/ before compilation
void write_files(const json& payload) {
    if (payload.contains("files") && payload["files"].is_object()) {
        for (auto& [filename, content] : payload["files"].items()) {
            std::ofstream out("/tmp/" + filename);
            out << content.get<std::string>();
            out.close();
        }
    }
}

int main()
{
    httplib::Server svr;
    SandboxOrchestrator orchestrator;

    std::cout << "Starting ECI Secure Execution Sandbox on port 8080..." << std::endl;

    // ═══════════════════════════════════════════════════════════════
    // ENDPOINT 1: Batch Execution (Original — Untouched)
    // Used by: HttpExecutorAdapter → Worker → Redis → API Gateway
    // ═══════════════════════════════════════════════════════════════
    svr.Post("/api/v1/execute", [&](const httplib::Request &req, httplib::Response &res)
             {
        try {
            // 1. Parse the incoming JSON payload from the API Gateway
            auto payload = json::parse(req.body);
            std::string language = payload.at("language").get<std::string>();
            std::string source_code = payload.at("source_code").get<std::string>();
            std::string stdin_data = payload.contains("stdin_data") ? payload.at("stdin_data").get<std::string>() : "";

            // 2a. Write multi-file payloads (if any) to /tmp/
            write_files(payload);

            // 2b. Configure the Orchestrator for the requested language
            orchestrator.set_language(language);

            // 3. Execute the code safely inside our SecurityContainer constraints
            ExecutionResult exec_result = orchestrator.run(source_code,stdin_data);

            // 4. Package the results back into JSON
            json response_json = {
                {"exit_code", exec_result.exit_code},
                {"stdout_output", exec_result.stdout_output},
                {"stderr_output", exec_result.stderr_output},
                {"memory_limit_exceeded", exec_result.memory_limit_exceeded},
                {"compilation_failed", exec_result.compilation_failed}
            };

            res.set_content(response_json.dump(), "application/json");

        } catch (const json::exception& e) {
            res.status = 400; // Bad Request
            res.set_content(json({{"error", "Invalid JSON format"}}).dump(), "application/json");
        } catch (const std::exception& e) {
            res.status = 500; // Internal Server Error
            res.set_content(json({{"error", e.what()}}).dump(), "application/json");
        } });

    // ═══════════════════════════════════════════════════════════════
    // ENDPOINT 2: Interactive Streaming Execution (NEW)
    // Used by: WebSocketRelayAdapter → Worker → Redis → API Gateway
    // Protocol: WebSocket with JSON messages
    //
    // Client → Server Messages:
    //   {"source_code": "...", "language": "cpp"}     (initial payload)
    //   {"stdin_data": "hello\n"}                     (user input)
    //
    // Server → Client Messages:
    //   {"status": "compiling"}
    //   {"status": "compile_error", "errors": "..."}
    //   {"status": "running"}
    //   {"status": "running", "stdout_output": "..."}
    //   {"status": "running", "stderr_output": "..."}
    //   {"status": "completed", "exit_code": 0}
    //   {"status": "timeout"}
    //   {"status": "error", "message": "..."}
    // ═══════════════════════════════════════════════════════════════
    svr.WebSocket("/ws/execute", [](const httplib::Request &req, httplib::ws::WebSocket &ws)
    {
        try
        {
            // ── Step 1: Receive initial payload ──
            std::string init_msg;
            auto read_result = ws.read(init_msg);
            if (read_result == httplib::ws::ReadResult::Fail)
            {
                return;
            }

            auto payload = json::parse(init_msg);
            std::string language = payload.at("language").get<std::string>();
            std::string source_code = payload.at("source_code").get<std::string>();

            // Write multi-file payloads (if any) to /tmp/ before compile
            write_files(payload);

            // ── Step 2: Create session and compile ──
            InteractiveSession session(language);

            ws.send(json({{"status", "compiling"}}).dump());

            auto compile_result = session.compile(source_code);
            if (!compile_result.success)
            {
                ws.send(json({
                    {"status", "compile_error"},
                    {"errors", compile_result.errors},
                    {"compilation_failed", true}
                }).dump());
                ws.close();
                return;
            }

            // ── Step 3: Start interactive execution ──
            if (session.is_compile_only()) {
                // This is a compile-only payload (like WASM). No execution process.
                auto exec_res = session.execute_only(source_code, "");
                json completed_msg;
                completed_msg["status"] = "completed";
                completed_msg["exit_code"] = exec_res.exit_code;
                completed_msg["memory_limit_exceeded"] = false;
                ws.send(completed_msg.dump());
                
                if (!exec_res.stdout_output.empty()) {
                    json running_msg;
                    running_msg["status"] = "running";
                    running_msg["stdout_output"] = exec_res.stdout_output;
                    ws.send(running_msg.dump());
                }
                ws.close();
                return;
            }

            if (!session.start_execution(source_code))
            {
                ws.send(json({
                    {"status", "error"},
                    {"message", "Failed to spawn execution process."}
                }).dump());
                ws.close();
                return;
            }

            ws.send(json({{"status", "running"}}).dump());

            std::atomic<bool> connection_active{true};
            std::mutex ws_mutex;

            auto safe_send = [&](const std::string &msg) {
                std::lock_guard<std::mutex> lock(ws_mutex);
                ws.send(msg);
            };

            // ── Step 4: Background Egress Thread ──
            // Polls stdout/stderr and streams it to the client
            std::thread output_thread([&]() {
                while (connection_active && session.is_running())
                {
                    std::string stdout_data = session.read_stdout();
                    if (!stdout_data.empty())
                    {
                        safe_send(json({
                            {"status", "running"},
                            {"stdout_output", stdout_data}
                        }).dump());
                    }

                    std::string stderr_data = session.read_stderr();
                    if (!stderr_data.empty())
                    {
                        safe_send(json({
                            {"status", "running"},
                            {"stderr_output", stderr_data}
                        }).dump());
                    }

                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                }

                // If loop ended because process exited, send final outputs and close
                if (connection_active)
                {
                    std::string final_stdout = session.read_stdout();
                    std::string final_stderr = session.read_stderr();

                    if (!final_stdout.empty())
                    {
                        safe_send(json({
                            {"status", "running"},
                            {"stdout_output", final_stdout}
                        }).dump());
                    }
                    if (!final_stderr.empty())
                    {
                        safe_send(json({
                            {"status", "running"},
                            {"stderr_output", final_stderr}
                        }).dump());
                    }

                    if (session.timed_out())
                    {
                        safe_send(json({
                            {"status", "timeout"},
                            {"message", "Execution timed out (idle for >15 seconds)."},
                            {"exit_code", session.exit_code()}
                        }).dump());
                    }
                    else
                    {
                        safe_send(json({
                            {"status", "completed"},
                            {"exit_code", session.exit_code()},
                            {"memory_limit_exceeded", session.memory_limit_exceeded()}
                        }).dump());
                    }

                    connection_active = false;
                    // Safely close the socket from this thread to unblock ws.read() in main thread
                    std::lock_guard<std::mutex> lock(ws_mutex);
                    ws.close();
                }
            });

            // ── Step 5: Main Ingress Loop (Blocking) ──
            // Wait for user input from WebSocket and push to stdin
            while (connection_active)
            {
                std::string client_msg;
                auto ws_result = ws.read(client_msg);
                
                if (ws_result == httplib::ws::ReadResult::Text)
                {
                    try
                    {
                        auto input = json::parse(client_msg);
                        if (input.contains("stdin_data"))
                        {
                            session.write_stdin(input.at("stdin_data").get<std::string>());
                            session.close_stdin(); // ponytail: EOF after first write (matches batch file semantics)
                        }
                        if (input.contains("close_stdin") && input.at("close_stdin").get<bool>())
                        {
                            session.close_stdin();
                        }
                    }
                    catch (const json::exception &)
                    {
                        // Raw text fallback
                        session.write_stdin(client_msg + "\n");
                    }
                }
                else if (ws_result == httplib::ws::ReadResult::Fail)
                {
                    // Client disconnected or socket closed
                    connection_active = false;
                    session.terminate();
                    break;
                }
            }

            connection_active = false;
            if (output_thread.joinable())
            {
                output_thread.join();
            }
        }
        catch (const json::exception &e)
        {
            try { ws.send(json({{"status", "error"}, {"message", "Invalid JSON format"}}).dump()); } catch (...) {}
            ws.close();
        }
        catch (const std::exception &e)
        {
            try { ws.send(json({{"status", "error"}, {"message", e.what()}}).dump()); } catch (...) {}
            ws.close();
        }
    });

    // Listen on all network interfaces (0.0.0.0) so Kubernetes can route traffic to it
    svr.listen("0.0.0.0", 8080);
    return 0;
}