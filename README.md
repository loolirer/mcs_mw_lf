# mcs_mw_lf

**Motion Capture System Middleware** Built with [Lingua Franca](https://www.lf-lang.org/) for high-performance, deterministic distributed capture.

---

## 🛠 Installation & Dependencies
For each capture node, ensure the environment is set up with the following packages before building the federated system.

```bash
# Build tools
sudo apt install cmake

# GStreamer & Libcamera support
sudo apt install gstreamer1.0-libcamera gstreamer1.0-plugins-good \
                 gstreamer1.0-plugins-bad gstreamer1.0-tools

# OpenCV Development headers
sudo apt install libopencv-dev
```

---

## 💡 Critical Tips

### RTI Connection Issues
If you encounter the error:  
`failed to accept the socket: Resource temporarily unavailable`

> **Note:** This usually indicates that at least one **federate failed during startup** or crashed before it could establish a connection with the RTI (Runtime Infrastructure). Check the build logs immediately.

### Checking Logs
When things go wrong, the answers are usually in the log files. Always inspect both the build and the individual federate logs:
```bash
# Inspect logs for specific federates
cat LinguaFrancaRemote/MotionTrackingArena/log/...
```

---

## 🐛 Troubleshooting & Known Bugs

### 1. Build Artifact Corruption
If you encounter weird behavior or stale code issues:
* **Solution:** Wipe the remote directory and start fresh.
  ```bash
  rm -rf LinguaFrancaRemote
  ```

### 2. Camera Device Locked
If the application hangs or fails to open the camera, another process might be holding the lock on `/dev/video0`.
* **Solution:** Force-kill any process using the video device.
  ```bash
  sudo fuser -k /dev/video0
  ```

### 3. PipeWire / WirePlumber Interference
On modern Raspberry Pi OS, background media servers can hijack the camera or audio interfaces.
* **Solution:** Stop the services before running your capture node.
  ```bash
  systemctl --user stop pipewire.socket pipewire-pulse.socket pipewire wireplumber
  ```

### 4. Clock Skew (Build Failures)
If `make` complains about "Clock skew detected" or files being "in the future," your system time is out of sync.
* **Diagnosis:** Run `date` to check the current time.
* **Solution:** Force a synchronization with the time server.
  ```bash
  sudo systemctl restart systemd-timesyncd
  ```

---