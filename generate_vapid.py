import ecdsa
import base64
import os

def generate_vapid_keys():
    # Generate ECDSA P-256 (prime256v1) key pair
    private_key = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
    public_key = private_key.get_verifying_key()
    
    # Format according to VAPID spec (uncompressed format 0x04)
    public_format = b'\x04' + public_key.to_string()
    
    # URL-safe Base64 encode
    priv_b64 = base64.urlsafe_b64encode(private_key.to_string()).decode('utf-8').rstrip('=')
    pub_b64 = base64.urlsafe_b64encode(public_format).decode('utf-8').rstrip('=')
    
    with open('vapid_keys.txt', 'w') as f:
        f.write("# Add these to your .env file and Render environment variables\n")
        f.write(f"VAPID_PRIVATE_KEY={priv_b64}\n")
        f.write(f"VAPID_PUBLIC_KEY={pub_b64}\n")
        
    print("VAPID Keys generated and saved to vapid_keys.txt")

if __name__ == '__main__':
    generate_vapid_keys()
