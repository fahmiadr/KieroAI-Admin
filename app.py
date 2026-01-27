import os
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
    
    # Cek status service
    services = registry.get('services', [])
    for svc in services:
        svc['status'] = 'Running' if check_service_status(svc.get('check_keyword', '')) else 'Stopped'
        
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
            flash(f"Service {service_id} {action_type}ed successfully.", 'success')
        else:
            flash(f"Error: {msg}", 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/logs/<service_id>')
def view_logs(service_id):
    registry = load_registry()
    service = next((s for s in registry['services'] if s['id'] == service_id), None)
    log_content = "Log file not found."
    
    if service and os.path.exists(service['log_file']):
        # Baca 50 baris terakhir
        with open(service['log_file'], 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            log_content = "".join(lines[-50:])
            
    return render_template('logs.html', service=service, content=log_content, env=get_current_env())

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
    
    return render_template('settings.html', 
                           env=get_current_env(),
                           app_config=app_config,
                           app_config_json=app_config_json)

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
        'group': request.form.get('group', 'Other'),
        'url': request.form.get('url', ''),
        'command_start': request.form.get('command_start'),
        'command_stop': request.form.get('command_stop'),
        'check_keyword': request.form.get('check_keyword', ''),
        'log_file': request.form.get('log_file', ''),
        'config_file': request.form.get('config_file', '')
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
                    services[i] = new_service
                    break
        else:
            # Add new service
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
