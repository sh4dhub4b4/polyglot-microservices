import pytest
from fastapi.testclient import TestClient
import time
import os
import sys
from unittest import mock

# Add the src directory to path to import the server
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from gui_server import app

client = TestClient(app)

# ==========================================
# DevSecOps & QA: GUI Engine Test Suite
# ==========================================

@mock.patch("subprocess.Popen")
@mock.patch("subprocess.run")
def test_python_tk_execution(mock_run, mock_popen):
    """
    Test Case 1: Verifies that a Python Tkinter GUI script can be executed.
    This ensures that the hot-reload endpoint successfully writes the file 
    and forks the subprocess.
    """
    mock_process = mock.Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    payload = {
        "project_id": "test_py_001",
        "language": "python-tk",
        "files": {
            "main.py": "import tkinter as tk\nroot = tk.Tk()\nroot.title('Test')\n"
        }
    }
    
    response = client.post("/execute", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify that subprocess.Popen was called with correct command
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0][0] == "python3"
    assert "main.py" in args[0][1]


@mock.patch("subprocess.Popen")
@mock.patch("subprocess.run")
def test_java_gui_compilation_and_execution(mock_run, mock_popen):
    """
    Test Case 2: Verifies that Java GUI (Swing) multi-step compilation works.
    Ensures 'javac' runs successfully before 'java'.
    """
    mock_process = mock.Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    payload = {
        "project_id": "test_java_001",
        "language": "java-gui",
        "files": {
            "Main.java": "import javax.swing.*;\npublic class Main { public static void main(String[] args) { JFrame f = new JFrame(); f.setSize(400,500); f.setVisible(true); } }"
        }
    }
    
    response = client.post("/execute", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify javac was called
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0][0] == "javac"
    
    # Verify java was called
    mock_popen.assert_called_once()
    assert mock_popen.call_args[0][0][0] == "java"


@mock.patch("subprocess.Popen")
@mock.patch("subprocess.run")
def test_hot_reload_terminates_previous_process(mock_run, mock_popen):
    """
    Test Case 3: Simulates 'Constant Developing' by sending code twice.
    Verifies that the first process is gracefully killed before starting the new one.
    """
    mock_process_1 = mock.Mock()
    mock_process_1.poll.return_value = None # Process 1 is running
    
    mock_process_2 = mock.Mock()
    mock_process_2.poll.return_value = None # Process 2 is running
    
    # Return process 1 on first call, process 2 on second
    mock_popen.side_effect = [mock_process_1, mock_process_2]
    
    payload = {
        "project_id": "test_hotreload",
        "language": "python-tk",
        "files": {"main.py": "import time\ntime.sleep(10)"}
    }
    
    # Execution 1
    client.post("/execute", json=payload)
    
    # Execution 2 (Hot Reload)
    client.post("/execute", json=payload)
    
    # Verify process 1 was terminated
    mock_process_1.terminate.assert_called_once()
    
    # Verify popen was called twice in total
    assert mock_popen.call_count == 2
