import subprocess
import time
import urllib.request
import json
import webbrowser

HOST_API_PORT = "8085"
HOST_VNC_PORT = "5905"

print("🚀 Step 1/4: Building GUI Docker Image (eci-gui-engine)...")
subprocess.run(["docker", "build", "-t", "eci-gui-engine", "-f", "src/gui-processing-engine/Dockerfile.gui", "src/gui-processing-engine"], check=True)

print("\n🚀 Step 2/4: Starting GUI Container (test-gui-pod)...")
subprocess.run(["docker", "rm", "-f", "test-gui-pod"], capture_output=True)
subprocess.run(["docker", "run", "-d", "--name", "test-gui-pod", "-p", f"{HOST_API_PORT}:8080", "-p", f"{HOST_VNC_PORT}:6080", "eci-gui-engine"], check=True)

print("\n⏳ Waiting for Xvfb and VNC server to boot up (5 seconds)...")
time.sleep(5)

print("\n🚀 Step 3/4: Injecting Java Swing Code via API...")

# A Temple Run style 2D lane-runner game in Java Swing
java_code = """
import java.awt.*;
import java.awt.event.*;
import java.util.ArrayList;
import java.util.Random;
import javax.swing.*;

public class TempleRunner extends JPanel implements ActionListener, KeyListener {
    private int playerLane = 1; // 0: Left, 1: Center, 2: Right
    private int score = 0;
    private boolean gameOver = false;
    private Timer timer;
    private ArrayList<Obstacle> obstacles;
    private Random random;

    private final int[] LANE_X = {50, 150, 250}; 
    private final int PLAYER_Y = 300;
    
    class Obstacle {
        int lane;
        int y;
        Obstacle(int lane, int y) { this.lane = lane; this.y = y; }
    }

    public TempleRunner() {
        setFocusable(true);
        addKeyListener(this);
        obstacles = new ArrayList<>();
        random = new Random();
        timer = new Timer(50, this);
        timer.start();
    }

    @Override
    public void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2d = (Graphics2D) g;
        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        // Draw Lanes
        g2d.setColor(Color.DARK_GRAY);
        g2d.fillRect(0, 0, 400, 400);
        g2d.setColor(Color.WHITE);
        g2d.drawLine(133, 0, 133, 400);
        g2d.drawLine(266, 0, 266, 400);

        if (gameOver) {
            g2d.setColor(Color.RED);
            g2d.setFont(new Font("Arial", Font.BOLD, 40));
            g2d.drawString("GAME OVER", 70, 200);
            g2d.setFont(new Font("Arial", Font.PLAIN, 20));
            g2d.drawString("Score: " + score, 150, 240);
            g2d.drawString("Press ENTER to Restart", 90, 280);
            return;
        }

        // Draw Player
        g2d.setColor(Color.GREEN);
        g2d.fillRoundRect(LANE_X[playerLane], PLAYER_Y, 40, 40, 10, 10);

        // Draw Obstacles
        g2d.setColor(Color.RED);
        for (Obstacle obs : obstacles) {
            g2d.fillRect(LANE_X[obs.lane], obs.y, 40, 40);
        }

        // Draw Score
        g2d.setColor(Color.YELLOW);
        g2d.setFont(new Font("Arial", Font.BOLD, 20));
        g2d.drawString("Score: " + score, 10, 30);
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        if (gameOver) return;

        // Move obstacles
        for (int i = 0; i < obstacles.size(); i++) {
            Obstacle obs = obstacles.get(i);
            obs.y += 10;
            
            // Collision detection
            if (obs.lane == playerLane && obs.y + 40 > PLAYER_Y && obs.y < PLAYER_Y + 40) {
                gameOver = true;
            }
        }

        // Remove off-screen obstacles & increase score
        if (!obstacles.isEmpty() && obstacles.get(0).y > 400) {
            obstacles.remove(0);
            score += 10;
        }

        // Spawn new obstacles
        if (random.nextInt(100) < 15) {
            if (obstacles.isEmpty() || obstacles.get(obstacles.size() - 1).y > 100) {
                obstacles.add(new Obstacle(random.nextInt(3), -40));
            }
        }

        repaint();
    }

    @Override
    public void keyPressed(KeyEvent e) {
        if (gameOver && e.getKeyCode() == KeyEvent.VK_ENTER) {
            gameOver = false;
            score = 0;
            obstacles.clear();
            playerLane = 1;
        }
        
        if (!gameOver) {
            if (e.getKeyCode() == KeyEvent.VK_LEFT && playerLane > 0) {
                playerLane--;
            } else if (e.getKeyCode() == KeyEvent.VK_RIGHT && playerLane < 2) {
                playerLane++;
            }
        }
    }
    
    @Override public void keyReleased(KeyEvent e) {}
    @Override public void keyTyped(KeyEvent e) {}

    public static void main(String[] args) {
        JFrame frame = new JFrame("Java Swing Temple Run");
        TempleRunner game = new TempleRunner();
        frame.add(game);
        frame.setSize(350, 430);
        frame.setVisible(true);
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
    }
}
"""

payload = {
    "project_id": "demo_java_templerun",
    "language": "java-gui",
    "files": {
        "TempleRunner.java": java_code
    }
}

req = urllib.request.Request(
    f"http://localhost:{HOST_API_PORT}/execute", 
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f"✅ API Response: {result}")
except Exception as e:
    print(f"❌ API Failed: {e}")
    exit(1)

print("\n🎉 Step 4/4: Ready for Visual Inspection!")
vnc_url = f"http://localhost:{HOST_VNC_PORT}/vnc_lite.html"
print("=========================================================")
print(f"👉 CLICK HERE TO VIEW YOUR JAVA GUI: {vnc_url}")
print("=========================================================")
print("When you open the link, click the 'Connect' button.")
print("To stop the test and clean up, run: docker rm -f test-gui-pod")

try:
    webbrowser.open(vnc_url)
except:
    pass
