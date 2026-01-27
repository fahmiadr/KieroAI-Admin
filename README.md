# Kawalo Ops Center - User Manual

Welcome to **Kawalo Ops Center**, a premium operations dashboard designed for managing Kawalo services, monitoring system health, and tracking user activity in real-time. This application features a modern **MacOS-style Glassmorphism UI** for a professional and intuitive experience.

## 🚀 How to Start

### Prerequisites
*   Python 3.8+
*   MySQL Database (Running)
*   Node.js (Optional, for frontend/backend services if running locally)

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/kawalo-ops.git
    cd kawalo-ops
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Setup:**
    *   Copy `.env.example` to `.env` (if available) or ensure your `.env` file has the correct DB credentials:
        ```env
        DB_HOST=localhost
        DB_USER=root
        DB_PASS=
        DB_NAME=kawalo_db
        APP_PORT=5006
        ```

### Running the Application
Run the main Flask application:
```bash
python app.py
```
*The server will start at `http://0.0.0.0:5006`*

---

### Accessing the Dashboard
*   **URL:** `http://localhost:5006` (Default)
*   **Login Credentials:**
    *   **Username:** `admin`
    *   **Password:** `password_aman_ops`
    *   *(Credentials are stored in `config_app.json`)*

---

## 🖥️ Dashboard Overview

The **Service Dashboard** is your central command center.

*   **System Stats:** Top widgets show real-time CPU, Memory, and Disk usage.
*   **Service List:** A row-based list of all registered services (e.g., Backend, Frontend, Database).
    *   **Status Indicators:** Green pulse (Running) or Red (Stopped).
    *   **Action Buttons:**
        *   `▶ Start`: Start the service.
        *   `⏹ Stop`: Stop the service.
        *   `Logs`: Open the live terminal log viewer.
        *   `Config`: Open the configuration editor.

---

## 🛠️ Managing Services

### Viewing Logs (Terminal Mode)
Clicking the **Logs** button opens a dedicated "Terminal Window".
*   **Auto-Scroll:** Automatically shows the last 50 lines of logs.
*   **Refresh:** Click the refresh icon in the window header to update log data.
*   **Interface:** Designed to look like a native macOS Terminal for better readability.

### Editing Configuration
Clicking the **Config** button opens the **Configuration Editor**.
*   **Syntax Highlighting:** Edit `.json` or `.env` configurations in a clean editor environment.
*   **Save:** Click "Save" to apply changes immediately to the file system.
*   **Safety:** Always backup your config before making drastic changes.

---

## 👥 User Monitor

Navigate to the **User Monitor** tab via the sidebar.

*   **Real-time Activity:** View which users are currently **Online**, **Away**, or **Offline**.
*   **Duty Status:** Track who is currently "On Duty" or "Off Duty".
*   **Finder-Style List:** A clean, searchable table layout showing:
    *   User Avatar & Name
    *   Email & Role
    *   Last Activity Timestamp
    *   Live Status Badge

---

## ⚙️ System Settings

Navigate to the **Settings** tab to manage the application environment.

### Environment Switcher
You can toggle the entire dashboard between **Development** and **Production** modes.
*   **Development:** Loads configuration from `configs/registry_dev.json`.
*   **Production:** Loads configuration from `configs/registry_prod.json`.
*   **How to Switch:** Click the "Dev" or "Prod" toggle in the Settings card. The UI will update instantly.

### Administrator Info
View the currently logged-in super admin details.

---

## 🎨 UI & Aesthetics
*   **Void Dark Theme:** Deep, rich background colors optimized for long-term usage.
*   **Glassmorphism:** Frosted glass effects on panels and windows.
*   **Interactive:** Hover effects, smooth transitions, and pulsing status indicators.

---

## 🆘 Troubleshooting
*   **Service Not Starting?** Check the Logs viewer for error messages.
*   **Config Not Saving?** Ensure the backend process has write permissions to the `configs/` folder.
*   **User List Empty?** Ensure the database connection in `.env` is correct and the `tkuser` table is populated.
