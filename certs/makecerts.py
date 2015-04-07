#!/usr/bin/env python
# **********************************************************************
#
# Copyright (c) 2003-2015 ZeroC, Inc. All rights reserved.
#
# **********************************************************************

import os, sys, shutil, glob, socket, subprocess, getopt

def usage():
    print("Usage: " + sys.argv[0] + " [options] [ip-address]")
    print("")
    print("Options:")
    print("-h               Show this message.")
    print("-d               Debugging output.")
    print("--ip-address     <ip address>")
    print("--hostname       <hostname>")
    sys.exit(1)

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

#
# Check arguments
#
debug = False
ipAddress = None
hostname = None
commonName = None

try:
    opts, args = getopt.getopt(sys.argv[1:], "hd", ["help", "debug", "ip-address=", "hostname="])
except getopt.GetoptError as e:
    print("Error %s " % e)
    usage()
    sys.exit(1)

for (o, a) in opts:
    if o == "-h" or o == "--help":
        usage()
        sys.exit(0)
    elif o == "-d" or o == "--debug":
        debug = True
    elif o == "--ip-address":
        ipAddress = a
    elif o == "--hostname":
        hostname = a

if hostname:
    commonName = hostname
elif ipAddress:
    commonName = ipAddress

if not ipAddress:
    try:
        ipAddress = socket.gethostbyname(socket.gethostname())
    except:
        ipAddress = "127.0.0.1"

if not hostname:
    hostname = "localhost"

if not commonName:
    commonName = "localhost"

cwd = os.getcwd()
if not os.path.exists("ImportKey.class") or os.path.basename(cwd) != "certs":
    print("You must run this script from the certs directory")
    sys.exit(1)

#
# Make sure keytool is available
#
if subprocess.call("keytool", shell=True, stdout=DEVNULL, stderr=DEVNULL) != 0:
    print("error: couldn't run keytool, make sure the Java bin directory is in your PATH,\nkeytool is required to generate Java certificates")
    sys.exit(1)

bksSupport = True
if subprocess.call("javap org.bouncycastle.jce.provider.BouncyCastleProvider", shell=True, stdout=DEVNULL, stderr=DEVNULL) != 0:
    print("warning: couldn't find Bouncy Castle provider, Android certificates won't be created")
    bksSupport = False
    
while True:
    print("The IP address used for the server certificate will be: " + ipAddress)
    sys.stdout.write("Do you want to keep this IP address? (y/n) [y]")
    sys.stdout.flush()
    input = sys.stdin.readline().strip()
    if input == 'n':
        sys.stdout.write("IP : ")
        sys.stdout.flush()
        ipAddress = sys.stdin.readline().strip()
    else:
        break
    
while True:
    print("The hostname used for the server certificate will be: " + hostname)
    sys.stdout.write("Do you want to keep this hostname? (y/n) [y]")
    sys.stdout.flush()
    input = sys.stdin.readline().strip()
    if input == 'n':
        sys.stdout.write("Hostname : ")
        sys.stdout.flush()
        hostname = sys.stdin.readline().strip()
    else:
        break

certs = "."
caHome = os.path.abspath(os.path.join(certs, "ca")).replace('\\', '/')

#
# Static configuration file data.
#

configFiles = {
"ca.cnf": """
# **********************************************************************
#
# Copyright (c) 2003-2015 ZeroC, Inc. All rights reserved.
#
# **********************************************************************

# Configuration file for the CA. This file is generated by iceca init.
# DO NOT EDIT!

###############################################################################
###  Self Signed Root Certificate\n\
###############################################################################

[ ca ]
default_ca = ice

[ ice ]
default_days     = 1825    # How long certs are valid.
default_md       = sha256  # The Message Digest type.
preserve         = no      # Keep passed DN ordering?

[ req ]
default_bits        = 2048
default_keyfile     = %(caHome)s/cakey.pem
default_md          = sha256
prompt              = no
distinguished_name  = dn
x509_extensions     = extensions

[ extensions ]
basicConstraints = CA:true

# PKIX recommendation.
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always

[dn]
countryName            = US
stateOrProvinceName    = Florida
localityName           = Jupiter
organizationName       = ZeroC, Inc.
organizationalUnitName = Ice
commonName             = ZeroC Tests and Demos CA
emailAddress           = info@zeroc.com
""",
"ice.cnf": """
# **********************************************************************
#
# Copyright (c) 2003-2015 ZeroC, Inc. All rights reserved.
#
# **********************************************************************

# Configuration file to sign a certificate. This file is generated by iceca init.
# DO NOT EDIT!!

[ ca ]
default_ca = ice

[ ice ]
dir              = %(caHome)s               # Where everything is kept.
private_key      = $dir/cakey.pem           # The CA Private Key.
certificate      = $dir/cacert.pem          # The CA Certificate.
database         = $dir/index.txt           # Database index file.
new_certs_dir    = $dir                     # Default loc for new certs.
serial           = $dir/serial              # The current serial number.
certs            = $dir                     # Where issued certs are kept.
RANDFILE         = $dir/.rand               # Private random number file.
default_days     = 1825                     # How long certs are valid.
default_md       = sha256                   # The Message Digest type.
preserve         = yes                      # Keep passed DN ordering?

policy           = ca_policy
x509_extensions  = certificate_extensions

[ certificate_extensions ]
basicConstraints = CA:false

# PKIX recommendation.
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
%(subjectAltName)s
[ ca_policy ]
countryName            = match
stateOrProvinceName    = match
organizationName       = match
organizationalUnitName = optional
emailAddress           = optional
commonName             = supplied

[ req ]
default_bits        = 1024
default_md          = sha256
prompt              = no
distinguished_name  = dn
x509_extensions     = extensions

[ extensions ]
basicConstraints = CA:false

# PKIX recommendation.
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
keyUsage = nonRepudiation, digitalSignature, keyEncipherment

[dn]
countryName            = US
stateOrProvinceName    = Florida
localityName           = Jupiter
organizationName       = ZeroC, Inc.
organizationalUnitName = Ice
commonName             = %(commonName)s
emailAddress           = info@zeroc.com
"""
}

def subjectAltName():
    s = ""
    if hostname  or ipAddress:
        s += "subjectAltName = "
        if hostname:
            s += "DNS: " + hostname
        if ipAddress:
            if hostname:
                s += " ,"
            s += "IP: " + ipAddress
    return s
        
def generateConf(file, dns = None, ip = None, commonName = None):
    
    data = configFiles[file]
    
    cnf = open(os.path.join(caHome, file), "w")
    if dns and ip and commonName:
        cnf.write(data % {"caHome": caHome,
                          "subjectAltName": subjectAltName(),
                          "commonName": commonName})
    else:
        cnf.write(data % {"caHome": caHome})
    cnf.close()

def run(cmd):
    if debug:
        print("[debug]", cmd)

    p = subprocess.Popen(cmd,
                         shell = True,
                         stdin = subprocess.PIPE,
                         stdout = subprocess.STDOUT if debug else subprocess.PIPE,
                         stderr = subprocess.STDERR if debug else subprocess.PIPE,
                         bufsize = 0)
    if p.wait() != 0:
        print("command failed:" + cmd + "\n")
        for line in p.stdout.readlines():
            print(line.decode("utf-8").strip())
        sys.exit(1)
    
def runOpenSSL(command):
    run("openssl " + command)

def jksToBks(source, target):
    cmd = "keytool -importkeystore -srckeystore " + source + " -destkeystore " + target + \
          " -srcstoretype JKS -deststoretype BKS -srcstorepass password -deststorepass password " + \
          "-provider org.bouncycastle.jce.provider.BouncyCastleProvider -noprompt"
    if debug:
        print("[debug]", cmd)

    p = subprocess.Popen(cmd, shell = True, stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                        stderr = subprocess.STDOUT, bufsize = 0)

    while(True):
        line = p.stdout.readline()            
        if p.poll() is not None and not line:
            # The process terminated
            break
            
        if line.find("java.lang.ClassNotFoundException: org.bouncycastle.jce.provider.BouncyCastleProvider") != -1:
            print("")
            print("WARNING: BouncyCastleProvider not found cannot export certificates for android")
            print("         demos in BKS format. You can download BKS provider from:")
            print("")
            print("            http://www.bouncycastle.org/")
            print("")
            print("         After download copy the JAR to $JAVA_HOME/lib/ext where JAVA_HOME")
            print("         points to your JRE and run this script again.")
            print("")
            return False
        elif line.find("java.security.InvalidKeyException: Illegal key size") != -1:
            print("")
            print("WARNING: You need to install Java Cryptography Extension (JCE) Unlimited")
            print("         Strength. You can download it from Additional Resources section")
            print("         in Orcale Java Download page at:")
            print("")
            print("             http://www.oracle.com/technetwork/java/javase/downloads/index.html")
            print("")
            return False
        return True
    if p.poll() != 0:
        sys.exit(1)

def generateCert(desc, name, commonName = None):

    if not commonName:
        commonName = desc
    
    generateConf("ice.cnf", hostname, ipAddress, commonName)

    cert = os.path.join(certs, name + "_rsa1024_pub.pem")
    key = os.path.join(certs, name + "_rsa1024_priv.pem")
    sys.stdout.write("Generating new " + desc + " certificates... ")
    sys.stdout.flush()

    if os.path.exists(cert):
        os.remove(cert)
    if os.path.exists(key):
        os.remove(key)

    serial = os.path.join(caHome, "serial")
    f = open(serial, "r")
    serialNum = f.read().strip()
    f.close()
    
    tmpKey = os.path.join(caHome, serialNum + "_key.pem")
    tmpCert = os.path.join(caHome, serialNum + "_cert.pem")
    req = os.path.join(caHome, "req.pem")
    config = os.path.join(caHome, "ice.cnf")

    #
    # Generate PEM certificates
    #
    runOpenSSL("req -config " + config + " -newkey rsa:1024 -nodes -keyout " + tmpKey + " -keyform PEM -out " + req)
    runOpenSSL("ca -config " + config + " -batch -in " + req)

    shutil.move(os.path.join(caHome, serialNum + ".pem"), tmpCert)
    shutil.copyfile(tmpKey, key)
    shutil.copyfile(tmpCert, cert)
    os.remove(req)

    #
    # Generate PKCS12 certificates
    #
    runOpenSSL("pkcs12 -in " + cert + " -inkey " + key + " -export -out " + name + "_rsa1024.pfx" + \
               " -certpbe PBE-SHA1-RC4-40 -keypbe PBE-SHA1-RC4-40" + \
               " -passout pass:password -name " + desc)

    #
    # Generate Java keystore
    #
    tmpFile = desc + ".p12"
    runOpenSSL("pkcs12 -in " + cert + " -inkey " + key + " -export -out " + tmpFile + \
               " -name rsakey -passout pass:password -certfile cacert.pem")
    run("java -classpath . ImportKey " + tmpFile + " rsakey cacert.pem " + desc + ".jks password")
    os.remove(tmpFile)

    #
    # Generate BKS for Android if supported
    #
    if bksSupport:
        jksToBks(desc + ".jks", desc + ".bks")
    
    if not debug:
        print("ok")


#
# Generate the CA certificate and database
#
if os.path.exists(caHome):
    shutil.rmtree(caHome)

sys.stdout.write("Generating new CA certificate and key... ")
sys.stdout.flush()
os.mkdir(caHome)

f = open(os.path.join(caHome, "serial"), "w")
f.write("01")
f.close()

f = open(os.path.join(caHome, "index.txt"), "w")
f.truncate(0)
f.close()

generateConf("ca.cnf")

config = os.path.join(caHome, "ca.cnf")
caCert = os.path.join(caHome, "cacert.pem")
runOpenSSL("req -config " + config + " -x509 -days 1825 -newkey rsa:1024 -out " + caCert + " -outform PEM -nodes")
runOpenSSL("x509 -in " + caCert + " -outform DER -out " + os.path.join(certs, "cacert.der")) # Convert to DER
shutil.copyfile(caCert, os.path.join(certs, "cacert.pem"))
shutil.copyfile(os.path.join(caHome, "cakey.pem"), os.path.join(certs, "cakey.pem"))
if os.path.exists("certs.jks"):
    os.remove("certs.jks")
run("keytool -import -alias cacert -file cacert.der -keystore certs.jks -storepass password -noprompt")
if not debug:
    print("ok")

#
# Generate the client and the server certificates
#
generateCert("server", "s", commonName)
generateCert("client", "c")

os.chdir("..")