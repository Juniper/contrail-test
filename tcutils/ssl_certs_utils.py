'''
Utility to generate ssl certificates using openssl:
-can generae private key
-can generate csr and certificate
-can generate self signed as well as CA signed certificates
'''
import logging as LOG
import subprocess
import sys

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.INFO)

OPEN_SSL_CNF='/etc/ssl/openssl.cnf'
TMP_SSL_CNF='/tmp/openssl.cnf'

class SslCert(object):

    @staticmethod
    def local_exec(cmd):
        result = 1
        output = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = output.communicate()
        if output.returncode != 0:
            result = 0
            LOG.error(stdout)
            LOG.error(stderr)
            raise RuntimeError('Command (%s) Failed' % cmd)

        return (result, stdout, stderr)

    @staticmethod
    def generate_private_key(location, options='genrsa'):
        result = SslCert.local_exec('openssl %s -out %s' % (options, location))[0]
        return result

    @staticmethod
    def generate_csr(location, private_key, subj='/', subjectAltName=''):
        result = 1
        cmd = 'openssl req -new -key %s -out %s -subj %s' % (
                    private_key, location, subj)
        if subjectAltName:
            #san = "subjectAltName=%s" % (subjectAltName)
            extensions = '-extensions SAN -config %s' % (TMP_SSL_CNF)
            cmd = 'cp %s %s;' % (OPEN_SSL_CNF, TMP_SSL_CNF) +\
                'echo [SAN] >> %s;' % (TMP_SSL_CNF) +\
                'echo subjectAltName=%s >> %s;' % (subjectAltName, TMP_SSL_CNF) +\
                cmd + ' %s' % (extensions)

        result = SslCert.local_exec(cmd)[0]
        return result

    @staticmethod
    def generate_cert(location, key, options='', ca_pem='', csr='',
                      self_signed=False, subj='/',
                      days=365, subjectAltName=''):
        result = 1
        if self_signed:
            cmd = 'openssl req -x509 -new -nodes -key %s -days %s -out %s -subj %s' % \
            (key, days, location, subj)
        elif (csr and ca_pem):
            cmd = 'openssl x509 -req -in %s -CA %s -CAkey %s -CAcreateserial -out %s -days %s' % \
            (csr, ca_pem, key, location, days)
            if subjectAltName:
                extensions = '-extensions SAN -extfile %s' % (TMP_SSL_CNF)
                cmd = cmd + ' %s' % (extensions)
        if options:
            cmd = 'openssl %s' % (options)

        result = SslCert.local_exec(cmd)[0]
        return result
