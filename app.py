import os
import time
import json
import subprocess
import psutil
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
from db_helper import get_active_users
from ai_helper import analyze_log_content

# 1. Load Environment
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_key')

# Store current environment in memory (can be switched via UI)
current_env = os.getenv('APP_ENV', 'development')

# 2. Fungsi Load Config Dinamis
def load_registry(env=None):
    """Load service registry berdasarkan environment (dev/prod)."""
    global current_env
    if env:
        current_env = env
    path = 'configs/registry_prod.json' if current_env == 'production' else 'configs/registry_dev.json'
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e), "services": []}

def load_app_config():
    """Load konfigurasi admin user."""
    with open('config_app.json', 'r') as f:
        return json.load(f)

def get_current_env():
    """Get current environment."""
    global current_env
    return current_env

# 3. Helper System Command
def run_cmd(command):
    """Menjalankan perintah shell."""
    try:
        subprocess.Popen(command, shell=True)
        return True, "Command executed"
    except Exception as e:
        return False, str(e)

def check_service_status(keyword):
    """Cek apakah service dengan keyword tertentu sedang berjalan."""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info.get('cmdline', []) or [])
            if keyword.lower() in cmdline.lower() or keyword.lower() in (proc.info.get('name', '') or '').lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def get_system_stats():
    """Mendapatkan statistik sistem (CPU, Memory, Disk)."""
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory()._asdict(),
        'disk': psutil.disk_usage('/')._asdict()
    }

# --- ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cfg = load_app_config()
        if request.form['username'] == cfg['admin_username'] and \
           request.form['password'] == cfg['admin_password']:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Middleware: Cek Login
@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'logged_in' not in session:
        return redirect(url_for('login'))

@app.route('/')
def dashboard():
    registry = load_registry()
    stats = get_system_stats()
    
    # Cek status service (Manual State Management)
    services = registry.get('services', [])
    for svc in services:
        # Default to 'Stopped' if status not set
        svc['status'] = svc.get('status', 'Stopped')
        
    return render_template('dashboard.html', 
                           data=registry, 
                           stats=stats,
                           env=get_current_env())

@app.route('/switch-env/<env_type>')
def switch_env(env_type):
    """Switch between development and production environment."""
    global current_env
    if env_type in ['development', 'production']:
        current_env = env_type
        flash(f'Switched to {env_type.upper()} environment', 'success')
    else:
        flash('Invalid environment type', 'error')
    return redirect(url_for('dashboard'))

@app.route('/action/<service_id>/<action_type>')
def service_action(service_id, action_type):
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if service:
        cmd = service['command_start'] if action_type == 'start' else service['command_stop']
        success, msg = run_cmd(cmd)
        if success:
            # Update Status in Registry
            new_status = 'Running' if action_type == 'start' else 'Stopped'
            service['status'] = new_status
            
            # Save Registry
            file_path = 'configs/registry_prod.json' if get_current_env() == 'production' else 'configs/registry_dev.json'
            try:
                # Re-read registry to ensure we don't overwrite concurrent changes (basic check)
                with open(file_path, 'r') as f:
                    current_registry = json.load(f)
                
                # Update the specific service in the list
                for s in current_registry.get('services', []):
                    if s['id'] == service_id:
                        s['status'] = new_status
                        break
                
                with open(file_path, 'w') as f:
                    json.dump(current_registry, f, indent=4)
                    
            except Exception as e:
                flash(f"Warning: Command executed but failed to save status: {str(e)}", 'warning')

            flash(f"Service {service_id} {action_type}ed successfully.", 'success')
        else:
            flash(f"Error: {msg}", 'error')
    
    
    # Tunggu sebentar (optional, for UX)
    time.sleep(0.5)
    return redirect(url_for('dashboard'))

@app.route('/logs/<service_id>')
def view_logs(service_id):
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if not service:
        return "Service not found", 404
        
    log_content = "Log file not found."
    
    if os.path.exists(service.get('log_file', '')):
        # Baca 50 baris terakhir
        with open(service['log_file'], 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            log_content = "".join(lines[-50:])
            
            
    # Calculate Web Directory for display
    web_dir = service.get('web_directory', '')
    if not web_dir or not os.path.exists(web_dir):
        config_file = service.get('config_file', '')
        if config_file:
            web_dir = os.path.dirname(config_file)
    
    if not web_dir or not os.path.exists(web_dir):
        import re
        command_start = service.get('command_start', '')
        match = re.search(r'cd\s+([^\s&]+)', command_start)
        if match:
            web_dir = match.group(1)

    return render_template('logs.html', service=service, content=log_content, env=get_current_env(), computed_web_dir=web_dir)

@app.route('/logs/<service_id>/directories')
def get_log_directories(service_id):
    """Get list of directories and files in the log folder."""
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if not service:
        return jsonify({"error": "Service not found"}), 404
    
    log_file = service.get('log_file', '')
    if not log_file:
        return jsonify({"error": "Log file not configured"}), 404
    
    # Get directory from log_file path
    log_dir = os.path.dirname(log_file)
    if not log_dir or not os.path.exists(log_dir):
        return jsonify({"error": f"Log directory not found: {log_dir}"}), 404
    
    items = []
    try:
        for item in os.scandir(log_dir):
            item_info = {
                'name': item.name,
                'path': item.path.replace('\\', '/'),
                'is_dir': item.is_dir(),
                'size': item.stat().st_size if item.is_file() else 0,
                'modified': item.stat().st_mtime
            }
            items.append(item_info)
        
        # Sort: directories first, then files by modified time (newest first)
        items.sort(key=lambda x: (not x['is_dir'], -x['modified']))
        
        return jsonify({
            "directory": log_dir.replace('\\', '/'),
            "items": items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logs/<service_id>/file')
def get_log_file_content(service_id):
    """Get content of a specific log file."""
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    file_path = request.args.get('path', '')
    lines_count = int(request.args.get('lines', 50))
    
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if not service:
        return jsonify({"error": "Service not found"}), 404
    
    # Security: Ensure the file path is within the log directory
    log_file = service.get('log_file', '')
    log_dir = os.path.dirname(log_file)
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    # Normalize paths for comparison
    abs_file_path = os.path.abspath(file_path)
    abs_log_dir = os.path.abspath(log_dir)
    
    if not abs_file_path.startswith(abs_log_dir):
        return jsonify({"error": "Access denied: file outside log directory"}), 403
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            content = "".join(lines[-lines_count:])
        
        return jsonify({
            "file": os.path.basename(file_path),
            "path": file_path.replace('\\', '/'),
            "content": content,
            "total_lines": len(lines)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logs/<service_id>/web-directories')
def get_web_directories(service_id):
    """Get list of directories and files in the web app folder."""
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if not service:
        return jsonify({"error": "Service not found"}), 404
    
    # Priority: 1. web_directory field, 2. config_file parent dir, 3. extract from command_start
    web_dir = service.get('web_directory', '')
    
    # Fallback to config_file parent directory
    if not web_dir or not os.path.exists(web_dir):
        config_file = service.get('config_file', '')
        if config_file:
            web_dir = os.path.dirname(config_file)
    
    # Fallback: extract from command_start (e.g., "cd C:/path && npm start")
    if not web_dir or not os.path.exists(web_dir):
        import re
        command_start = service.get('command_start', '')
        match = re.search(r'cd\s+([^\s&]+)', command_start)
        if match:
            web_dir = match.group(1)
    
    if not web_dir or not os.path.exists(web_dir):
        return jsonify({"error": f"Web directory not found. Please configure 'Web Directory' in Service Manager."}), 404

    
    # Get subdirectory from query param
    subdir = request.args.get('path', '')
    original_web_dir = web_dir # Preserve root for relpath calculation
    
    if subdir:
        target_dir = os.path.join(web_dir, subdir)
        # Security check
        abs_target = os.path.abspath(target_dir)
        abs_web = os.path.abspath(web_dir)
        if not abs_target.startswith(abs_web):
            return jsonify({"error": "Access denied: path outside web directory"}), 403
        web_dir = target_dir
    
    items = []
    try:
        for item in os.scandir(web_dir):
            # Skip hidden files and node_modules
            if item.name.startswith('.') or item.name == 'node_modules':
                continue
                
            # Calculate path relative to the ORIGINAL root (or config file dir)
            # This ensures that when the frontend sends this path back, it's correct relative to root
            base_rel_dir = os.path.dirname(service.get('config_file', '')) if service.get('config_file') else original_web_dir
            if not base_rel_dir: base_rel_dir = original_web_dir

            item_info = {
                'name': item.name,
                'path': os.path.relpath(item.path, base_rel_dir).replace('\\', '/'),
                'full_path': item.path.replace('\\', '/'),
                'is_dir': item.is_dir(),
                'size': item.stat().st_size if item.is_file() else 0,
                'modified': item.stat().st_mtime
            }
            items.append(item_info)
        
        # Sort: directories first, then files alphabetically
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        return jsonify({
            "directory": web_dir.replace('\\', '/'),
            "base_directory": os.path.dirname(service.get('config_file', '')).replace('\\', '/'),
            "items": items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logs/<service_id>/web-file')
def get_web_file_content(service_id):
    """Get content of a specific web file."""
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    file_path = request.args.get('path', '')
    
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if not service:
        return jsonify({"error": "Service not found"}), 404
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    # Security: Get web directory
    config_file = service.get('config_file', '')
    web_dir = os.path.dirname(config_file) if config_file else None
    
    if not web_dir:
        import re
        command_start = service.get('command_start', '')
        match = re.search(r'cd\s+([^\s&]+)', command_start)
        if match:
            web_dir = match.group(1)
    
    if web_dir:
        abs_file_path = os.path.abspath(file_path)
        abs_web_dir = os.path.abspath(web_dir)
        if not abs_file_path.startswith(abs_web_dir):
            return jsonify({"error": "Access denied: file outside web directory"}), 403
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Detect file extension for syntax highlighting
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.jsx': 'jsx', '.ts': 'typescript', '.tsx': 'tsx',
            '.html': 'html', '.css': 'css', '.json': 'json', '.md': 'markdown',
            '.env': 'shell', '.sh': 'bash', '.sql': 'sql', '.yml': 'yaml', '.yaml': 'yaml'
        }
        
        return jsonify({
            "file": os.path.basename(file_path),
            "path": file_path.replace('\\', '/'),
            "content": content,
            "language": lang_map.get(ext, 'text'),
            "total_lines": content.count('\n') + 1
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/analyze_log/<service_id>', methods=['POST'])
def analyze_log(service_id):
    """AI-powered log analysis using Google Gemini."""
    # 1. Security Check
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # 2. Load Service Data
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if not service:
        return jsonify({"error": "Service tidak ditemukan"}), 404

    # 3. Read Log File
    if not os.path.exists(service['log_file']):
        return jsonify({"error": f"File log tidak ditemukan di: {service['log_file']}"}), 404

    try:
        with open(service['log_file'], 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # Get last 60 lines for AI context
            log_snippet = "".join(lines[-60:])
        
        if not log_snippet.strip():
            return jsonify({"result": "<div style='color: #30D158; padding: 16px; text-align: center;'>✅ File log kosong, tidak ada error yang terdeteksi.</div>"})

        # 4. Call AI (pass service category: frontend/backend)
        category = service.get('category', 'backend')
        result = analyze_log_content(log_snippet, service['name'], category)
        
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/config/<service_id>', methods=['GET', 'POST'])
def edit_config(service_id):
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    
    if request.method == 'POST':
        new_content = request.form['content']
        # Backup logic could be added here
        with open(service['config_file'], 'w') as f:
            f.write(new_content)
        flash("Configuration saved!", 'success')
        return redirect(url_for('dashboard'))
        
    content = ""
    if service and os.path.exists(service['config_file']):
        with open(service['config_file'], 'r') as f:
            content = f.read()
            
    return render_template('editor.html', service=service, content=content, env=get_current_env())

@app.route('/users')
def monitor_users():
    raw_users = get_active_users()
    users = []
    
    online_count = 0
    away_count = 0
    
    for u in raw_users:
        # DB Keys: UserName, Email, UserDuty, OnlineStatus, LastActivity, Role
        is_online = u.get('OnlineStatus') == 'Online'
        
        if is_online:
            online_count += 1
        if u.get('OnlineStatus') == 'Away':
            away_count += 1
            
        users.append({
            'username': u.get('UserName', 'Unknown'),
            'full_name': u.get('UserName', 'Unknown'), # Fallback as full_name not in query
            'email': u.get('Email', '-'),
            'role': u.get('Role', 'member'),
            'status': u.get('OnlineStatus', 'Offline').lower(),
            'duty_status': u.get('UserDuty', 'OFF DUTY'),
            'last_activity': u.get('LastActivity'), # Use raw DT object or string
            'is_online': is_online
        })
    
    total_users = len(users)
    return render_template('users.html', 
                         users=users, 
                         online_count=online_count,
                         away_count=away_count,
                         total_users=total_users,
                         env=get_current_env())

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page for environment and app configuration."""
    if request.method == 'POST':
        # Update Global Config from JSON Editor
        config_json_str = request.form.get('config_json', '{}')
        try:
            new_config = json.loads(config_json_str)
            with open('config_app.json', 'w') as f:
                json.dump(new_config, f, indent=4)
            flash('Global configuration updated successfully!', 'success')
        except json.JSONDecodeError as e:
            flash(f'Invalid JSON format: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error updating config: {str(e)}', 'error')
        return redirect(url_for('settings'))

    # Load config and convert to pretty JSON string for editor
    app_config = load_app_config()
    app_config_json = json.dumps(app_config, indent=4)
    
    # Load registry files for editing
    try:
        with open('configs/registry_dev.json', 'r') as f:
            registry_dev_json = f.read()
    except:
        registry_dev_json = '{}'
    
    try:
        with open('configs/registry_prod.json', 'r') as f:
            registry_prod_json = f.read()
    except:
        registry_prod_json = '{}'
    
    return render_template('settings.html', 
                           env=get_current_env(),
                           app_config=app_config,
                           app_config_json=app_config_json,
                           registry_dev_json=registry_dev_json,
                           registry_prod_json=registry_prod_json)


@app.route('/settings/save-registry/<env_type>', methods=['POST'])
def save_registry(env_type):
    """Save registry_dev.json or registry_prod.json."""
    if env_type not in ['dev', 'prod']:
        flash('Invalid environment type', 'error')
        return redirect(url_for('settings'))
    
    file_path = f'configs/registry_{env_type}.json'
    json_content = request.form.get('registry_json', '{}')
    
    try:
        # Validate JSON
        parsed_json = json.loads(json_content)
        
        # Validate structure
        if 'services' not in parsed_json:
            flash('Registry must contain "services" array', 'error')
            return redirect(url_for('settings'))
        
        # Save file
        with open(file_path, 'w') as f:
            json.dump(parsed_json, f, indent=4)
        
        env_name = 'Development' if env_type == 'dev' else 'Production'
        flash(f'{env_name} registry saved successfully!', 'success')
    except json.JSONDecodeError as e:
        flash(f'Invalid JSON format: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error saving registry: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/services', methods=['GET'])
def manage_services():
    """Service Manager page to edit dev/prod service registries."""
    # Load both registries
    try:
        with open('configs/registry_dev.json', 'r') as f:
            dev_registry = json.load(f)
        dev_services = dev_registry.get('services', [])
    except:
        dev_services = []
    
    try:
        with open('configs/registry_prod.json', 'r') as f:
            prod_registry = json.load(f)
        prod_services = prod_registry.get('services', [])
    except:
        prod_services = []
    
    return render_template('services.html',
                           env=get_current_env(),
                           dev_services=dev_services,
                           prod_services=prod_services,
                           dev_services_json=json.dumps(dev_services),
                           prod_services_json=json.dumps(prod_services))

@app.route('/services/save', methods=['POST'])
def save_service():
    """Save a service (add or update) to the registry."""
    env_target = request.form.get('env_target', 'development')
    original_id = request.form.get('original_id', '')
    
    # Build service object from form
    new_service = {
        'id': request.form.get('id'),
        'name': request.form.get('name'),
        'type': request.form.get('type', 'node'),
        'icon': request.form.get('icon', 'bi-window'),
        'group': request.form.get('group', 'Other'),
        'url': request.form.get('url', ''),
        'command_start': request.form.get('command_start'),
        'command_stop': request.form.get('command_stop'),
        'check_keyword': request.form.get('check_keyword', ''),
        'log_file': request.form.get('log_file', ''),
        'config_file': request.form.get('config_file', ''),
        'web_directory': request.form.get('web_directory', '')
    }

    # Determine file path
    file_path = 'configs/registry_prod.json' if env_target == 'production' else 'configs/registry_dev.json'
    
    try:
        with open(file_path, 'r') as f:
            registry = json.load(f)
        
        services = registry.get('services', [])
        
        if original_id:
            # Update existing service
            for i, svc in enumerate(services):
                if svc['id'] == original_id:
                    # Preserve existing status!
                    new_service['status'] = svc.get('status', 'Stopped')
                    services[i] = new_service
                    break
        else:
            # Add new service - Default Status STOPPED
            new_service['status'] = 'Stopped'
            services.append(new_service)
        
        registry['services'] = services
        
        with open(file_path, 'w') as f:
            json.dump(registry, f, indent=4)
        
        flash(f'Service "{new_service["name"]}" saved to {env_target}!', 'success')
    except Exception as e:
        flash(f'Error saving service: {str(e)}', 'error')
    
    return redirect(url_for('manage_services'))

@app.route('/services/delete/<env>/<service_id>')
def delete_service(env, service_id):
    """Delete a service from the registry."""
    file_path = 'configs/registry_prod.json' if env == 'production' else 'configs/registry_dev.json'
    
    try:
        with open(file_path, 'r') as f:
            registry = json.load(f)
        
        services = registry.get('services', [])
        registry['services'] = [s for s in services if s['id'] != service_id]
        
        with open(file_path, 'w') as f:
            json.dump(registry, f, indent=4)
        
        flash(f'Service "{service_id}" deleted from {env}!', 'success')
    except Exception as e:
        flash(f'Error deleting service: {str(e)}', 'error')
    
    return redirect(url_for('manage_services'))

if __name__ == '__main__':
    port = int(os.getenv('APP_PORT', 5006))
    debug_mode = os.getenv('APP_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
