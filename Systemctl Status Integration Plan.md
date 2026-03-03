# **Integration Plan: Systemctl Status Checking**

## **1\. Concept**

To ensure accurate service status reporting in the dashboard, we will transition from legacy keyword checking (ps aux | grep ...) to querying the native system manager (systemctl).

The command systemctl is-active \[service\_name\] provides precise states:

* active (Running)  
* inactive (Stopped)  
* failed (Error)  
* activating (Starting)

## **2\. Configuration Updates (JSON)**

We need to inject a command\_status field into the existing service registry (configs/registry\_prod.json or configs/registry\_dev.json).

### **Example Implementation**

{  
    "environment\_name": "Production (Kiero Server)",  
    "services": \[  
        {  
            "id": "kiero\_web\_admin",  
            "name": "Kirana AI \- Web Admin",  
            "type": "systemd",  
            "command\_start": "/usr/bin/systemctl start kiero\_web\_admin.service",  
            "command\_stop": "/usr/bin/systemctl stop kiero\_web\_admin.service",  
            "command\_status": "/usr/bin/systemctl is-active kiero\_web\_admin.service",  
            "log\_file": "/var/log/syslog",  
            "config\_file": "/root/kirana/app/web\_admin\_v2/KieroAI-Admin/.env",  
            "web\_directory": "/root/kirana/app/web\_admin\_v2/KieroAI-Admin"  
        },  
        {  
            "id": "kiai\_analyzer",  
            "name": "Kirana AI \- Analyzer v2",  
            "type": "systemd",  
            "command\_start": "/usr/bin/systemctl start kiai\_analyzer\_v2.service",  
            "command\_stop": "/usr/bin/systemctl stop kiai\_analyzer\_v2.service",  
            "command\_status": "/usr/bin/systemctl is-active kiai\_analyzer\_v2.service",  
            "log\_file": "/var/log/syslog"  
        }  
        // ... Apply to all other services ...  
    \]  
}

## **3\. Python Backend Implementation**

The Flask application needs a function to execute the defined command\_status and translate the output into dashboard-friendly terms. This likely belongs in ai\_helper.py or log\_manager.py depending on your architecture.

### **Status Evaluator Function**

import subprocess

def evaluate\_systemctl\_status(service\_config):  
    """  
    Evaluates the status of a service using its defined systemctl command.  
    """  
    command \= service\_config.get("command\_status")  
      
    if command:  
        try:  
            \# Execute the systemctl is-active command  
            process \= subprocess.Popen(  
                command,   
                shell=True,   
                stdout=subprocess.PIPE,   
                stderr=subprocess.PIPE,  
                text=True  
            )  
            stdout, \_ \= process.communicate()  
            status\_output \= stdout.strip().lower()

            \# Translate Systemd status to Dashboard terms  
            if status\_output \== "active":  
                return "Running"  
            elif status\_output \== "failed":  
                return "Error"  
            elif status\_output \== "activating":  
                return "Starting"  
            else:  
                return "Stopped"  
                  
        except Exception as error:  
            print(f"Status check failed: {error}")  
            return "Unknown"

    \# Fallback to legacy check if command\_status is missing  
    return legacy\_keyword\_check(service\_config)  
      
def legacy\_keyword\_check(service\_config):  
    \# Keep your old ps aux | grep logic here as a safety net  
    return "Stopped"

## **4\. Execution Steps**

1. **Update Configuration:** Edit the relevant JSON file in the configs/ directory to include command\_status.  
2. **Integrate Python Logic:** Locate where the dashboard polls for service statuses (likely an API route in app.py) and inject the evaluate\_systemctl\_status function.  
3. **Restart Web Admin:** Execute systemctl restart kiero\_web\_admin.service to apply changes.