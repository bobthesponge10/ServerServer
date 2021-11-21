from gevent import monkey
monkey.patch_all()
from flask import Flask, url_for, redirect, render_template, request, flash
import flask
from gevent.pywsgi import WSGIServer
import os
from flask import session
import queue
from .HandleGroup import HandleGroup
import time
import json


class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        q = queue.Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]

    @staticmethod
    def format_sse(data: str, event=None) -> str:
        msg = f'data: {data}\n\n'
        if event is not None:
            msg = f'event: {event}\n{msg}'
        return msg


class GUI:
    def __init__(self):
        self.app = None
        self.server = None
        self.ip = ""
        self.port = 80
        self.static_dir = "Webserver/Static"
        self.template_dir = "Webserver/Templates"

        self.manager = None
        self.handle_group = None

        self.usernames = ["admin"]

    def set_manager(self, manager):
        self.manager = manager

    def set_ip(self, ip):
        self.ip = ip

    def set_port(self, port):
        self.port = port

    def get_ip(self):
        return self.ip

    def get_port(self):
        return self.port

    def check_login(self):
        return self.manager.get_user_data().is_user(session.get("username"))

    def get_permissions(self):
        if not self.check_login():
            return 0
        return self.manager.get_user_data().get_user_data(session.get("username"), "permission", default=0)

    def get_handle(self):
        if not self.check_login():
            return
        username = session.get("username")
        h = self.handle_group.get_handle(username, session.get("id"))
        id_ = (h["id"], h["time"])
        session["id"] = id_
        return h

    def create_app(self):
        if not self.manager:
            return False
        self.handle_group = HandleGroup(self.manager.get_handle_list(), self.manager.get_user_data())
        self.handle_group.set_timeout(30)

        app = Flask(__name__,
                    static_folder=os.path.join(os.getcwd(), self.static_dir),
                    template_folder=os.path.join(os.getcwd(), self.template_dir),
                    static_url_path="")
        app.secret_key = b'_5#y2L"F4h8z\n\xec]/'

        @app.route('/console/listen', methods=['GET'])
        def console_listen():
            if self.check_login():
                username = session.get("username")
                h = self.get_handle()
                id_ = (h["id"], h["time"])
                handle = h["handle"]

                def stream():
                    last_update_time = time.time()
                    events = []
                    while True:
                        t = time.time()
                        events += handle.get_events()
                        if len(events) > 0:
                            e = json.dumps(events[0])
                            events.pop(0)

                            yield MessageAnnouncer.format_sse(e, event="control")
                            last_update_time = t
                            self.handle_group.update_time(username, id_)
                        else:
                            if not handle.get_running():
                                return "", 204
                            if t > last_update_time + 10:
                                yield MessageAnnouncer.format_sse("ping", event="ping")
                                self.handle_group.update_time(username, id_)
                                last_update_time = t
                            time.sleep(0.1)

                return flask.Response(stream(), mimetype='text/event-stream')
            return "", 204

        @app.route("/")
        def index():
            if not self.check_login():
                return redirect(url_for("login"))
            return redirect(url_for("home"))

        @app.route("/home")
        def home():
            if not self.check_login():
                return redirect(url_for("login"))
            return render_template("index.html", status=self.manager.get_status())

        @app.route("/controllers")
        def controllers():
            if not self.check_login():
                return redirect(url_for("login"))
            return render_template("controllers.html", controllers=self.manager.get_server_names())

        @app.route("/controllers/<controller>", methods=['POST', 'GET'])
        def controller(controller):
            if not self.check_login():
                return redirect(url_for("login"))
            if not self.manager.is_controller(controller):
                return redirect(url_for("home"))
            servers = self.manager.get_names_of_server_from_type(controller)
            if request.method == "POST":
                name = request.form.get("server_name")
                args = request.form.get("args")
                p = self.get_permissions()
                if p < 4:
                    flash("Higher permission required")
                elif self.manager.create_instance(controller, name, args):
                    flash(f"Created {controller} server: {name}")
                    servers = self.manager.get_names_of_server_from_type(controller)
                else:
                    flash(f"Invalid Arguments")
            return render_template("controller.html", servers=servers, controller=controller)

        @app.route("/controllers/<controller>/<server>", methods=['POST', 'GET'])
        def server(controller, server):
            if not self.check_login():
                return redirect(url_for("login"))
            if not self.manager.is_controller(controller):
                return redirect(url_for("home"))
            if not self.manager.is_server(controller, server):
                return redirect(url_for("home"))
            server_ = self.manager.get_instance_from_type_and_name(controller, server)
            if request.method == 'POST':
                p = self.get_permissions()
                if "start" in request.form.keys():
                    if p < 3:
                        flash("Higher permission required")
                    elif not server_.get_running():
                        server_.start()
                        flash(f"Started {server}")
                elif "stop" in request.form.keys():
                    if p < 3:
                        flash("Higher permission required")
                    elif server_.get_running():
                        server_.stop()
                        flash(f"Stopped {server}")
                        return render_template("server.html", server=server_, running=False)
                elif "delete" in request.form.keys():
                    if p < 4:
                        flash("Higher permission required")
                    elif server_.get_running():
                        flash(f"Can't delete running server")
                    else:
                        if self.manager.remove_instance(controller, server):
                            flash(f"Deleted {server}")
                            return redirect(url_for("controller", controller=controller))
                        else:
                            flash(f"Error deleting {server}")

                return redirect(url_for("server", controller=controller, server=server))
            return render_template("server.html", server=server_, running=server_.get_running())

        @app.route("/servers")
        def servers():
            if not self.check_login():
                return redirect(url_for("login"))
            servers = []
            for i in self.manager.get_server_names():
                instances = self.manager.get_names_of_server_from_type(i)
                for instance in instances:
                    servers.append((i, instance))
            return render_template("servers.html", servers=servers)

        @app.route("/console", methods=['POST', 'GET'])
        def console():
            if not self.check_login():
                return redirect(url_for("login"))
            handle = self.get_handle()["handle"]
            if request.method == "POST":
                handle.put_event({"type": "text", "text": request.form.get("input")})
                return '', 204
            return render_template("console.html", prefix=handle.get_prefix())

        @app.route("/settings")
        def settings():
            if not self.check_login():
                return redirect(url_for("login"))
            return render_template("settings.html", config=self.manager.get_config())

        @app.route("/login", methods=['POST', 'GET'])
        def login():
            if request.method == 'POST':
                username = request.form.get("username")
                password = request.form.get("password")
                if self.manager.get_user_data().login_user(username, password=password):
                    session['username'] = username
                    flash(f"Successfully logged in as {username}")
                    return redirect(url_for("home"))
                else:
                    flash("Invalid Login")
            return render_template("login.html")

        @app.route("/logout")
        def logout():
            if self.check_login():
                self.handle_group.remove_handle(session.get("username"), session.get("id"))
                session.pop("username")
                session.pop("id")
            return redirect(url_for("login"))

        self.app = app
        return True

    def update(self):
        self.handle_group.check_for_timeouts()

    def start(self):
        if not self.app:
            return False
        if not self.server:
            class devnull:
                write = lambda _: None
            self.server = WSGIServer((self.ip, self.port), self.app, log=devnull)

        self.server.start()
        return True

    def get_running(self):
        if self.server:
            return True
        return False

    def stop(self, timeout=0):
        self.server.stop(timeout)
        self.handle_group.close_all()
        self.server = None


