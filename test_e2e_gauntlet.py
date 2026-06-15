import asyncio
import websockets
import json
import uuid
import time
import random
import os

# 🌍 THE I/O STRESS PAYLOADS (Testing the RAM Disk)
PAYLOADS = {
    "cpp": {
        "language": "cpp",
        "course_code": "CS-201-ADV-CPP",
        "source_code": r"""#include <iostream>
using namespace std;
int main(){
string x;
cin>>x;
cout<<"Hello "<<x<<endl;
return 0;}"""
    },
    "python": {
        "language": "python",
        "course_code": "DS-301-PYTHON",
        "source_code": r"""import os
import sys

print("=== 🕵️‍♂️ HACKER PAYLOAD START ===")

# 1. Attempt to read K8s Secrets (Should be empty due to Mount Namespace)
print("\n[+] Attacking /var/run/secrets:")
try:
    print(os.listdir("/var/run/secrets"))
except Exception as e:
    print(f"Failed: {e}")

# 2. Attempt to read Proprietary Engine Binary (Should be empty due to Mount Namespace)
print("\n[+] Attacking /app:")
try:
    print(os.listdir("/app"))
    print("\n[+] Checking Mounts:")
    with open("/proc/mounts", "r") as f:
        print([line.strip() for line in f if "app" in line or "secrets" in line])
except Exception as e:
    print(f"Failed: {e}")

# 3. Attempt to kill the orchestrator (Should fail due to Seccomp)
print("\n[+] Attempting Process Isolation Break (Killall):")
# os.system("killall engine_binary")

# 4. Attempt Reverse Shell / Network Call (Should fail due to Seccomp blocking socket)
print("\n[+] Attempting Network Egress (Curl):")
os.system("curl -s --connect-timeout 2 http://8.8.8.8")

print("\n=== 🛑 HACKER PAYLOAD END ===")
"""
    },
    "go": {
        "language": "go",
        "course_code": "DS-308-GO",
        "source_code": r"""package main

import "fmt"

func main() {
    var name string
    var age int
    
    fmt.Println("Enter name and age:")
    fmt.Scanln(&name, &age)  // Reads until newline
    
    fmt.Printf("Hello %s, you are %d years old  %s", name, age)
}"""},
    "c": {
        "language": "c",
        "course_code": "DS-308-C",
        "source_code": r"""
#include <stdio.h>

// Function to calculate the Doomsday number for a given century
int getDoomsdayCenturyNumber(int year) {
    int centuryDoomsday = 5;
    for(int i = 1100; i <= year; i += 100) {
        if (centuryDoomsday == 0) {
            centuryDoomsday = 5;
        } else if (centuryDoomsday == 3) {
            centuryDoomsday -= 1;
        } else {
            centuryDoomsday -= 2;
        }
    }  
    return centuryDoomsday;
}

// Function to get the Doomsday date of the given month and year
int getDoomsdayMonthDate(int month, int year) {
    switch(month) {
        case 1:
            if ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) return 4; // Leap year
            else return 3; // Non-leap year
        case 2:
            if ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) return 29; // Leap year
            else return 28; // Non-leap year
        case 3: return 14;
        case 4: return 4;
        case 5: return 9;
        case 6: return 6;
        case 7: return 11;
        case 8: return 8;
        case 9: return 5;
        case 10: return 10;
        case 11: return 7;
        case 12: return 12;
        default: return -1; // Invalid month
    }
}

// Function to calculate the day code for the first date of the month
int getDayCodeOfFirstDate(int doomsdayOfYear, int doomsdayMonthDate) {
    for (int i = doomsdayMonthDate; i > 1; i--) {
        if (doomsdayOfYear == 0) {
            doomsdayOfYear = 6;
        } else {
            doomsdayOfYear--;
        }
    }
    return doomsdayOfYear;
}

// Main function to calculate the day code for the first day of a given month and year
int calculateFirstDayCode(int year, int month) {
    int century = (year / 100) * 100;
    int centuryDoomsdayNumber = getDoomsdayCenturyNumber(century);
    int yearPart = year - century;
    int sum = centuryDoomsdayNumber + yearPart + (yearPart / 4);
    int doomsdayOfYear = sum % 7;
    int doomsdayMonthDate = getDoomsdayMonthDate(month, year);
    return getDayCodeOfFirstDate(doomsdayOfYear, doomsdayMonthDate);
}

int main() {   
    int year;
    int MonthLastDate[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    
    printf("Enter the year [After 1500] :\n");
    scanf("%d", &year);
    
    printf("\n\n\nWelcome to the Year \n\t%d\n\n", year);
    
    // Adjust February days for leap year
    if ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) {
        MonthLastDate[1] = 29;
    }
    
    int MonthFirstDay[12];
    for (int i = 0; i < 12; i++) {
        MonthFirstDay[i] = calculateFirstDayCode(year, i + 1);
    }
    
    char *Month[] = {"JAN","FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"};
    
    for (int L = 0; L < 12; L++) {
        for (int i = 0; i < 20; i++) printf("-"); 
        printf("\n\t%s\n", Month[L]);
        for (int i = 0; i < 20; i++) printf("-"); 
        printf("\n");
        
        printf(" S  M  T  W  T  F  S \n\n");
    
        for (int MonthFirstDate = 1, i = 1; 1; i++) {
            if (i <= MonthFirstDay[L]) {
                printf("   ");
            } else {
                printf("%2d ", MonthFirstDate);
                MonthFirstDate++;
                if (i % 7 == 0) printf("\n");
            }
            if (MonthFirstDate == MonthLastDate[L] + 1) break;
        }
        printf("\n\n");
    }
    printf("<------- END ------>");
    return 0;
}


""",
    
    },

    "javascript": {
        "language": "javascript",
        "course_code": "WEB-101-JS",
        "source_code": r"""const fs = require('fs');

// Read all of stdin directly from file descriptor 0 (Standard for CP platforms)
const input = fs.readFileSync(0, 'utf-8').trim();

console.log(`Hello ${input} from Node.js!`);"""
    },
    
    "rust": {
        "language": "rust",
        "course_code": "SYS-402-RUST",
        "source_code": r"""use std::io::{self, Write};

fn main() {
    println!("Enter your name:");
    
    let mut name = String::new();
    io::stdin()
        .read_line(&mut name)
        .expect("Failed to read line");
    
    let name = name.trim();
    println!("Hello {} from Rust! 🦀", name)
}"""
    },
"java": {
        "language": "java",
        "course_code": "OOP-101-JAVA",
        "source_code": r"""import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;

abstract class Organism {
    protected String species;
    protected int age;
    
    public Organism(String s, int a) {
        species = s;
        age = a;
    }
    
    abstract void metabolize();
    
    public void age() {
        age++;
    }
    
    public String getSpecies() {
        return species;
    }
}

interface Evolvable {
    void mutate();
    
    default void adapt(Organism o) {
        System.out.println(o.getSpecies() + " adapting...");
    }
}

class Bacteria extends Organism implements Evolvable {
    private double divisionRate;
    
    public Bacteria(String s, double rate) {
        super(s, 0);
        divisionRate = rate;
    }
    
    void metabolize() {
        if (age % 2 == 0) {
            System.out.println(species + " fermenting at rate " + divisionRate);
        }
    }
    
    public void mutate() {
        divisionRate *= 1.5;
        System.out.println(species + " mutated! New rate: " + divisionRate);
    }
}

class Virus {
    private String strain;
    private int virulence;
    private List<String> mutations = new ArrayList<>();
    
    public Virus(String s, int v) {
        strain = s;
        virulence = v;
    }
    
    class Protein {
        String shape;
        
        Protein(String sh) {
            shape = sh;
        }
        
        void bind() {
            System.out.println("Protein " + shape + " binding to host");
        }
    }
    
    public Virus replicate() {
        Virus v = new Virus(
            strain + "-" + mutations.size(), 
            virulence + new Random().nextInt(10)
        );
        v.mutations = new ArrayList<>(mutations);
        v.mutations.add("MUT" + System.nanoTime() % 1000);
        return v;
    }
}

public class Main {
    private static final Map<String, Organism> ecosystem = new ConcurrentHashMap<>();
    private static final BlockingQueue<String> eventLog = new LinkedBlockingQueue<>();
    
    public static void main(String[] args) throws Exception {
        // Setup organisms
        Bacteria ecoli = new Bacteria("E.coli", 2.0);
        Bacteria staph = new Bacteria("S.aureus", 1.5);
        ecosystem.put("b1", ecoli);
        ecosystem.put("b2", staph);
        
        // Thread pool for concurrent operations
        ExecutorService executor = Executors.newFixedThreadPool(3);
        
        // Thread 1: Metabolism cycles
        executor.submit(() -> {
            for (int i = 0; i < 10; i++) {
                ecosystem.forEach((k, v) -> v.metabolize());
                eventLog.offer("METABOLISM_CYCLE_" + i);
                try {
                    Thread.sleep(50);
                } catch (Exception ex) {
                    // Continue despite interruption
                }
            }
        });
        
        // Thread 2: Mutation events
        executor.submit(() -> {
            for (int i = 0; i < 5; i++) {
                ecoli.mutate();
                staph.mutate();
                eventLog.offer("MUTATION_" + ecoli.hashCode());
                try {
                    Thread.sleep(100);
                } catch (Exception ex) {
                    // Continue despite interruption
                }
            }
        });
        
        // Thread 3: Virus replication with inner class
        executor.submit(() -> {
            Virus covid = new Virus("SARS-CoV-2", 95);
            for (int i = 0; i < 3; i++) {
                Virus mutant = covid.replicate();
                Virus.Protein spike = mutant.new Protein("Spike" + i);
                spike.bind();
                eventLog.offer("VIRUS_" + mutant.hashCode());
                try {
                    Thread.sleep(150);
                } catch (Exception ex) {
                    // Continue despite interruption
                }
            }
        });
        
        // Graceful shutdown
        executor.shutdown();
        executor.awaitTermination(5, TimeUnit.SECONDS);
        
        // Stream processing: Sort events
        List<String> sortedEvents = eventLog.stream()
            .sorted()
            .collect(Collectors.toList());
        
        // Stream reduction: Sum calculation
        int sum = IntStream.range(1, 11)
            .reduce(0, (a, b) -> a + b);
        
        // Parallel stream stress test
        long parallelCount = IntStream.range(0, 100000)
            .parallel()
            .map(x -> x * x)
            .filter(x -> x % 7 == 0)
            .count();
        
        // Output results
        System.out.println("=== Event Log (" + eventLog.size() + " events) ===");
        sortedEvents.forEach(e -> System.out.println("  " + e));
        
        System.out.println("=== Ecosystem Status ===");
        System.out.println("Organisms: " + ecosystem.size());
        System.out.println("Sum test: " + sum);
        System.out.println("Parallel stream matches: " + parallelCount);
        
        // Boundary exception test
        try {
            int[] arr = new int[3];
            arr[5] = 10; // ArrayIndexOutOfBoundsException
        } catch (ArrayIndexOutOfBoundsException e) {
            System.out.println("Boundary check: " + e.getMessage());
        }
        
        // Final stress indicator
        throw new RuntimeException("STRESS_TEST_COMPLETE");
    }
}"""
    },
    "csharp": {
        "language": "csharp",
        "course_code": "OOP-102-CSHARP",
        "source_code": r"""using System;
class Program {
    static void Main() {
        string name = Console.ReadLine();
        Console.WriteLine($"Hello {name} from C#!");
    }
}"""
    },
    "wasm": {
        "language": "wasm",
        "course_code": "WASM-101",
        "source_code": r"""#include <iostream>
using namespace std;
int main() {
    cout<<"Enter your name: ";
    string name;
    cin >> name;
    cout << "Hello " << name << " from WebAssembly (WASM)!" << endl;
    return 0;
}"""
    },
    "wasm-rust": {
        "language": "rust",
        "course_code": "WASM-102",
        "source_code": r"""fn main() {
    println!("Hello from WebAssembly Rust!");
}"""
    },
    "wasm-go": {
        "language": "go",
        "course_code": "WASM-103",
        "source_code": r"""package main
import "fmt"
func main() {
    fmt.Println("Hello from WebAssembly Go!")
}"""
    },
    "gui-cpp": {
        "language": "cpp-opengl",
        "course_code": "GUI-101",
        "source_code": r"""#include <GL/glew.h>
#include <GLFW/glfw3.h>

#include <iostream>
#include <vector>
#include <cmath>
#include <ctime>

// ================= WINDOW SETTINGS =================
const unsigned int SCR_WIDTH = 800
const unsigned int SCR_HEIGHT = 600;

// ================= SHADERS =================

// Vertex Shader
const char *vertexShaderSource = "#version 330 core\n"
                                 "layout (location = 0) in vec3 aPos;\n"
                                 "void main()\n"
                                 "{\n"
                                 "   gl_Position = vec4(aPos, 1.0);\n"
                                 "}\0";

// Fragment Shader
const char *fragmentShaderSource = "#version 330 core\n"
                                   "out vec4 FragColor;\n"
                                   "uniform vec4 ourColor;\n"
                                   "void main()\n"
                                   "{\n"
                                   "   FragColor = ourColor;\n"
                                   "}\n\0";

// ================= FUNCTIONS =================

// Window resize callback
void framebuffer_size_callback(GLFWwindow *window, int width, int height)
{
    glViewport(0, 0, width, height);
}

// Keyboard input
void processInput(GLFWwindow *window)
{
    if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(window, true);
}

// Convert degrees to radians
float degToRad(float degrees)
{
    return degrees * 3.1415926f / 180.0f;
}

// ================= MAIN =================
int main()
{
    // ================= GLFW INIT =================
    glfwInit();

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow *window = glfwCreateWindow(
        SCR_WIDTH,
        SCR_HEIGHT,
        "Analog Clock - Native C++ OpenGL",
        NULL,
        NULL);

    if (window == NULL)
    {
        std::cout << "Failed to create GLFW window\n";
        glfwTerminate();
        return -1;
    }

    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

    // ================= GLEW =================
    glewExperimental = GL_TRUE;
    if (glewInit() != GLEW_OK)
    {
        std::cout << "Failed to initialize GLEW\n";
        return -1;
    }

    // ================= SHADERS =================
    
    // Vertex Shader
    unsigned int vertexShader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertexShader, 1, &vertexShaderSource, NULL);
    glCompileShader(vertexShader);
    
    // Check vertex shader compilation
    int success;
    char infoLog[512];
    glGetShaderiv(vertexShader, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        glGetShaderInfoLog(vertexShader, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::VERTEX::COMPILATION_FAILED\n" << infoLog << std::endl;
    }

    // Fragment Shader
    unsigned int fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragmentShader, 1, &fragmentShaderSource, NULL);
    glCompileShader(fragmentShader);
    
    // Check fragment shader compilation
    glGetShaderiv(fragmentShader, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        glGetShaderInfoLog(fragmentShader, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::FRAGMENT::COMPILATION_FAILED\n" << infoLog << std::endl;
    }

    // Shader Program
    unsigned int shaderProgram = glCreateProgram();
    glAttachShader(shaderProgram, vertexShader);
    glAttachShader(shaderProgram, fragmentShader);
    glLinkProgram(shaderProgram);
    
    // Check linking
    glGetProgramiv(shaderProgram, GL_LINK_STATUS, &success);
    if (!success)
    {
        glGetProgramInfoLog(shaderProgram, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::PROGRAM::LINKING_FAILED\n" << infoLog << std::endl;
    }

    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);

    // ================= CLOCK CIRCLE =================
    std::vector<float> circleVertices;
    std::vector<float> filledCircleVertices;

    float centerX = 0.0f;
    float centerY = 0.0f;
    float radius = 0.7f;

    // Generate outline circle points (for LINE_LOOP)
    for (int i = 0; i <= 360; i++)
    {
        float angle = degToRad(i);
        float x = centerX + cos(angle) * radius;
        float y = centerY + sin(angle) * radius;
        circleVertices.push_back(x);
        circleVertices.push_back(y);
        circleVertices.push_back(0.0f);
    }
    
    // Generate filled circle points (for TRIANGLE_FAN)
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

    // ================= VAO + VBO for Circle =================
    unsigned int circleVAO, circleVBO;
    glGenVertexArrays(1, &circleVAO);
    glGenBuffers(1, &circleVBO);
    
    glBindVertexArray(circleVAO);
    glBindBuffer(GL_ARRAY_BUFFER, circleVBO);
    glBufferData(GL_ARRAY_BUFFER, circleVertices.size() * sizeof(float), circleVertices.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
    glEnableVertexAttribArray(0);
    
    // ================= VAO + VBO for Filled Circle =================
    unsigned int filledCircleVAO, filledCircleVBO;
    glGenVertexArrays(1, &filledCircleVAO);
    glGenBuffers(1, &filledCircleVBO);
    
    glBindVertexArray(filledCircleVAO);
    glBindBuffer(GL_ARRAY_BUFFER, filledCircleVBO);
    glBufferData(GL_ARRAY_BUFFER, filledCircleVertices.size() * sizeof(float), filledCircleVertices.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
    glEnableVertexAttribArray(0);

    // Enable blending for transparency
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    // ================= RENDER LOOP =================
    while (!glfwWindowShouldClose(window))
    {
        processInput(window);

        // Get current system time
        time_t now = time(nullptr);
        struct tm *localTime = localtime(&now);

        int seconds = localTime->tm_sec;
        int minutes = localTime->tm_min;
        int hours = localTime->tm_hour % 12;
        
        // Fix: When hours = 0, it should be 12 o'clock
        float displayHours = (hours == 0) ? 12.0f : (float)hours;
        
        // Clockwise rotation means angles DECREASE as time increases
        float secondDegrees = 90.0f - (seconds / 60.0f) * 360.0f;
        float minuteDegrees = 90.0f - ((minutes + seconds / 60.0f) / 60.0f) * 360.0f;
        float hourDegrees = 90.0f - ((displayHours + minutes / 60.0f) / 12.0f) * 360.0f;
        
        // Convert to radians for OpenGL
        float secondAngle = degToRad(secondDegrees);
        float minuteAngle = degToRad(minuteDegrees);
        float hourAngle = degToRad(hourDegrees);

        // Hand lengths
        float secondLength = 0.65f;
        float minuteLength = 0.55f;
        float hourLength = 0.40f;

        float secondX = cos(secondAngle) * secondLength;
        float secondY = sin(secondAngle) * secondLength;
        float minuteX = cos(minuteAngle) * minuteLength;
        float minuteY = sin(minuteAngle) * minuteLength;
        float hourX = cos(hourAngle) * hourLength;
        float hourY = sin(hourAngle) * hourLength;

        // Clear screen
        glClearColor(0.05f, 0.05f, 0.1f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glUseProgram(shaderProgram);
        int colorLoc = glGetUniformLocation(shaderProgram, "ourColor");

        // ================= DRAW FILLED CIRCLE BACKGROUND =================
        glUniform4f(colorLoc, 0.15f, 0.15f, 0.2f, 0.9f);
        glBindVertexArray(filledCircleVAO);
        glDrawArrays(GL_TRIANGLE_FAN, 0, filledCircleVertices.size() / 3);

        // ================= DRAW CIRCLE OUTLINE =================
        glUniform4f(colorLoc, 1.0f, 1.0f, 1.0f, 1.0f);
        glBindVertexArray(circleVAO);
        glDrawArrays(GL_LINE_LOOP, 0, circleVertices.size() / 3);

        // ================= DRAW HOUR MARKERS (1-12) =================
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
        
        // Draw minute markers (smaller dots)
        glPointSize(4.0f);
        glUniform4f(colorLoc, 0.7f, 0.7f, 0.7f, 1.0f);
        
        for (int i = 1; i <= 60; i++)
        {
            if (i % 5 == 0) continue; // Skip hour markers
            
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

        // ================= DRAW SECOND HAND =================
        glUniform4f(colorLoc, 1.0f, 0.2f, 0.2f, 1.0f);  // Bright red
        glLineWidth(2.0f);
        
        float secondLineVertices[] = {0.0f, 0.0f, 0.0f, secondX, secondY, 0.0f};
        unsigned int lineVBO;
        glGenBuffers(1, &lineVBO);
        glBindBuffer(GL_ARRAY_BUFFER, lineVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(secondLineVertices), secondLineVertices, GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(0);
        glDrawArrays(GL_LINES, 0, 2);
        
        // Draw tip of second hand
        glPointSize(8.0f);
        float secondTip[] = {secondX, secondY, 0.0f};
        glBufferData(GL_ARRAY_BUFFER, sizeof(secondTip), secondTip, GL_STATIC_DRAW);
        glDrawArrays(GL_POINTS, 0, 1);
        glDeleteBuffers(1, &lineVBO);

        // ================= DRAW MINUTE HAND =================
        glUniform4f(colorLoc, 0.2f, 1.0f, 0.2f, 1.0f);  // Bright green
        glLineWidth(4.0f);
        
        float minuteLineVertices[] = {0.0f, 0.0f, 0.0f, minuteX, minuteY, 0.0f};
        glGenBuffers(1, &lineVBO);
        glBindBuffer(GL_ARRAY_BUFFER, lineVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(minuteLineVertices), minuteLineVertices, GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(0);
        glDrawArrays(GL_LINES, 0, 2);
        glDeleteBuffers(1, &lineVBO);

        // ================= DRAW HOUR HAND =================
        glUniform4f(colorLoc, 0.2f, 0.5f, 1.0f, 1.0f);  // Bright blue
        glLineWidth(6.0f);
        
        float hourLineVertices[] = {0.0f, 0.0f, 0.0f, hourX, hourY, 0.0f};
        glGenBuffers(1, &lineVBO);
        glBindBuffer(GL_ARRAY_BUFFER, lineVBO);
        glBufferData(GL_ARRAY_BUFFER, sizeof(hourLineVertices), hourLineVertices, GL_STATIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(0);
        glDrawArrays(GL_LINES, 0, 2);
        glDeleteBuffers(1, &lineVBO);

        // ================= DRAW CENTER POINT =================
        glUniform4f(colorLoc, 1.0f, 1.0f, 0.0f, 1.0f);  // Yellow
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

        // Debug output removed to prevent spamming stdout in container
        // ================= SWAP BUFFERS =================
        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    // ================= CLEANUP =================
    glDeleteVertexArrays(1, &circleVAO);
    glDeleteBuffers(1, &circleVBO);
    glDeleteVertexArrays(1, &filledCircleVAO);
    glDeleteBuffers(1, &filledCircleVBO);
    glDeleteProgram(shaderProgram);
    glfwTerminate();

    return 0;
}
"""

    },
    "gui-java": {
        "language": "java-gui",
        "course_code": "GUI-102",
        "source_code": r"""import javax.swing.*;
public class Main {
    public static void main(String[] args) {
        JFrame frame = new JFrame("Hello Java GUI");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(400, 300);
        JLabel label = new JLabel("Welcome to Java Swing in Browser!", SwingConstants.CENTER);
        frame.getContentPane().add(label);
        frame.setVisible(true);
    }
}"""
    }
}


async def run_virtual_student(student_number):
    uri = "ws://127.0.0.1:8080/ws/execute"
    await asyncio.sleep(random.uniform(0.0, 1.0)) # Anti-DDoS Jitter
    
    stdId = str(uuid.uuid4())

    test_scenarios = [
        {"lang": "gui-cpp"},
        {"lang": "gui-java"},
        {"lang": "wasm"},
        {"lang": "wasm-rust"},
        {"lang": "wasm-go"},
        {"lang": "cpp"},
        {"lang": "python"},
        {"lang": "csharp"},
        {"lang": "c"},
        {"lang": "java"},
        {"lang": "rust"},
        {"lang": "javascript"},
        {"lang": "go"},
    ]

    for attempt, scenario in enumerate(test_scenarios):
        lang_choice = scenario["lang"]
        
        print(f"\n--- Preparations for [Run {attempt+1} | {lang_choice.upper()}] ---")
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, f"Provide input for {lang_choice.upper()} (type 'None' to skip): ")
        scenario["input"] = user_input
        
        # 🚀 Map simple language names to actual PodCatalog IDs for the Orchestrator
        language_map = {
            "cpp": "cpp-basic",
            "python": "python-ds",
            "csharp": "csharp-dotnet",
            "java": "java-basic",
            "c": "cpp-basic", # C runs in cpp-basic engine
            "rust": "rust-sys",
            "javascript": "node-js",
            "go": "go-sys",
            "wasm": "wasm-cpp",
            "wasm-rust": "wasm-rust",
            "wasm-go": "wasm-go",
            "gui-cpp": "gui-opengl",
            "gui-java": "gui-java"
        }
        pod_catalog_id = language_map.get(lang_choice, "cpp-basic")

        payload = {
            "mode": "interactive" if "gui" in lang_choice or "wasm" in lang_choice else "batch",
            "student_id": stdId,
            "course_code": PAYLOADS[lang_choice]["course_code"],
            "env_type": pod_catalog_id,
            "source_code": PAYLOADS[lang_choice]["source_code"],
            "stdin_data": scenario.get("input", ""),
            "is_gui": lang_choice.startswith("gui-")
        }
        
        try:
            async with websockets.connect(uri) as websocket:
                start_req = time.time()
                await websocket.send(json.dumps(payload))
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    status = data.get("status")
                    
                    if status == "executing":
                        print(f"🚀 [Run {attempt+1} | {lang_choice.upper()}] EXECUTING CODE...")
                        
                        if payload.get("is_gui"):
                            pod_name = data.get("pod_name", "unknown-gui-pod")
                            print(f"\n" + "="*60)
                            print(f"🖥️  GUI APP LAUNCHED!")
                            print(f"👉 1. Open a new terminal and run this command to connect:")
                            print(f"      kubectl port-forward pod/{pod_name} 6080:6080 -n eci-sandboxes")
                            print(f"👉 2. Then open your browser to view the GUI:")
                            print(f"      http://localhost:6080/vnc.html")
                            print("="*60 + "\n")
                            
                        # If there is stdin_data to send interactively, send it now automatically
                        if scenario.get("input") and scenario["input"] != "None":
                            await websocket.send(json.dumps({
                                "stdin_data": scenario["input"] + "\n",
                                "close_stdin": True
                            }))
                    elif status == "running":
                        stdout = data.get('stdout_output', '')
                        stderr = data.get('stderr_output', '')
                        if stdout:
                            print(stdout, end="", flush=True)
                        if stderr:
                            print(f"\n⚠️ STDERR: {stderr.strip()}", flush=True)
                    elif status == "completed":
                        end_req = time.time()
                        print(f"✅ [Run {attempt+1} | {lang_choice.upper()}] EXECUTION COMPLETED")
                        print(f"   ┣ Engine Exec Time: {data.get('execution_time_ms', 0)} ms")
                        print(f"   ┣ Total E2E Time: {(end_req - start_req)*1000:.2f} ms")
                        print(f"   ┣ Exit Code: {data.get('exit_code')}")
                        
                        if data.get("compilation_failed"):
                            print(f"   ┣ 🚨 COMPILATION ERROR:\n{data.get('stderr_output', '').strip()}")
                                
                        print("-" * 60)
                        
                        if payload.get("is_gui"):
                            print(f"⏳ Waiting for 90 seconds so you can interact with the GUI...")
                            await asyncio.sleep(90)
                            print(f"➡️  Moving to next test...")
                            
                        break
                    elif status == "timeout":
                        end_req = time.time()
                        print(f"⏳ [Run {attempt+1} | {lang_choice.upper()}] TIMEOUT: {data.get('message')}")
                        print(f"   ┣ Total E2E Time: {(end_req - start_req)*1000:.2f} ms")
                        
                        if data.get("postmortem_data"):
                            log_dir = "pod_error_logs"
                            os.makedirs(log_dir, exist_ok=True)
                            log_file = os.path.join(log_dir, f"{lang_choice}_timeout_{stdId[:8]}.json")
                            with open(log_file, "w", encoding="utf-8") as f:
                                json.dump(data["postmortem_data"], f, indent=4)
                            print(f"   ┣ 📄 Full Pod Logs & /tmp Snapshot saved to: {log_file}")
                            
                        print("-" * 60)
                        break
                    elif status == "compile_error":
                        print(f"🚨 [Run {attempt+1} | {lang_choice.upper()}] COMPILE ERROR:\n{data.get('errors')}")
                        print("-" * 60)
                        break
                    elif status == "error":
                        print(f"❌ [Std-{student_number:02d}] SYSTEM ERROR: {data.get('message')}")
                        
                        if data.get("postmortem_data"):
                            log_dir = "logs"
                            os.makedirs(log_dir, exist_ok=True)
                            log_file = os.path.join(log_dir, f"{lang_choice}_error_{stdId[:8]}.json")
                            with open(log_file, "w", encoding="utf-8") as f:
                                json.dump(data["postmortem_data"], f, indent=4)
                            print(f"   ┣ 📄 Full Pod Logs & /tmp Snapshot saved to: {log_file}")
                            
                        break
        except Exception as e:
            print(f"❌ [Std-{student_number:02d}] Connection failed: {e}")

async def main():
    print("🌐 LAUNCHING RAM-DISK & PARALLEL OPTIMIZATION VALIDATION 🌐")
    print("Sending 1 concurrent I/O intensive workloads to K8s Sandbox...\n")
    tasks = [run_virtual_student(1)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())