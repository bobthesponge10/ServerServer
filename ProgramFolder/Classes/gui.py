from gevent import monkey
monkey.patch_time()
from flask import Flask, url_for, redirect, render_template, request
from gevent.pywsgi import WSGIServer
import os


class GUI:
    def __init__(self, manager):
        self.app = None
        self.server = None
        self.ip = ""
        self.port = 80
        self.static_dir = "Webserver/Static"
        self.template_dir = "Webserver/Templates"

        self.manager = manager
        self.create_app()

    def set_ip(self, ip):
        self.ip = ip

    def set_port(self, port):
        self.port = port

    def get_ip(self):
        return self.ip

    def get_port(self):
        return self.port

    def create_app(self):
        app = Flask(__name__,
                    static_folder=os.path.join(os.getcwd(), self.static_dir),
                    template_folder=os.path.join(os.getcwd(), self.template_dir),
                    static_url_path="")

        @app.route("/")
        def index():
            return redirect(url_for("home"))

        @app.route("/home")
        def home():
            return render_template("index.html")

        @app.route("/controllers")
        def controllers():
            return render_template("controllers.html", controllers=self.manager.get_server_names())

        @app.route("/controllers/<controller>")
        def controller(controller):
            if not self.manager.is_controller(controller):
                return redirect(url_for("home"))
            servers = self.manager.get_names_of_server_from_type(controller)
            return render_template("controller.html", servers=servers, controller=controller)

        @app.route("/controllers/<controller>/<server>", methods=['POST', 'GET'])
        def server(controller, server):
            if not self.manager.is_controller(controller):
                return redirect(url_for("home"))
            if not self.manager.is_server(controller, server):
                return redirect(url_for("home"))
            server = self.manager.get_instance_from_type_and_name(controller, server)
            if request.method == 'POST':
                if "start" in request.form.keys():
                    if not server.get_running():
                        server.start()
                elif "stop" in request.form.keys():
                    if server.get_running():
                        server.stop()
                        return render_template("server.html", server=server, running=False)
                return redirect(url_for("server", controller=controller, server=server))
            return render_template("server.html", server=server, running=server.get_running())

        @app.route("/servers")
        def servers():
            servers = []
            for i in self.manager.get_server_names():
                instances = self.manager.get_names_of_server_from_type(i)
                for instance in instances:
                    servers.append((i, instance))

            return render_template("servers.html", servers=servers)

        @app.route("/console")
        def console():
            return redirect(url_for("index"))

        @app.route("/settings")
        def settings():
            return render_template("settings.html")

        self.app = app

    def start(self):
        if not self.server:
            class devnull:
                write = lambda _: None
            self.server = WSGIServer((self.ip, self.port), self.app, log=devnull)

        self.server.start()

    def stop(self, timeout=0):
        self.server.stop(timeout)


