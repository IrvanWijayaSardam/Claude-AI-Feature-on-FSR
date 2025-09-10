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
import glob

# Global variables
CLAUDE_EXECUTABLE = None
MCP_CONFIG = None

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

def find_mcp_servers():
    """Find and configure MCP servers for Claude CLI"""
    global MCP_CONFIG
    
    # Check environment variable for MCP config
    env_mcp_config = os.environ.get('CLAUDE_MCP_CONFIG')
    if env_mcp_config:
        print(f"[BRIDGE] Using MCP config from environment: {env_mcp_config}")
        MCP_CONFIG = env_mcp_config
        return MCP_CONFIG
    
    # Specific MCP server configurations (based on user's setup)
    mcp_servers = {}
    
    # Check for Ghidra MCP server
    ghidra_bridge_path = "D:/Irvan/Work/MCP/GhidraMCPFrida/bridge_mcp_ghidra.py"
    if os.path.exists(ghidra_bridge_path):
        print(f"[BRIDGE] Found Ghidra MCP server at: {ghidra_bridge_path}")
        mcp_servers["ghidra"] = {
            "command": "python",
            "args": [
                ghidra_bridge_path,
                "--ghidra-server",
                "http://127.0.0.1:8080/"
            ]
        }
    
    # Check for JADX MCP server
    jadx_server_path = "D:/Irvan/Work/MCP/JadxMCPServer/jadx-mcp-server-v3.3.0/jadx-mcp-server/jadx_mcp_server.py"
    uv_path = "C:/Users/Evan/.local/bin/uv.exe"
    
    if os.path.exists(jadx_server_path) and os.path.exists(uv_path):
        print(f"[BRIDGE] Found JADX MCP server at: {jadx_server_path}")
        mcp_servers["jadx-mcp-server"] = {
            "command": uv_path,
            "args": [
                "--directory",
                "D:/Irvan/Work/MCP/JadxMCPServer/jadx-mcp-server-v3.3.0/jadx-mcp-server/",
                "run",
                "jadx_mcp_server.py",
                "--jadx-port",
                "8650"
            ]
        }
    
    # If we found any MCP servers, create config
    if mcp_servers:
        mcp_config = {"mcpServers": mcp_servers}
        
        # Save to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mcp_config, f, indent=2)
            MCP_CONFIG = f.name
            print(f"[BRIDGE] Created MCP config file: {MCP_CONFIG}")
            print(f"[BRIDGE] Found {len(mcp_servers)} MCP servers: {list(mcp_servers.keys())}")
            return MCP_CONFIG
    
    # Check if user has Claude MCP config directory
    claude_config_dir = None
    if os.name == 'nt':  # Windows
        claude_config_dir = os.path.expanduser("~\\AppData\\Roaming\\Claude\\mcp_servers")
    else:  # Unix-like
        claude_config_dir = os.path.expanduser("~/.config/claude/mcp_servers")
    
    if claude_config_dir and os.path.exists(claude_config_dir):
        # Look for existing MCP server configs
        config_files = glob.glob(os.path.join(claude_config_dir, "*.json"))
        if config_files:
            MCP_CONFIG = config_files[0]  # Use first found config
            print(f"[BRIDGE] Using existing Claude MCP config: {MCP_CONFIG}")
            return MCP_CONFIG
    
    print("[BRIDGE] No MCP servers found")
    return None

class ClaudeBridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_health_check()
        elif self.path == '/' or self.path == '/test':
            self.send_test_page()
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
    
    def send_test_page(self):
        """Send HTML test page"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Bridge - Frida Script Tester</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: #2d3748;
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.8;
        }
        
        .content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0;
            min-height: 600px;
        }
        
        .input-section {
            padding: 30px;
            border-right: 1px solid #e2e8f0;
        }
        
        .output-section {
            padding: 30px;
            background: #f7fafc;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #2d3748;
        }
        
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            transition: border-color 0.3s;
            resize: vertical;
        }
        
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        #promptInput {
            min-height: 150px;
        }
        
        #output {
            min-height: 400px;
            background: #1a202c;
            color: #e2e8f0;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 13px;
            line-height: 1.5;
            border: none;
            resize: none;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .status {
            margin: 15px 0;
            padding: 10px;
            border-radius: 4px;
            font-weight: 500;
        }
        
        .status.success {
            background: #c6f6d5;
            color: #22543d;
            border: 1px solid #9ae6b4;
        }
        
        .status.error {
            background: #fed7d7;
            color: #742a2a;
            border: 1px solid #fc8181;
        }
        
        .status.loading {
            background: #bee3f8;
            color: #2a4365;
            border: 1px solid #90cdf4;
        }
        
        .example-prompts {
            margin-top: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
        }
        
        .example-prompts h3 {
            color: #2d3748;
            margin-bottom: 10px;
        }
        
        .example-prompt {
            background: white;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            color: #4a5568;
            border: 1px solid #e2e8f0;
            transition: background 0.2s;
        }
        
        .example-prompt:hover {
            background: #edf2f7;
        }
        
        @media (max-width: 768px) {
            .content {
                grid-template-columns: 1fr;
            }
            
            .input-section {
                border-right: none;
                border-bottom: 1px solid #e2e8f0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Claude Bridge - Frida Script Tester</h1>
            <p>Test your Frida script generation prompts with Claude AI</p>
        </div>
        
        <div class="content">
            <div class="input-section">
                <div class="form-group">
                    <label for="promptInput">Enter your prompt:</label>
                    <textarea id="promptInput" placeholder="Example: Hook the login function and log all parameters..."></textarea>
                </div>
                
                <button id="generateBtn" class="btn" onclick="generateScript()">
                    Generate Frida Script
                </button>
                
                <div id="status"></div>
                
                <div class="example-prompts">
                    <h3>Example Prompts:</h3>
                    <div class="example-prompt" onclick="setPrompt(this)">
                        Hook the main function and log all parameters
                    </div>
                    <div class="example-prompt" onclick="setPrompt(this)">
                        Intercept SSL pinning bypass for Android app
                    </div>
                    <div class="example-prompt" onclick="setPrompt(this)">
                        Monitor file operations and log file paths
                    </div>
                    <div class="example-prompt" onclick="setPrompt(this)">
                        Hook Java method com.example.App.authenticate and modify return value
                    </div>
                </div>
            </div>
            
            <div class="output-section">
                <div class="form-group">
                    <label for="output">Generated Frida Script:</label>
                    <textarea id="output" readonly placeholder="Click 'Generate Frida Script' to see the result here..."></textarea>
                </div>
            </div>
        </div>
    </div>

    <script>
        function setPrompt(element) {
            document.getElementById('promptInput').value = element.textContent.trim();
        }
        
        function showStatus(message, type = 'loading') {
            const status = document.getElementById('status');
            status.innerHTML = message;
            status.className = `status ${type}`;
        }
        
        async function generateScript() {
            const promptInput = document.getElementById('promptInput');
            const outputArea = document.getElementById('output');
            const generateBtn = document.getElementById('generateBtn');
            
            const prompt = promptInput.value.trim();
            
            if (!prompt) {
                showStatus('Please enter a prompt', 'error');
                return;
            }
            
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';
            showStatus('🤖 Generating Frida script with Claude AI...', 'loading');
            outputArea.value = 'Generating script, please wait...';
            
            try {
                const response = await fetch('/generate-script', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ prompt: prompt })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    outputArea.value = data.script;
                    showStatus('✅ Script generated successfully!', 'success');
                } else {
                    outputArea.value = `Error: ${data.error}`;
                    showStatus(`❌ Error: ${data.error}`, 'error');
                }
            } catch (error) {
                outputArea.value = `Network Error: ${error.message}`;
                showStatus(`❌ Network Error: ${error.message}`, 'error');
            } finally {
                generateBtn.disabled = false;
                generateBtn.textContent = 'Generate Frida Script';
            }
        }
        
        // Allow Enter key to generate (Ctrl+Enter or Cmd+Enter)
        document.getElementById('promptInput').addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                generateScript();
            }
        });
        
        // Check health on page load
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'healthy') {
                    showStatus(`✅ Claude Bridge is healthy (${data.claude_version})`, 'success');
                } else {
                    showStatus(`❌ Claude Bridge is unhealthy: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                showStatus(`❌ Cannot connect to bridge: ${error.message}`, 'error');
            });
    </script>
</body>
</html>"""

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(html_content.encode('utf-8'))
    
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
            
            # Use the prompt directly without additional formatting
            formatted_prompt = prompt
            
            try:
                global CLAUDE_EXECUTABLE
                if not CLAUDE_EXECUTABLE:
                    response = {
                        'success': False,
                        'error': 'Claude executable not found'
                    }
                    self.send_json_response(500, response)
                    return
                    
                # Try Claude CLI with MCP first, fallback to plain Claude
                result = None
                
                # Method 1: Try with MCP if available
                global MCP_CONFIG
                if MCP_CONFIG:
                    print(f"[BRIDGE] Trying Claude CLI with MCP config: {MCP_CONFIG}")
                    try:
                        cmd_args = [
                            CLAUDE_EXECUTABLE, 
                            '--mcp-config', MCP_CONFIG, 
                            '--print',
                            '--dangerously-skip-permissions'
                        ]
                        result = subprocess.run(
                            cmd_args,
                            input=formatted_prompt,
                            capture_output=True,
                            text=True,
                            timeout=120,  # Longer timeout for MCP
                            cwd=os.getcwd()
                        )
                        
                        if result.returncode == 0 and result.stdout.strip():
                            print(f"[BRIDGE] MCP method succeeded!")
                        else:
                            print(f"[BRIDGE] MCP method failed: {result.stderr}")
                            result = None
                    except Exception as e:
                        print(f"[BRIDGE] MCP method exception: {e}")
                        result = None
                
                # Method 2: Fallback to plain Claude CLI
                if not result:
                    print(f"[BRIDGE] Falling back to plain Claude CLI...")
                    try:
                        result = subprocess.run([
                            CLAUDE_EXECUTABLE, '--print'
                        ], 
                        input=formatted_prompt,
                        capture_output=True, 
                        text=True, 
                        timeout=60,
                        cwd=os.getcwd())
                        
                        if result.returncode == 0:
                            print(f"[BRIDGE] Plain Claude CLI succeeded!")
                        else:
                            print(f"[BRIDGE] Plain Claude CLI failed: {result.stderr}")
                    except Exception as e:
                        print(f"[BRIDGE] Plain Claude CLI exception: {e}")
                        result = None
                
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
    
    # Find and configure MCP servers
    mcp_config_path = find_mcp_servers()
    if mcp_config_path:
        print(f"✅ MCP servers configured")
    else:
        print(f"⚠️  No MCP servers found - using plain Claude CLI")
    
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