import sys
from pexpect import spawn
from tempfile import mkdtemp
from shutil import rmtree
import types
import urllib2
import re

repository_url = 'git://github.com/troyand/universitytimetable.git'


def main():
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
        shell.sendline('export PS1="%s"' % shell.prompt)
        shell.waitprompt()
        shell.waitprompt()
        shell.sendline('pwd')
        shell.waitprompt()
        origdir = shell.before.splitlines()[1]
        shell.sendline('cd %s' % tempdir)
        shell.waitprompt()
        shell.sendline('pwd')
        shell.waitprompt()
        shell.sendline('git clone %s' % repository_url)
        shell.waitprompt()
        shell.sendline('echo $?')
        shell.waitprompt()
        result = int(shell.before.splitlines()[1])
        if result != 0:
            raise Exception('git clone failed')
        shell.sendline('ls')
        shell.waitprompt()
        shell.sendline('cd universitytimetable')
        shell.waitprompt()
        shell.sendline('cp %s/local_settings.py ./' % origdir)
        shell.waitprompt()
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
        shell.sendcontrol('c')
        shell.waitprompt()
    except:
        print 'Exception caught'
    print
    print 'Removing the temporary directory %s and its contents' % tempdir
    rmtree(tempdir)


if __name__ == '__main__':
    main()
