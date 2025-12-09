import json
import csv
from http.server import HTTPServer, BaseHTTPRequestHandler
from .csv_storage import TASKS_CSV

def get_tasks_dict():
    tasks = {}
    with open(TASKS_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            tid = int(row['task_id'])
            row['task_id'] = tid
            row['assignee_user_id'] = int(row['assignee_user_id']) if row['assignee_user_id'] else None
            row['creator_user_id'] = int(row['creator_user_id'])
            tasks[tid] = row
    return tasks

def save_tasks_dict(tasks):
    with open(TASKS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'task_id', 'title', 'description', 'status', 'assignee_user_id',
            'creator_user_id', 'created_at', 'updated_at', 'due_date',
            'completed_at', 'priority', 'tags'
        ])
        writer.writeheader()
        for task in tasks.values():
            writer.writerow(task)

class TaskAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/task/') and len(self.path.split('/')) > 3:
            parts = self.path.split('/')
            if parts[3].isdigit():
                task_id = int(parts[3])
                tasks = get_tasks_dict()
                if task_id in tasks:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(tasks[task_id], indent=2, ensure_ascii=False).encode())
                    return
        self.send_error(404)

    def do_POST(self):
        if self.path.endswith('/status') and '/api/task/' in self.path:
            parts = self.path.split('/')
            if len(parts) >= 5 and parts[3].isdigit():
                task_id = int(parts[3])
                tasks = get_tasks_dict()
                if task_id in tasks:
                    try:
                        content_len = int(self.headers.get('Content-Length', 0))
                        data = json.loads(self.rfile.read(content_len))
                        status = data.get('status', '').lower()
                        if status in ['todo', 'in_progress', 'done']:
                            tasks[task_id]['status'] = status
                            import time
                            tasks[task_id]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                            if status == 'done':
                                tasks[task_id]['completed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                tasks[task_id]['completed_at'] = ''
                            save_tasks_dict(tasks)
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'success': True}, ensure_ascii=False).encode())
                            return
                    except:
                        pass
        self.send_error(400)

def run_api_server(port=8000):
    server = HTTPServer(('localhost', port), TaskAPIHandler)
    import logging
    logging.info(f"HTTP API запущен на http://localhost:{port}")
    server.serve_forever()