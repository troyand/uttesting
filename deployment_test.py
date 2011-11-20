import sys
from pexpect import spawn
from tempfile import mkdtemp
from shutil import rmtree
import types
import urllib2
import re
import unittest

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


    def __git_clone(self):
        self.shell.cmd('cd %s' % self.tempdir)
        self.shell.check_cmd('git clone %s' % repository_url)
        self.shell.check_cmd('cd universitytimetable')
        self.shell.check_cmd('git checkout %s' % self.branch)
        self.shell.check_cmd('cp %s/local_settings.py ./' % self.origdir)


    def __syncdb(self):
        self.shell.check_cmd('python2.6 manage.py syncdb --noinput')


    def __run_django_tests(self):
        self.shell.check_cmd('python2.6 manage.py test')


    def __test_dev_server(self):
        self.shell.sendline('python2.6 manage.py runserver')
        self.shell.expect_exact('Quit the server with CONTROL-C.')
        response = urllib2.urlopen('http://127.0.0.1:8000').read()
        title = re.findall(r'<title>([^<]*)</title>', response)[0]
        self.shell.expect_exact('GET / HTTP/1.1')
        self.shell.sendcontrol('c')
        self.shell.waitprompt()


    def test_main(self):
        self.__git_clone()
        self.__syncdb()
        #self.__run_django_tests()
        self.__test_dev_server()

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
