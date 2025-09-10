#!/usr/bin/env python3
"""
Claude CLI HTTP Bridge for Docker (Minimal Dependencies)
Runs on host to serve Claude CLI requests from Docker container
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import tempfile
import os
import sys
import urllib.parse
import shutil

# Global variable to store Claude executable path
CLAUDE_EXECUTABLE = None

def find_claude_executable():
    """Find Claude CLI executable on Windows/Linux/Mac"""
    global CLAUDE_EXECUTABLE
    
    # Try common command names with actual execution test
    for cmd in ['claude', 'claude.exe']:
        full_path = shutil.which(cmd)
        if full_path:
            # Test if it actually works
            try:
                result = subprocess.run([full_path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    CLAUDE_EXECUTABLE = full_path
                    return full_path
            except:
                continue
    
    # Try common installation paths on Windows
    if sys.platform.startswith('win'):
        username = os.environ.get('USERNAME', 'User')
        windows_paths = [
            f"C:\\Users\\{username}\\AppData\\Local\\AnthropicClaude\\claude.exe",
            f"C:\\Users\\{username}\\AppData\\Local\\Programs\\claude\\claude.exe",
            "C:\\Program Files\\Claude\\claude.exe",
            "C:\\Program Files (x86)\\Claude\\claude.exe",
            f"C:\\Users\\{username}\\AppData\\Local\\claude\\claude.exe",
        ]
        
        for path in windows_paths:
            if os.path.exists(path):
                # Test if it actually works
                try:
                    result = subprocess.run([path, '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        CLAUDE_EXECUTABLE = path
                        return path
                except:
                    continue
    
    # Try common paths on Unix-like systems
    else:
        unix_paths = [
            "/usr/local/bin/claude",
            "/usr/bin/claude",
            os.path.expanduser("~/.local/bin/claude"),
            "/opt/claude/claude",
        ]
        
        for path in unix_paths:
            if os.path.exists(path):
                # Test if it actually works
                try:
                    result = subprocess.run([path, '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        CLAUDE_EXECUTABLE = path
                        return path
                except:
                    continue
    
    return None

class ClaudeBridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_health_check()
        else:
            self.send_error(404, "Not found")
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/generate-script':
            self.handle_generate_script()
        else:
            self.send_error(404, "Not found")
    
    def send_health_check(self):
        """Health check endpoint"""
        global CLAUDE_EXECUTABLE
        try:
            if not CLAUDE_EXECUTABLE:
                response = {
                    'status': 'unhealthy', 
                    'error': 'Claude executable not found'
                }
                self.send_json_response(503, response)
                return
                
            # Check if Claude CLI is available
            result = subprocess.run([CLAUDE_EXECUTABLE, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                response = {
                    'status': 'healthy', 
                    'claude_version': result.stdout.strip(),
                    'claude_path': CLAUDE_EXECUTABLE
                }
                self.send_json_response(200, response)
            else:
                response = {
                    'status': 'unhealthy', 
                    'error': 'Claude CLI not responding'
                }
                self.send_json_response(503, response)
        except Exception as e:
            response = {
                'status': 'unhealthy', 
                'error': str(e)
            }
            self.send_json_response(503, response)
    
    def handle_generate_script(self):
        """Generate Frida script using Claude CLI"""
        try:
            print("[BRIDGE] Received generate-script request")
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            print(f"[BRIDGE] Request content length: {content_length}")
            
            if content_length == 0:
                self.send_json_response(400, {'error': 'No data provided'})
                return
                
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if 'prompt' not in data:
                self.send_json_response(400, {'error': 'No prompt provided'})
                return
            
            prompt = data['prompt']
            print(f"[BRIDGE] Prompt length: {len(prompt)} characters")
            
            # Format the prompt for Claude Code CLI
            formatted_prompt = f"""You are an expert Frida script developer. Generate a complete, working Frida script based on this request:

{prompt}

Requirements:
- Return ONLY JavaScript code for Frida
- Include Java.perform() wrapper if hooking Java code
- Add proper error handling with try-catch blocks
- Include console.log statements for debugging
- Make it production-ready and executable immediately

Generate the script now (JavaScript code only):"""
            
            try:
                global CLAUDE_EXECUTABLE
                if not CLAUDE_EXECUTABLE:
                    response = {
                        'success': False,
                        'error': 'Claude executable not found'
                    }
                    self.send_json_response(500, response)
                    return
                    
                # Try different approaches to call Claude CLI
                result = None
                
                # Method 1: Direct prompt via command line
                print(f"[BRIDGE] Trying direct prompt method...")
                try:
                    result = subprocess.run([
                        CLAUDE_EXECUTABLE, 
                        '--prompt', formatted_prompt
                    ], 
                    capture_output=True, 
                    text=True, 
                    timeout=60,
                    cwd=os.getcwd())
                    
                    if result.returncode == 0 and result.stdout.strip():
                        print(f"[BRIDGE] Direct prompt method succeeded!")
                    else:
                        print(f"[BRIDGE] Direct prompt failed: {result.stderr}")
                        result = None
                except Exception as e:
                    print(f"[BRIDGE] Direct prompt exception: {e}")
                    result = None
                
                # Method 2: Using stdin
                if not result:
                    print(f"[BRIDGE] Trying stdin method...")
                    try:
                        result = subprocess.run([
                            CLAUDE_EXECUTABLE
                        ], 
                        input=formatted_prompt,
                        capture_output=True, 
                        text=True, 
                        timeout=60,
                        cwd=os.getcwd())
                        
                        if result.returncode == 0 and result.stdout.strip():
                            print(f"[BRIDGE] Stdin method succeeded!")
                        else:
                            print(f"[BRIDGE] Stdin failed: {result.stderr}")
                            result = None
                    except Exception as e:
                        print(f"[BRIDGE] Stdin exception: {e}")
                        result = None
                
                # Method 3: Interactive approach with echo
                if not result:
                    print(f"[BRIDGE] Trying echo pipe method...")
                    try:
                        if os.name == 'nt':  # Windows
                            cmd = f'echo {formatted_prompt} | {CLAUDE_EXECUTABLE}'
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                        else:  # Unix-like
                            cmd = f'echo "{formatted_prompt}" | {CLAUDE_EXECUTABLE}'
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0 and result.stdout.strip():
                            print(f"[BRIDGE] Echo pipe method succeeded!")
                        else:
                            print(f"[BRIDGE] Echo pipe failed: {result.stderr}")
                            result = None
                    except Exception as e:
                        print(f"[BRIDGE] Echo pipe exception: {e}")
                        result = None
                
                # If all methods failed, return error
                if not result:
                    response = {
                        'success': False,
                        'error': 'All Claude CLI methods failed'
                    }
                    self.send_json_response(500, response)
                    return
                
                # Process successful result
                print(f"[BRIDGE] Claude CLI return code: {result.returncode}")
                print(f"[BRIDGE] Claude CLI stdout length: {len(result.stdout) if result.stdout else 0}")
                print(f"[BRIDGE] Claude CLI stderr: {result.stderr[:200] if result.stderr else 'None'}")
                
                if result.returncode == 0:
                    generated_script = result.stdout.strip()
                    
                    # Log the AI response for debugging
                    print(f"[BRIDGE] ==================== AI RESPONSE ====================")
                    print(f"[BRIDGE] Raw Claude Output:")
                    print(result.stdout)
                    print(f"[BRIDGE] =====================================================")
                    print(f"[BRIDGE] Cleaned script length: {len(generated_script)}")
                    
                    response = {
                        'success': True,
                        'script': generated_script
                    }
                    print(f"[BRIDGE] Sending successful response, script length: {len(generated_script)}")
                    self.send_json_response(200, response)
                else:
                    error_msg = f'Claude CLI failed with code {result.returncode}: {result.stderr}'
                    print(f"[BRIDGE] Claude CLI failed: {error_msg}")
                    response = {
                        'success': False,
                        'error': error_msg
                    }
                    self.send_json_response(500, response)
                        
            except subprocess.TimeoutExpired:
                response = {
                    'success': False,
                    'error': 'Claude CLI timed out'
                }
                self.send_json_response(500, response)
            except Exception as e:
                response = {
                    'success': False,
                    'error': f'Claude CLI execution failed: {str(e)}'
                }
                self.send_json_response(500, response)
            
        except Exception as e:
            response = {
                'success': False,
                'error': f'Bridge error: {str(e)}'
            }
            self.send_json_response(500, response)
    
    def send_json_response(self, status_code, data):
        """Send JSON response"""
        response_data = json.dumps(data).encode('utf-8')
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        self.wfile.write(response_data)
    
    def log_message(self, format, *args):
        """Override to reduce logging noise but show errors"""
        if 'POST' in format or 'error' in format.lower():
            print(f"[BRIDGE] {format % args}")
        pass

if __name__ == '__main__':
    print("🚀 Starting Claude CLI HTTP Bridge (No Dependencies)...")
    print("📡 Bridge will be available at: http://localhost:8090")
    print("🔗 Docker containers can access at: http://host.docker.internal:8090")
    print("💡 Use /health to check status, /generate-script to generate Frida scripts")
    print("⚠️  Make sure Claude CLI is installed and authenticated on this host")
    print()
    
    # Find Claude CLI executable
    claude_cmd = find_claude_executable()
    if not claude_cmd:
        print("❌ Claude CLI not found or not working")
        print("   Locations checked:")
        
        # Show what was found by shutil.which
        for cmd in ['claude', 'claude.exe']:
            which_result = shutil.which(cmd)
            if which_result:
                print(f"   - Found '{cmd}' at: {which_result} (but not working)")
            else:
                print(f"   - '{cmd}' not found in PATH")
        
        # Show Windows paths checked
        if sys.platform.startswith('win'):
            username = os.environ.get('USERNAME', 'User')
            windows_paths = [
                f"C:\\Users\\{username}\\AppData\\Local\\AnthropicClaude\\claude.exe",
                f"C:\\Users\\{username}\\AppData\\Local\\Programs\\claude\\claude.exe",
                "C:\\Program Files\\Claude\\claude.exe", 
                "C:\\Program Files (x86)\\Claude\\claude.exe",
                f"C:\\Users\\{username}\\AppData\\Local\\claude\\claude.exe",
            ]
            
            for path in windows_paths:
                if os.path.exists(path):
                    print(f"   - Found at: {path} (but not working)")
                else:
                    print(f"   - Not found: {path}")
        
        print()
        print("   Solutions:")
        print("   1. Install Claude Code from: https://claude.ai/code")
        print("   2. Ensure Claude CLI is properly installed and authenticated")
        print("   3. Try running 'claude --version' manually to test")
        sys.exit(1)
    
    print(f"✅ Claude CLI found at: {claude_cmd}")
    
    # Get version info
    try:
        result = subprocess.run([claude_cmd, '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Version: {result.stdout.strip()}")
        else:
            print(f"⚠️  Warning: Version check failed: {result.stderr}")
    except Exception as e:
        print(f"⚠️  Warning: Could not get version: {e}")
    
    # Check available options
    print("🔍 Checking Claude CLI options...")
    try:
        help_result = subprocess.run([claude_cmd, '--help'], capture_output=True, text=True, timeout=5)
        if help_result.returncode == 0:
            help_text = help_result.stdout
            print("📋 Available options discovered:")
            if '--file' in help_text:
                print("   ✅ --file supported")
            if '--ide' in help_text:
                print("   ✅ --ide supported") 
            if '--prompt' in help_text:
                print("   ✅ --prompt supported")
            if '--input' in help_text:
                print("   ✅ --input supported")
        else:
            print("⚠️  Could not get help info")
    except Exception as e:
        print(f"⚠️  Could not check options: {e}")
    
    # Start HTTP server
    server_address = ('0.0.0.0', 8090)
    httpd = HTTPServer(server_address, ClaudeBridgeHandler)
    
    print(f"🎯 Bridge server started on {server_address[0]}:{server_address[1]}")
    print("📝 Logs will be minimal. Press Ctrl+C to stop.")
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down Claude CLI bridge...")
        httpd.server_close()