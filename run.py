import sys
import subprocess

def run_tests():
    print("=== Running System Algorithmic Unit Tests ===")
    result = subprocess.run([sys.executable, "-m", "unittest", "tests/test_search.py"])
    return result.returncode == 0

def start_server():
    print("=== Launching JurisSearch Dev Server ===")
    print("Access the dashboard at http://localhost:8000")
    print("Access the API docs at http://localhost:8000/docs")
    try:
        import uvicorn
        # Run server on port 8000
        uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
    except ImportError:
        print("Error: Uvicorn not installed. Run 'pip install -r requirements.txt'")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test-only":
        success = run_tests()
        sys.exit(0 if success else 1)
        
    # Default behavior: run tests first, then start server if tests pass
    tests_passed = run_tests()
    if not tests_passed:
        print("Tests failed! Aborting server start.")
        sys.exit(1)
        
    print("\nTests passed successfully. Starting server...\n")
    start_server()
