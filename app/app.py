from flask import Flask, jsonify, request
import os
from datetime import datetime

app = Flask(__name__)

# In-memory data store
tasks = [
    {"id": 1, "title": "Learn Kubernetes", "completed": False},
    {"id": 2, "title": "Deploy to EKS", "completed": False}
]

VERSION = os.getenv('APP_VERSION', '1.0.0')

@app.route('/')
def home():
    """Landing page"""
    return jsonify({
        'message': 'Flask EKS Demo - Simple Task API',
        'version': VERSION,
        'endpoints': {
            'health': '/health',
            'tasks': '/api/tasks',
            'version': '/version'
        },
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/health')
def health():
    """Health check for Kubernetes"""
    return jsonify({
        'status': 'healthy',
        'version': VERSION
    }), 200

@app.route('/ready')
def ready():
    """Readiness check for Kubernetes"""
    return jsonify({'status': 'ready'}), 200

@app.route('/version')
def version():
    """Version info"""
    return jsonify({
        'version': VERSION,
        'environment': os.getenv('ENVIRONMENT', 'dev')
    })

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    """Get all tasks or create new task"""
    if request.method == 'GET':
        return jsonify({
            'tasks': tasks,
            'count': len(tasks)
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        new_task = {
            'id': len(tasks) + 1,
            'title': data.get('title'),
            'completed': False
        }
        tasks.append(new_task)
        return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_task(task_id):
    """Get, update or delete a specific task"""
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if request.method == 'GET':
        return jsonify(task)
    
    elif request.method == 'PUT':
        data = request.get_json()
        task['title'] = data.get('title', task['title'])
        task['completed'] = data.get('completed', task['completed'])
        return jsonify(task)
    
    elif request.method == 'DELETE':
        tasks.remove(task)
        return jsonify({'message': 'Task deleted'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)