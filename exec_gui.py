import asyncio, json, websockets, sys

GUI_CODE = r"""#include <GL/glew.h>
#include <GLFW/glfw3.h>

#include <iostream>
#include <vector>
#include <cmath>
#include <ctime>

const unsigned int SCR_WIDTH = 800;
const unsigned int SCR_HEIGHT = 600;

const char *vertexShaderSource = "#version 330 core\n"
                                 "layout (location = 0) in vec3 aPos;\n"
                                 "void main()\n"
                                 "{\n"
                                 "   gl_Position = vec4(aPos, 1.0);\n"
                                 "}\0";

const char *fragmentShaderSource = "#version 330 core\n"
                                   "out vec4 FragColor;\n"
                                   "uniform vec4 ourColor;\n"
                                   "void main()\n"
                                   "{\n"
                                   "   FragColor = ourColor;\n"
                                   "}\n\0";

void framebuffer_size_callback(GLFWwindow *window, int width, int height)
{
    glViewport(0, 0, width, height);
}

void processInput(GLFWwindow *window)
{
    if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(window, true);
}

float degToRad(float degrees)
{
    return degrees * 3.1415926f / 180.0f;
}

int main()
{
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow *window = glfwCreateWindow(
        SCR_WIDTH, SCR_HEIGHT, "Analog Clock - Native C++ OpenGL",
        NULL, NULL);

    if (window == NULL)
    {
        std::cout << "Failed to create GLFW window\n";
        glfwTerminate();
        return -1;
    }

    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

    glewExperimental = GL_TRUE;
    if (glewInit() != GLEW_OK)
    {
        std::cout << "Failed to initialize GLEW\n";
        return -1;
    }

    unsigned int vertexShader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertexShader, 1, &vertexShaderSource, NULL);
    glCompileShader(vertexShader);

    int success;
    char infoLog[512];
    glGetShaderiv(vertexShader, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        glGetShaderInfoLog(vertexShader, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::VERTEX::COMPILATION_FAILED\n" << infoLog << std::endl;
    }

    unsigned int fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragmentShader, 1, &fragmentShaderSource, NULL);
    glCompileShader(fragmentShader);

    glGetShaderiv(fragmentShader, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        glGetShaderInfoLog(fragmentShader, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::FRAGMENT::COMPILATION_FAILED\n" << infoLog << std::endl;
    }

    unsigned int shaderProgram = glCreateProgram();
    glAttachShader(shaderProgram, vertexShader);
    glAttachShader(shaderProgram, fragmentShader);
    glLinkProgram(shaderProgram);

    glGetProgramiv(shaderProgram, GL_LINK_STATUS, &success);
    if (!success)
    {
        glGetProgramInfoLog(shaderProgram, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::PROGRAM::LINKING_FAILED\n" << infoLog << std::endl;
    }

    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);

    std::vector<float> circleVertices;
    std::vector<float> filledCircleVertices;

    float centerX = 0.0f;
    float centerY = 0.0f;
    float radius = 0.7f;

    for (int i = 0; i <= 360; i++)
    {
        float angle = degToRad(i);
        float x = centerX + cos(angle) * radius;
        float y = centerY + sin(angle) * radius;
        circleVertices.push_back(x);
        circleVertices.push_back(y);
        circleVertices.push_back(0.0f);
    }

    filledCircleVertices.push_back(centerX);
    filledCircleVertices.push_back(centerY);
    filledCircleVertices.push_back(0.0f);

    for (int i = 0; i <= 360; i++)
    {
        float angle = degToRad(i);
        float x = centerX + cos(angle) * radius;
        float y = centerY + sin(angle) * radius;
        filledCircleVertices.push_back(x);
        filledCircleVertices.push_back(y);
        filledCircleVertices.push_back(0.0f);
    }

    unsigned int circleVAO, circleVBO;
    glGenVertexArrays(1, &circleVAO);
    glGenBuffers(1, &circleVBO);

    glBindVertexArray(circleVAO);
    glBindBuffer(GL_ARRAY_BUFFER, circleVBO);
    glBufferData(GL_ARRAY_BUFFER, circleVertices.size() * sizeof(float), circleVertices.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
    glEnableVertexAttribArray(0);

    unsigned int filledCircleVAO, filledCircleVBO;
    glGenVertexArrays(1, &filledCircleVAO);
    glGenBuffers(1, &filledCircleVBO);

    glBindVertexArray(filledCircleVAO);
    glBindBuffer(GL_ARRAY_BUFFER, filledCircleVBO);
    glBufferData(GL_ARRAY_BUFFER, filledCircleVertices.size() * sizeof(float), filledCircleVertices.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
    glEnableVertexAttribArray(0);

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    while (!glfwWindowShouldClose(window))
    {
        processInput(window);

        time_t now = time(nullptr);
        struct tm *localTime = localtime(&now);

        int seconds = localTime->tm_sec;
        int minutes = localTime->tm_min;
        int hours = localTime->tm_hour % 12;

        float displayHours = (hours == 0) ? 12.0f : (float)hours;

        float secondDegrees = 90.0f - (seconds / 60.0f) * 360.0f;
        float minuteDegrees = 90.0f - ((minutes + seconds / 60.0f) / 60.0f) * 360.0f;
        float hourDegrees = 90.0f - ((displayHours + minutes / 60.0f) / 12.0f) * 360.0f;

        float secondAngle = degToRad(secondDegrees);
        float minuteAngle = degToRad(minuteDegrees);
        float hourAngle = degToRad(hourDegrees);

        float secondLength = 0.65f;
        float minuteLength = 0.55f;
        float hourLength = 0.40f;

        float secondX = cos(secondAngle) * secondLength;
        float secondY = sin(secondAngle) * secondLength;
        float minuteX = cos(minuteAngle) * minuteLength;
        float minuteY = sin(minuteAngle) * minuteLength;
        float hourX = cos(hourAngle) * hourLength;
        float hourY = sin(hourAngle) * hourLength;

        glClearColor(0.05f, 0.05f, 0.1f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glUseProgram(shaderProgram);
        int colorLoc = glGetUniformLocation(shaderProgram, "ourColor");

        glUniform4f(colorLoc, 0.15f, 0.15f, 0.2f, 0.9f);
        glBindVertexArray(filledCircleVAO);
        glDrawArrays(GL_TRIANGLE_FAN, 0, filledCircleVertices.size() / 3);

        glUniform4f(colorLoc, 1.0f, 1.0f, 1.0f, 1.0f);
        glBindVertexArray(circleVAO);
        glDrawArrays(GL_LINE_LOOP, 0, circleVertices.size() / 3);

        glUniform4f(colorLoc, 1.0f, 1.0f, 1.0f, 1.0f);

        for (int i = 1; i <= 12; i++)
        {
            float angleDegrees = 90.0f - (i * 30.0f);
            float angleRad = degToRad(angleDegrees);
            float markerX = cos(angleRad) * (radius - 0.08f);
            float markerY = sin(angleRad) * (radius - 0.08f);

            glPointSize(12.0f);

            float markerPoint[] = {markerX, markerY, 0.0f};
            unsigned int tempVBO;
            glGenBuffers(1, &tempVBO);
            glBindBuffer(GL_ARRAY_BUFFER, tempVBO);
            glBufferData(GL_ARRAY_BUFFER, sizeof(markerPoint), markerPoint, GL_STATIC_DRAW);
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
            glEnableVertexAttribArray(0);
            glDrawArrays(GL_POINTS, 0, 1);
            glDeleteBuffers(1, &tempVBO);
        }

        glPointSize(4.0f);
        glUniform4f(colorLoc, 0.7f, 0.7f, 0.7f, 1.0f);

        for (int i = 1; i <= 60; i++)
        {
            if (i % 5 == 0) continue;

            float angleDegrees = 90.0f - (i * 6.0f);
            float angleRad = degToRad(angleDegrees);
            float markerX = cos(angleRad) * (radius - 0.05f);
            float markerY = sin(angleRad) * (radius - 0.05f);

            float markerPoint[] = {markerX, markerY, 0.0f};
            unsigned int tempVBO;
            glGenBuffers(1, &tempVBO);
            glBindBuffer(GL_ARRAY_BUFFER, tempVBO);
            glBufferData(GL_ARRAY_BUFFER, sizeof(markerPoint), markerPoint, GL_STATIC_DRAW);
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
            glEnableVertexAttribArray(0);
            glDrawArrays(GL_POINTS, 0, 1);
            glDeleteBuffers(1, &tempVBO);
        }

        glUniform4f(colorLoc, 1.0f, 0.2f, 0.2f, 1.0f);
        glLineWidth(2.0f);

        float secondLineVertices[] = {0.0f, 0.0f, 0.0f, secondX, secondY, 0.0f};
        unsigned int lineVBO;
        glGenBuffers(1, &lineVBO);
        glBindBuffer(GL_ARRAY_BUFFER, lineVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(secondLineVertices), secondLineVertices, GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(0);
        glDrawArrays(GL_LINES, 0, 2);

        glPointSize(8.0f);
        float secondTip[] = {secondX, secondY, 0.0f};
        glBufferData(GL_ARRAY_BUFFER, sizeof(secondTip), secondTip, GL_STATIC_DRAW);
        glDrawArrays(GL_POINTS, 0, 1);
        glDeleteBuffers(1, &lineVBO);

        glUniform4f(colorLoc, 0.2f, 1.0f, 0.2f, 1.0f);
        glLineWidth(4.0f);

        float minuteLineVertices[] = {0.0f, 0.0f, 0.0f, minuteX, minuteY, 0.0f};
        glGenBuffers(1, &lineVBO);
        glBindBuffer(GL_ARRAY_BUFFER, lineVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(minuteLineVertices), minuteLineVertices, GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(0);
        glDrawArrays(GL_LINES, 0, 2);
        glDeleteBuffers(1, &lineVBO);

        glUniform4f(colorLoc, 0.2f, 0.5f, 1.0f, 1.0f);
        glLineWidth(6.0f);

        float hourLineVertices[] = {0.0f, 0.0f, 0.0f, hourX, hourY, 0.0f};
        glGenBuffers(1, &lineVBO);
        glBindBuffer(GL_ARRAY_BUFFER, lineVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(hourLineVertices), hourLineVertices, GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(0);
        glDrawArrays(GL_LINES, 0, 2);
        glDeleteBuffers(1, &lineVBO);

        glUniform4f(colorLoc, 1.0f, 1.0f, 0.0f, 1.0f);
        glPointSize(14.0f);

        float centerPoint[] = {0.0f, 0.0f, 0.0f};
        unsigned int centerVBO;
        glGenBuffers(1, &centerVBO);
        glBindBuffer(GL_ARRAY_BUFFER, centerVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(centerPoint), centerPoint, GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(0);
        glDrawArrays(GL_POINTS, 0, 1);
        glDeleteBuffers(1, &centerVBO);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glDeleteVertexArrays(1, &circleVAO);
    glDeleteBuffers(1, &circleVBO);
    glDeleteVertexArrays(1, &filledCircleVAO);
    glDeleteBuffers(1, &filledCircleVBO);
    glDeleteProgram(shaderProgram);
    glfwTerminate();

    return 0;
}
"""

async def run_gui(sid: str):
    async with websockets.connect("ws://localhost:8080/ws/execute") as ws:
        await ws.send(json.dumps({
            "source_code": GUI_CODE,
            "language": "gui-opengl",
            "env_type": "gui-opengl",
            "student_id": sid,
            "course_code": "GUI-101",
            "mode": "interactive",
            "is_gui": True
        }))
        async for msg in ws:
            d = json.loads(msg)
            s = d.get("status")
            pod = d.get("pod_name", "")
            out = d.get("stdout_output", "") or d.get("message", "")
            if pod:
                print("\n" + "="*60)
                print("GUI APP LAUNCHED!")
                print("Open a new terminal and run:")
                print(f"  kubectl port-forward pod/{pod} 6080:6080 -n eci-sandboxes")
                print("Then open in browser:")
                print("  http://localhost:6080/vnc.html")
                print("="*60 + "\n")
            if out:
                print(out, end="", flush=True)
            if s in ("completed", "error", "compile_error"):
                if d.get("compilation_failed"):
                    print(f"\nCOMPILATION ERROR:\n{d.get('stderr_output', '')}")
                print(f"\nDone. Status: {s}, Exit code: {d.get('exit_code')}")
                break

if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else "019efa0f-d6c8-7a1d-ab32-f97ba7672f98"
    asyncio.run(run_gui(sid))
