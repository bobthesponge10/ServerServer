from gevent import monkey
monkey.patch_time()
from flask import Flask, url_for, redirect, render_template, request, flash
from gevent.pywsgi import WSGIServer
import os
from flask import session
from sys import version


class GUI:
    def __init__(self):
        self.app = None
        self.server = None
        self.ip = ""
        self.port = 80
        self.static_dir = "Webserver/Static"
        self.template_dir = "Webserver/Templates"

        self.manager = None

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

    def create_app(self):
        if not self.manager:
            return False
        app = Flask(__name__,
                    static_folder=os.path.join(os.getcwd(), self.static_dir),
                    template_folder=os.path.join(os.getcwd(), self.template_dir),
                    static_url_path="")
        app.secret_key = b'_5#y2L"F4h8z\n\xec]/'

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
                if self.manager.create_instance(controller, name, args):
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
                if "start" in request.form.keys():
                    if not server_.get_running():
                        server_.start()
                        flash(f"Started {server}")
                elif "stop" in request.form.keys():
                    if server_.get_running():
                        server_.stop()
                        flash(f"Stopped {server}")
                        return render_template("server.html", server=server_, running=False)
                elif "delete" in request.form.keys():
                    if server_.get_running():
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

        @app.route("/console")
        def console():
            if not self.check_login():
                return redirect(url_for("login"))
            return redirect(url_for("index"))

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
                session.pop("username")
            return redirect(url_for("login"))

        self.app = app
        return True

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
        self.server = None


