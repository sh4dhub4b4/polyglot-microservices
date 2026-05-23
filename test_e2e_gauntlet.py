import asyncio
import websockets
import json
import uuid
import time
import random

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
        "source_code": r"""
x=input();print("Hello ",x)
"""  # Intentional Syntax Error (printf instead of print)
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
    println!("Hello {} from Rust! 🦀", name);
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


}


async def run_virtual_student(student_number):
    uri = "ws://127.0.0.1:8080/ws/execute"
    await asyncio.sleep(random.uniform(0.0, 1.0)) # Anti-DDoS Jitter
    
    stdId = str(uuid.uuid4())

    lang = ["rust","javascript","cpp","c","go","python","java", "csharp"]  # Test all three
    for lang_choice in lang:
        # if lang_choice!="java":
        #     continue
        payload = {
        "student_id": stdId,
        "course_code": PAYLOADS[lang_choice]["course_code"],
        "language": PAYLOADS[lang_choice]["language"],
        "stdin_data": r"""2026
""",
        "source_code": PAYLOADS[lang_choice]["source_code"]
        }
        
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(payload))
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    # print(data)
                    status = data.get("status")
                    
                    if status == "executing":
                        print(f"🚀 [Std-{student_number:02d} | {lang_choice.upper()}] EXECUTING CODE...")
                    elif status == "completed":
                        print(f"✅ [Std-{student_number:02d} | {lang_choice.upper()}] EXECUTION COMPLETED")
                        print(f"   ┣ Exit Code: {data.get('exit_code')}")
                        
                        # Handle Explicit Compilation Failures
                        if data.get("compilation_failed"):
                            print(f"   ┣ 🚨 COMPILATION ERROR:\n{data.get('stderr_output', '').strip()}")
                        else:
                            # Handle Runtime Outputs (Both Stderr and Stdout)
                            stdout = data.get('stdout_output', '').strip()
                            stderr = data.get('stderr_output', '').strip()
                            
                            if stdout:
                                print(f"   ┣ 📝 STDOUT:\n{stdout}")
                            if stderr:
                                print(f"   ┣ ⚠️ STDERR (Runtime Error):\n{stderr}")
                                
                        print("-" * 60)
                        break
                    elif status == "error":
                        print(f"❌ [Std-{student_number:02d}] SYSTEM ERROR: {data['message']}")
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