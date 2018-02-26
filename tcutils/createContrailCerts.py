import subprocess, os
import shlex,time

if os.path.isfile("/usr/bin/openssl"):
    OPENSSL="/usr/bin/openssl"
else:
    OPENSSL="/usr/local/ssl/bin/openssl"

PRINTF="/usr/bin/printf"
MKDIR="/bin/mkdir"
TOUCH="/bin/touch"
RM="/bin/rm"
CP="/bin/cp"
ECHO="/bin/echo"
CAT="/bin/cat"
CHOWN="/bin/chown"

OPENSSL_CFG='''
[ new_oids ]
                        [ ca ]
default_ca              = CA_default
# The default ca section
[ CA_default ]

certs           = certs                 # Where the issued certs are kept
crl_dir         = crl                   # Where the issued crl are kept
database        = database.txt          # database index file.
new_certs_dir   = certs                 # default place for new certs.

certificate     = cacert.pem            # The CA certificate
serial          = serial.txt            # The current serial number

default_days    = 365                   # how long to certify for
default_crl_days= 30                    # how long before next CRL
default_md      = sha1                  # which md to use.
preserve        = no                    # keep passed DN ordering

# A few difference way of specifying how similar the request should look
# For type CA, the listed attributes must be the same, and the optional
# and supplied fields are just that :-)
policy          = policy_match

# For the CA policy
[ policy_match ]
countryName                     = match
stateOrProvinceName             = match
organizationName                = match
organizationalUnitName          = optional
commonName                      = supplied
emailAddress                    = optional

# For the 'anything' policy
# At this point in time, you must list all acceptable 'object'
# types.
[ policy_anything ]
countryName                     = optional
stateOrProvinceName             = optional
localityName                    = optional
organizationName                = optional
organizationalUnitName          = optional
commonName                      = supplied
emailAddress                    = optional

####################################################################
[ req ]
default_bits                    = 1024
default_keyfile                 = privkey.pem
distinguished_name              = req_distinguished_name
attributes                      = req_attributes
x509_extensions = v3_ca # The extentions to add to the self signed cert
[ req_distinguished_name ]
countryName                             = Country Name (2 letter code)
countryName_min                         = 2
countryName_max                         = 2
stateOrProvinceName                     = State or Province Name (full name)
localityName                            = Locality Name (eg, city)
0.organizationName                      = Organization Name (eg, company)
commonName                              = Common Name (eg, YOUR name)

#Default certificate generation filelds
organizationalUnitName_default          = Juniper Contrail
0.organizationName_default              = OpenContrail
stateOrProvinceName_default             = California
localityName_default                    = Sunnyvale
countryName_default                     = US
commonName_default                      = 10.87.141.33
commonName_max                          = 64
emailAddress                            = Email Address
emailAddress_default                    = admin@juniper.com
emailAddress_max                        = 40

# SET-ex3                               = SET extension number 3
[ req_attributes ]
challengePassword                       = A challenge password
challengePassword_min                   = 4
challengePassword_max                   = 20
unstructuredName                        = An optional company name
[ usr_cert ]
basicConstraints=CA:FALSE
nsComment                       = OpenSSL Generated Certificate
# PKIX recommendations harmless if included in all certificates.
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer:always
[ v3_ca]
# Extensions for a typical CA
# PKIX recommendation.
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer:always
basicConstraints = CA:true
[ crl_ext ]
authorityKeyIdentifier=keyid:always,issuer:always
'''

def create_certificate():
    
    output = subprocess.Popen([MKDIR, '-p', './working/cfg'], stdout=subprocess.PIPE)
    ##time.sleep(2)
    ##if os.path.isdir('./working'):
        ##os.chdir('working')
    ##else:
        ##assert 'failed to create temp directory'

    check_file_dir_exists('./working')
    os.chdir('working')
    
    subprocess.Popen([TOUCH, './cfg/openssl.cfg'], stdout=subprocess.PIPE)
    with open("./cfg/openssl.cfg", "w") as cfg_file:
        cfg_file.write(OPENSSL_CFG)

    output = subprocess.Popen([MKDIR, './key'], stdout=subprocess.PIPE)

    check_file_dir_exists('./key')
    output = subprocess.Popen([OPENSSL, 'genrsa', '-aes128', '-out', './key/private.key', '-passout',
        'pass:changeit', '1024'], stdout=subprocess.PIPE)

    check_file_dir_exists('./key/private.key')
    print "Convert to PKCS8"
    cmd = OPENSSL+" pkcs8 -in ./key/private.key -topk8 -nocrypt -out ./key/privatep8.key -passin pass:changeit"
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)

    check_file_dir_exists('./key/privatep8.key')
    print "Create CA Certificate"
    output = subprocess.Popen([MKDIR, './cacert'], stdout=subprocess.PIPE)
    cmd = OPENSSL+' req -config ./cfg/openssl.cfg -new -x509 -days 3650 -key\
        ./key/privatep8.key -out ./cacert/ca.cer -batch'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)

    check_file_dir_exists('./cacert/ca.cer')
    print "Create CSR"
    output = subprocess.Popen([MKDIR, './req'], stdout=subprocess.PIPE)
    cmd = OPENSSL+' req -new -key ./key/privatep8.key -out ./req/client.csr -config ./cfg/openssl.cfg -batch'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    cmd = OPENSSL+' req -new -key ./key/privatep8.key -out ./req/server.csr -config ./cfg/openssl.cfg -batch'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)

    check_file_dir_exists('./req/server.csr')
    print "Create CA signed cert from CSR"
    output = subprocess.Popen([MKDIR, './certs'], stdout=subprocess.PIPE)
    cmd = TOUCH+' ./database.txt ./database.txt.attr ./serial.txt'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    check_file_dir_exists('./serial.txt')
    with open('./serial.txt', 'w') as cfg_file:
        cfg_file.write('01')

    ##time.sleep(2)
    cmd = OPENSSL+' ca -policy policy_anything -config cfg/openssl.cfg -cert cacert/ca.cer\
        -in req/client.csr -keyfile key/privatep8.key -days 3650 -out certs/client.crt -batch'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)

    check_file_dir_exists('./certs/client.crt')
    [os.remove(file) for file in os.listdir(os.curdir) if 'database' in file]

    time.sleep(2)
    cmd = TOUCH + ' database.txt database.txt.attr'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)

    check_file_dir_exists('./database.txt.attr')
    cmd = OPENSSL + ' ca -policy policy_anything -config cfg/openssl.cfg -cert cacert/ca.cer\
        -in req/server.csr -keyfile key/privatep8.key -days 3650 -out certs/server.crt -batch'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)

    retVal = []
    cmd = 'cat cacert/ca.cer'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    retVal.append(output.communicate()[0])
    cmd = 'cat key/privatep8.key'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    retVal.append(output.communicate()[0])
    
    os.chdir('..')
    cmd = RM + ' -fr working'
    output = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    
    return retVal

def check_file_dir_exists(file_dir, tries=5):
    while tries > 0:
        if os.path.isfile(file_dir) or os.path.isdir(file_dir):
            return 1
        else:
            time.sleep(0.5)
            tries -= 1
    assert False, 'file is not created'

if __name__ == '__main__':
    create_certificate()
