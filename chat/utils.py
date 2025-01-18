from Crypto.PublicKey import RSA

import base64

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Random import get_random_bytes

def generate_key_pair():
    key = RSA.generate(2048)
    private_key = key.export_key().decode('utf-8')
    public_key = key.publickey().export_key().decode('utf-8')
    return private_key, public_key



def hybrid_encrypt_audio(audio_data, public_key_pem):
    """
    Encrypts audio data using AES and RSA (hybrid encryption).
    :param audio_data: The audio data (bytes).
    :param public_key_pem: The RSA public key in PEM format.
    :return: Encrypted AES key and AES-encrypted audio data.
    """
    # Generate a random AES key
    aes_key = get_random_bytes(32)  # 256-bit AES key

    # Encrypt the audio data using AES
    cipher_aes = AES.new(aes_key, AES.MODE_EAX)
    ciphertext, tag = cipher_aes.encrypt_and_digest(audio_data)

    # Encrypt the AES key using RSA
    public_key = RSA.import_key(public_key_pem)
    cipher_rsa = PKCS1_OAEP.new(public_key)
    encrypted_aes_key = cipher_rsa.encrypt(aes_key)

    return encrypted_aes_key, ciphertext, cipher_aes.nonce, tag



def hybrid_decrypt_audio(encrypted_aes_key, ciphertext, nonce, tag, private_key_pem):
    """
    Decrypts audio data using AES and RSA (hybrid decryption).
    :param encrypted_aes_key: The RSA-encrypted AES key.
    :param ciphertext: The AES-encrypted audio data.
    :param nonce: The AES nonce.
    :param tag: The AES tag.
    :param private_key_pem: The RSA private key in PEM format.
    :return: Decrypted audio data (bytes).
    """
    # Decrypt the AES key using RSA
    private_key = RSA.import_key(private_key_pem)
    cipher_rsa = PKCS1_OAEP.new(private_key)
    aes_key = cipher_rsa.decrypt(encrypted_aes_key)

    # Decrypt the audio data using AES
    cipher_aes = AES.new(aes_key, AES.MODE_EAX, nonce=nonce)
    audio_data = cipher_aes.decrypt_and_verify(ciphertext, tag)

    return audio_data