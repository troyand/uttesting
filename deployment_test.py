import sys
from pexpect import spawn
from tempfile import mkdtemp, gettempdir
from shutil import rmtree
import types
import urllib2
import re
import unittest
import time

repository_url = 'git://github.com/troyand/universitytimetable.git'

class DeploymentTestCase(unittest.TestCase):
    def __spawn_shell(self):
        def check_cmd(self, cmd):
            self.cmd(cmd)
            cmd_output = self.before
            self.cmd('echo $?')
            cmd_result = int(self.before.splitlines()[1])
            if cmd_result != 0:
                raise AssertionError(
                        '%s\nExpected exit status 0, got %d' % (
                            cmd,
                            cmd_result,
                            )
                        )

        shell = spawn('/bin/sh')
        shell.logfile_read = open('shell_output.log', 'w')
        shell.expect_exact('$')
        shell.prompt = '###> '
        shell.waitprompt = types.MethodType(
                lambda self: self.expect_exact(self.prompt),
                shell
                )
        shell.cmd = types.MethodType(
                lambda self, cmd:
                self.sendline(cmd) and self.waitprompt(),
                shell
                )
        shell.check_cmd = types.MethodType(
                check_cmd,
                shell
                )
        shell.sendline('export PS1="%s"' % shell.prompt)
        shell.waitprompt()
        shell.waitprompt()
        return shell

    def setUp(self):
        self.tempdir = mkdtemp()
        self.shell = self.__spawn_shell()
        self.shell.cmd('pwd')
        self.origdir = self.shell.before.splitlines()[1]
        self.shell.cmd('cd %s' % self.tempdir)

    def __git_clone(self):
        self.shell.check_cmd('git clone %s' % repository_url)
        self.shell.check_cmd('cd universitytimetable')
        self.shell.check_cmd('git checkout %s' % self.branch)
        self.shell.check_cmd('cp %s/local_settings.py ./' % self.origdir)

    def __create_virtualenv(self):
        self.shell.check_cmd('virtualenv --no-site-packages venv')
        self.shell.check_cmd('. venv/bin/activate')

    def __install_requirements(self):
        self.shell.cmd(
                'export PIP_DOWNLOAD_CACHE=%s/pip_download_cache' % gettempdir()
                )
        self.shell.check_cmd('pip install -r requirements.txt')

    def __syncdb(self):
        self.shell.check_cmd('python manage.py syncdb --noinput')
        # temp 'crutch' to make shell.before return what I want
        # instead of '0' output from echo $?
        self.shell.cmd('python manage.py syncdb')
        syncdb_output = self.shell.before
        # south marks the apps that need migrations with ' - ' in line beginning
        for line in filter(lambda s: s.startswith(' - '), syncdb_output.splitlines()):
            self.shell.check_cmd('python manage.py migrate %s' % line[3:])

    def __run_django_tests(self):
        self.shell.check_cmd('python manage.py test')

    def __test_dev_server(self):
        self.shell.sendline('python manage.py runserver')
        self.shell.expect_exact('Quit the server with CONTROL-C.')
        # workaround for fast boxes
        time.sleep(0.5)
        try:
            response = urllib2.urlopen('http://127.0.0.1:8000').read()
            title = re.findall(r'<title>([^<]*)</title>', response)[0]
        except urllib2.HTTPError:
            pass
        self.shell.expect_exact('GET / HTTP/1.1', timeout=2)
        self.shell.sendcontrol('c')
        self.shell.waitprompt()

    def __test_admin(self):
        self.shell.sendline('python manage.py runserver')
        self.shell.expect_exact('Quit the server with CONTROL-C.')
        # workaround for fast boxes
        time.sleep(0.5)
        response = urllib2.urlopen('http://127.0.0.1:8000/admin/').read()
        title = re.findall(r'<title>([^<]*)</title>', response)[0]
        self.shell.expect_exact('GET /admin/ HTTP/1.1', timeout=2)
        self.shell.sendcontrol('c')
        self.shell.waitprompt()


    def test_main(self):
        self.__create_virtualenv()
        self.__git_clone()
        self.__install_requirements()
        self.__syncdb()
        #self.__run_django_tests()
        self.__test_dev_server()
        self.__test_admin()

    def tearDown(self):
        rmtree(self.tempdir)
        self.shell.logfile_read.close()




if __name__ == '__main__':
    if len(sys.argv) == 2:
        DeploymentTestCase.branch = sys.argv[1]
    else:
        DeploymentTestCase.branch = 'master'
    #main(branch)
    suite = unittest.TestLoader().loadTestsFromTestCase(DeploymentTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
