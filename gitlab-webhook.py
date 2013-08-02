#!/usr/bin/env python

import os
import json
import argparse
import BaseHTTPServer
import shlex
import subprocess
import shutil
import logging

logger = logging.getLogger('gitlab-webhook-processor')
logger.setLevel(logging.DEBUG)
logging_handler = logging.StreamHandler()
logging_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                      "%B %d %H:%M:%S"))
logger.addHandler(logging_handler)

repository = ''
branch_dir = ''

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(self):
        logger.info("Received POST request.")
        self.rfile._sock.settimeout(5)
        
        if not self.headers.has_key('Content-Length'):
            return self.error_response()
        
        json_data = self.rfile.read(
            int(self.headers['Content-Length'])).decode('utf-8')

        try:
            data = json.loads(json_data)
        except ValueError:
            logger.error("Unable to load JSON data '%s'" % json_data)
            return self.error_response()

        data_repository = data.get('repository', {}).get('url')
        if data_repository == repository:
            branch_to_update = data.get('ref', '').split('refs/heads/')[-1]
            branch_to_update = branch_to_update.replace('; ', '')
            if branch_to_update == '':
                logger.error("Unable to identify branch to update: '%s'" %
                             data.get('ref', ''))
                return self.error_response()
            elif (branch_to_update.find("/") != -1 or
                  branch_to_update in ['.', '..']):
                # Avoid feature branches, malicious branches and similar.
                logger.debug("Skipping update for branch '%s'." %
                             branch_to_update)
            else:
                self.ok_response()
                branch_deletion = data['after'].replace('0', '') == ''
                branch_addition = data['before'].replace('0', '') == ''
                if branch_addition:
                    self.add_branch(branch_to_update)
                elif branch_deletion:
                    self.remove_branch(branch_to_update)
                else:
                    self.update_branch(branch_to_update)
                return 
        else:
            logger.debug(("Repository '%s' is not our repository '%s'. "
                          "Ignoring.") % (data_repository, repository))

        self.ok_response()
        logger.info("Finished processing POST request.")

    def add_branch(self, branch):
        os.chdir(branch_dir)
        branch_path = os.path.join(branch_dir, branch)
        if os.path.isdir(branch_path):
            return self.update_branch(branch_path)
        run_command("git clone --depth 1 -o origin -b %s %s %s" %
                    (branch, repository, branch))
        os.chmod(branch_path, 0770)
        logger.info("Added directory '%s'" % branch_path)

    def update_branch(self, branch):
        branch_path = os.path.join(branch_dir, branch)
        if not os.path.isdir(branch_path):
            return self.add_branch(branch)
        os.chdir(branch_path)
        run_command("git checkout -f %s" % branch)
        run_command("git clean -fdx")
        run_command("git fetch origin %s" % branch)
        run_command("git reset --hard FETCH_HEAD")
        logger.info("Updated branch '%s'" % branch_path)
        
    def remove_branch(self, branch):
        branch_path = os.path.join(branch_dir, branch)
        if not os.path.isdir(branch_path):
            logger.warn("Directory to remove does not exist: %s" % branch_path)
            return
        try:
            shutil.rmtree(branch_path)
        except (OSError, IOError), e:
            logger.exception("Error removing directory '%s'" % branch_path)
        else:
            logger.info("Removed directory '%s'" % branch_path)
        
    def ok_response(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def error_response(self):
        self.log_error("Bad Request.")
        self.send_response(400)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_command(command):
    logger.debug("Running command: %s" % command)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    process.wait()
    if process.returncode != 0:
        logger.error("Command '%s' exited with return code %s: %s" %
                     (command, process.returncode, process.stdout.read()))
        return ''
    return process.stdout.read()
        
def get_arguments():
    parser = argparse.ArgumentParser(description=(
            'Deploy Gitlab branches in repository to a directory.'))
    parser.add_argument('repository', help=(
            'repository location. Example: git@gitlab.company.com:repo'))
    parser.add_argument('branch_dir', help=(
            'directory to clone branches to. Example: /opt/repo'))
    parser.add_argument('-p', '--port', default=8000, metavar='8000',
                        help='server address (host:port). host is optional.')
    return parser.parse_args()

def main():
    global repository
    global branch_dir
    
    args = get_arguments()
    repository = args.repository
    branch_dir = os.path.abspath(os.path.expanduser(args.branch_dir))
    address = str(args.port)
    
    if address.find(':') == -1:
        host = '0.0.0.0'
        port = int(address)
    else:
        host, port = address.split(":", 1)
        port = int(port)
    server = BaseHTTPServer.HTTPServer((host, port), RequestHandler)

    logger.info("Starting HTTP Server at %s:%s." % (host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    logger.info("Stopping HTTP Server.")
    server.server_close()
    
if __name__ == '__main__':
    main()
