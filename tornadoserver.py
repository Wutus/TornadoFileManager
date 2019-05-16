import logging
import os
import sys
import time
import tornado.httpserver
import tornado.ioloop
import tornado.log
import tornado.web
import json
import shutil

base_path = '/home/samba/wieclawk/linux/TornadoFileManager/fun'

class User:
    def __init__(self, name, password):
        self.name = name
        self.password = password

    def __eq__(self, other):
        return self.name == other.name and self.password == other.password

class Fileinfo:
    def __init__(self, path, data, size):
        self.path = os.path.normpath(path)
        self.name = os.path.basename(path) + ('/' if os.path.isdir(os.path.normpath(os.path.join(base_path + path))) else '')
        self.data = data
        self.size = size

class BrowseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get(self, path):
        path = os.path.normpath(path)
        path = path.replace('\\','/')
        path_to_list = os.path.normpath(os.path.join(base_path, path)).replace('\\','/')
        if not path_to_list.startswith(base_path):
            raise tornado.web.HTTPError(403)
        if not os.path.isdir(path_to_list):
            raise tornado.web.HTTPError(404)
        files = []
        for f in (['..'] if path != '.' else []) + sorted([i for i in os.listdir(path_to_list)]):
            absf = os.path.join(path_to_list, f)
            lstat_result = os.lstat(absf)
            data = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(lstat_result.st_mtime))
            files.append(Fileinfo(os.path.join(path,f), data, lstat_result.st_size))
        if not path.endswith('/'):
            path = path + '/'
        self.render('browse.thtml', files=files, path=path)

def load_users():
    with open("users.json") as usersfile:
        users_array = json.load(usersfile)
        users = []
        for u in users_array:
            users.append(User(u['name'],u['password']))
        return users

class LoginHandler(tornado.web.RequestHandler):

    users = load_users()

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get(self, path):
        incorrect=self.get_argument("incorrect", None, False)
        self.render("login.thtml", incorrect=incorrect)

    def post(self, path):
        username = self.get_argument("username", None)
        password = self.get_argument("password", None)
        user = User(username, password)
        if user not in LoginHandler.users:
            self.redirect("/login?incorrect=True")
        else:
            self.set_secure_cookie("user", user.name)
            self.redirect("/browse")

class LogoutHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie('user')
    
    def get(self, path):
        self.clear_cookie('user')
        self.redirect('/browse/')

class UploadHandler(tornado.web.RequestHandler):
    
    def get_current_user(self):
        return self.get_secure_cookie("user")
    
    @tornado.web.authenticated
    def get(self, path):
        path = os.path.normpath(path)
        if not path.endswith('/'):
            path = path + '/'
        self.render("upload.thtml", path=path)

    @tornado.web.authenticated
    def post(self, path):
        path = os.path.normpath(path)
        file = self.request.files['uploadedFile'][0]
        if not path.endswith('/'):
            path = path + '/'
        real_path = os.path.join(base_path, path)
        uploaded_file_path = os.path.join(real_path + file['filename'])
        with open(uploaded_file_path, 'wb') as output_file:
            output_file.write(file['body'])
        self.redirect('/browse/' + path)

class RemoveHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user")

    @tornado.web.authenticated
    def get(self, path):
        real_path = os.path.normpath(os.path.join(base_path,path))
        if os.path.exists(real_path):
            if os.path.isdir(real_path):
                shutil.rmtree(real_path)
            else:
                os.remove(real_path)
        self.redirect('/browse/')


class BasicHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get(self, path):
        self.redirect('/browse/')

class FileManagerApp():
    def __init__(self):
        with open("settings.json", "r+") as settingsfile:
            settings = json.load(settingsfile)
        self.listen_address = '0.0.0.0'
        self.listen_port = 8000
        tornado.log.enable_pretty_logging()
        self.application = tornado.web.Application(
            [
                ('/()', BasicHandler),
                ('/browse()', BasicHandler),
                ('/browse/(.*/)', BrowseHandler),
                ('/browse/()', BrowseHandler),
                ('/login()', LoginHandler),
                ('/logout()', LogoutHandler),
                ('/upload/()', UploadHandler),
                ('/upload/(.*/)', UploadHandler),
                ('/remove(.*)', RemoveHandler),
                ('/browse/(.*)', tornado.web.StaticFileHandler, {'path': base_path, 'default_filename': ''}),
            ],
            **settings
        )
        self.http_server = tornado.httpserver.HTTPServer(self.application)

    def Run(self):
        self.http_server.listen(self.listen_port, self.listen_address)
        logging.info('Listening on %s:%s' % (self.listen_address or '[::]' if ':' not in self.listen_address else '[%s]' % self.listen_address, self.listen_port))
        tornado.ioloop.IOLoop.instance().start()


def main():
    global base_path 
    if(len(sys.argv) > 1):
        base_path = sys.argv[1]
    if(len(sys.argv) > 2):
        print("Usage: tornadoserver.py [base_path]")
        exit(1)
    base_path = os.path.abspath(base_path)
    if not os.path.exists(base_path):
        print("Base path %s does not exists" % base_path)
        exit(1)
    app = FileManagerApp()
    app.Run()

if __name__ == "__main__":
    main()