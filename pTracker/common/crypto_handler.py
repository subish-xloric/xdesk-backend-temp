""" Helper module for cryptography

! Old module name: CryptoHandler.py
"""
from os import urandom
from base64 import b64encode, b64decode
from Crypto.Cipher import ARC4
from django.conf import settings


class CryptoHandler:
    """ Class contains methods for to encrypt and decrypt given data """

    def __init__(self):
        """ constructor for initiation """
        self.secretKey = "verterisDevelopement" #settings.SECRET_KEY
        self.saltSize = 8

    def encrypt(self,plaintext):
        plaintext = plaintext.encode('ascii','ignore')
        salt = urandom(self.saltSize)
        arc4 = ARC4.new(salt + self.secretKey.encode('ascii','ignore'))
        plaintext = "%3d%s%s" % (len(plaintext), plaintext, urandom(256-len(plaintext)))
        return "%s$%s" % (b64encode(salt).decode('ascii','ignore'), b64encode(arc4.encrypt(plaintext)).decode('ascii','ignore'))

    def decrypt(self, ciphertext):
        """ Method to decrypt given input """
        a = ciphertext.split('$')
        salt = b64decode(a[0].encode('ascii','ignore'))
        ciphertext = b64decode(a[1].encode('ascii','ignore'))
        arc4 = ARC4.new(salt + self.secretKey.encode('ascii', 'ignore'))
        plaintext = arc4.decrypt(ciphertext).decode('ascii', 'ignore')
        return plaintext[3:3+int(plaintext[:3].strip())]