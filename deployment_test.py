import sys
from pexpect import spawn
from tempfile import mkdtemp
from shutil import rmtree
import types
import urllib2
import re

repository_url = 'git://github.com/troyand/universitytimetable.git'

def check_cmd(self, cmd):
    self.cmd(cmd)
    cmd_output = self.before
    self.cmd('echo $?')
    cmd_result = int(self.before.splitlines()[1])
    if cmd_result != 0:
        raise Exception(
                '%s: failed with exit status %d' % (
                    cmd,
                    cmd_result,
                    )
                )


def main(branch):
    tempdir = mkdtemp()
    print 'Using temporary directory: %s' % tempdir
    try:
        shell = spawn('/bin/sh')
        shell.logfile_read = sys.stdout
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
        shell.cmd('pwd')
        origdir = shell.before.splitlines()[1]
        shell.cmd('cd %s' % tempdir)
        shell.cmd('pwd')
        shell.check_cmd('git clone %s' % repository_url)
        shell.cmd('ls')
        shell.cmd('cd universitytimetable')
        shell.check_cmd('git checkout %s' % branch)
        shell.cmd('cp %s/local_settings.py ./' % origdir)
        shell.sendline('python2.6 manage.py runserver')
        shell.expect_exact('Quit the server with CONTROL-C.')
        try:
            response = urllib2.urlopen('http://127.0.0.1:8000').read()
            title = re.findall(r'<title>([^<]*)</title>', response)[0]
            print 'Fetched response with title: %s' % title
        except urllib2.URLError, e:
            print 'URLError:', e.reason
        except urllib2.HTTPError, e:
            print 'HTTPError', e.code
        shell.expect_exact('GET / HTTP/1.1')
        shell.sendcontrol('c')
        shell.waitprompt()
    except Exception, e:
        print 'Exception caught'
        print e
    print
    print 'Removing the temporary directory %s and its contents' % tempdir
    rmtree(tempdir)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        branch = sys.argv[1]
    else:
        branch = 'master'
    main(branch)
