# Claude Instructions for Frida Script Runner

## Project Context
This is a Frida Script Runner project that generates dynamic instrumentation scripts for reverse engineering Android applications.

## MCP Tools Available
- **JadxMCP**: For analyzing Java/Android code from JADX projects
- **GhidraMCP**: For analyzing native code from Ghidra projects

## Script Generation Workflow

When generating Frida scripts:

1. **Use MCP Tools First**: Always analyze the currently opened Ghidra and JADX projects using the available MCP tools to get:
   - Function addresses and signatures
   - Class names and method names
   - String references and constants
   - Memory layouts and data structures

2. **Generate Complete Scripts**: Create working Frida JavaScript code that includes:
   - Proper `Java.perform()` wrapper
   - Hook implementations based on MCP analysis findings
   - Console logging for debugging
   - Error handling

3. **File Output Requirements**:
   - **MUST** save generated scripts to: `temp_generated.js`
   - Use the Write tool with exact filename: `temp_generated.js`
   - Do NOT use other filenames like `sesame-hook.js`, `scripts/hook.js`, etc.
   - Always overwrite if file exists

## Example Template

```javascript
Java.perform(function() {
    console.log("[+] Frida script started");

    // Your hook code here based on MCP analysis
    // Use specific addresses, function names from Ghidra/JADX analysis

    console.log("[+] Script setup completed");
});
```

## Important Rules

- ✅ **DO**: Use MCP tools to analyze open projects
- ✅ **DO**: Create `temp_generated.js` with Write tool
- ✅ **DO**: Include specific findings from analysis (addresses, function names)
- ✅ **DO**: Generate working JavaScript code

- ❌ **DON'T**: Create files with different names
- ❌ **DON'T**: Just reference existing scripts without creating new ones
- ❌ **DON'T**: Provide only analysis without generating code

The bridge system expects to find the generated script at `temp_generated.js` and will serve its contents to the UI.