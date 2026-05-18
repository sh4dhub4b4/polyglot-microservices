#include "httplib.h"
#include "json.hpp"
#include "SandboxOrchestrator.hpp"
#include <iostream>

using json = nlohmann::json;

int main()
{
    httplib::Server svr;
    SandboxOrchestrator orchestrator;

    std::cout << "Starting ECI Secure Execution Sandbox on port 8080..." << std::endl;

    svr.Post("/api/v1/execute", [&](const httplib::Request &req, httplib::Response &res)
             {
        try {
            // 1. Parse the incoming JSON payload from the API Gateway
            auto payload = json::parse(req.body);
            std::string language = payload.at("language").get<std::string>();
            std::string source_code = payload.at("source_code").get<std::string>();
            std::string stdin_data = payload.contains("stdin_data") ? payload.at("stdin_data").get<std::string>() : "";

            // 2. Configure the Orchestrator for the requested language
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

    // Listen on all network interfaces (0.0.0.0) so Kubernetes can route traffic to it
    svr.listen("0.0.0.0", 8080);
    return 0;
}