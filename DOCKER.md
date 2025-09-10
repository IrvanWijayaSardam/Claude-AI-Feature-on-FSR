# Docker Setup for Frida Script Runner

## Prerequisites
- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)
- Android SDK Platform Tools (for ADB)
- Android device with USB debugging enabled

## Device Setup (IMPORTANT)

Since Docker containers can't directly access USB devices, you need to set up network ADB:

### Option 1: Quick Setup (Recommended)

**Windows:**
```bash
./setup-adb.bat
```

**Linux/Mac:**
```bash
chmod +x setup-adb.sh
./setup-adb.sh
```

### Option 2: Manual Setup

1. **Connect your device via USB** and enable USB debugging

2. **Start ADB server on host:**
   ```bash
   adb start-server
   adb devices  # Verify device is connected
   ```

3. **Enable network ADB on your device:**
   ```bash
   adb tcpip 5555
   ```

4. **Find your device's IP address:**
   ```bash
   adb shell ip route | grep wlan
   ```

5. **Connect via network:**
   ```bash
   adb connect <device-ip>:5555
   ```

6. **Verify connection:**
   ```bash
   adb devices  # Should show device as <ip>:5555
   ```

## Quick Start

1. **Setup ADB network connection** (see above)

2. **Start Docker Desktop** (make sure it's running)

3. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Open your browser and go to: http://localhost:5000

## Commands

- **Build the container:**
  ```bash
  docker-compose build
  ```

- **Run in detached mode:**
  ```bash
  docker-compose up -d
  ```

- **Stop the application:**
  ```bash
  docker-compose down
  ```

- **View logs:**
  ```bash
  docker-compose logs -f
  ```

- **Rebuild and restart:**
  ```bash
  docker-compose up --build --force-recreate
  ```

## Volume Mounts

The following directories are mounted as volumes:
- `./scripts` - Frida scripts directory
- `./tmp` - Temporary files
- `./frida-server` - Frida server binaries

This allows you to modify scripts and files on the host machine and they will be reflected in the container.

## Troubleshooting

### General Issues
- Make sure Docker Desktop is running before executing commands
- If you get permission errors, try running commands as administrator
- To completely rebuild: `docker-compose down && docker-compose up --build`

### ADB/Device Issues
- **No devices found**: Make sure network ADB is properly configured
- **Connection lost**: Device IP might have changed, reconnect with new IP
- **Permission denied**: Ensure USB debugging is authorized on device
- **ADB not found**: Install Android SDK Platform Tools on host system

### Verify ADB Connection
```bash
# Check if ADB server is running on host
adb devices

# Test from inside container (after starting)
docker exec -it <container-name> adb devices
```

### Network ADB Troubleshooting
```bash
# Restart ADB if having issues
adb kill-server
adb start-server

# If device keeps disconnecting
adb connect <device-ip>:5555
```

## iOS Support
iOS devices require different setup:
- Install libimobiledevice tools on host
- iOS devices connect via USB/Lightning (no network setup needed)
- Container will access iOS devices through host's usbmuxd