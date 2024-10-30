from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from base64 import urlsafe_b64decode
import pyzipper
import os
import logging
import time
from dotenv import load_dotenv
from bitwarden_sdk import BitwardenClient, DeviceType, client_settings_from_dict
from uuid import UUID
from argon2.low_level import hash_secret_raw, Type
from colorama import init, Fore, Style
from tqdm import tqdm
from terminaltexteffects.effects import effect_rain, effect_beams, effect_decrypt, effect_matrix

# Initialize colorama
init(autoreset=True)

def display_decrypt_effect(text):
    effect = effect_decrypt.Decrypt(text)
    effect.effect_config.final_gradient_frames = 1

    with effect.terminal_output(end_symbol=" ") as terminal:
        for frame in effect:
            terminal.print(frame)
            time.sleep(0.01)
        print()
##-------------Interactive-------------

def clear_screen():
    """
    Clear the terminal screen.
    """
    print("\033c", end="")  # Clear the terminal
    
def display_ascii_art():
    """
    Display ASCII art with Beam effect animation.
    """
    art = """
█░░ ▄▀█ ▀█ █▄█ █░█░█ ▄▀█ █▀█ █▀▄ █▀▀ █▄░█
█▄▄ █▀█ █▄ ░█░ ▀▄▀▄▀ █▀█ █▀▄ █▄▀ ██▄ █░▀█
    """
    effect = effect_beams.Beams(art)
    effect.effect_config.final_gradient_frames = 1
    
    with effect.terminal_output(end_symbol=" ") as terminal:
        for frame in effect:
            terminal.print(frame)
            time.sleep(0.02)  # Ajuste de velocidad de la animación

def interactive_message():
    """
    Display an interactive welcome message with loading animation.
    """
    print("\033c", end="")  # Clear the terminal

    # Welcome message with Rain effect
    welcome_text = "WELCOME TO LAZYWARDEN"
    effect_welcome = effect_rain.Rain(welcome_text)
    effect_welcome.effect_config.final_gradient_frames = 1
    
    with effect_welcome.terminal_output(end_symbol=" ") as terminal:
        for frame in effect_welcome:
            terminal.print(frame)
            time.sleep(0.06)  # Ajuste de velocidad de la animación
            print()

    # Additional ASCII art below the welcome message with Beams effect
    additional_art1 = """
       ________
      | |____| |
      |   __   |
      |  (__)  |
      |        |
      |________|
    """
    
    effect_additional1 = effect_rain.Rain(additional_art1)
    effect_additional1.effect_config.final_gradient_frames = 1
    
    with effect_additional1.terminal_output(end_symbol=" ") as terminal:
        for frame in effect_additional1:
            terminal.print(frame)
            time.sleep(0.02)  # Ajuste de velocidad de la animación
            print()

    # Loading message with Rain effect
    loading_text = "Loading, please wait..."
    effect_loading = effect_rain.Rain(loading_text)
    effect_loading.effect_config.final_gradient_frames = 1
    
    with effect_loading.terminal_output(end_symbol=" ") as terminal:
        for frame in effect_loading:
            terminal.print(frame)
            time.sleep(0.05)

    clear_screen()
    display_ascii_art()
    print()
    print("\n")

##------------------------------------------------------------------------

    display_decrypt_effect("Starting by Decrypting All Zip and JSON Folder 🔑")
    print()

#------------------------------------------------------------------------



# Display interactive message
interactive_message()

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for Bitwarden Secret Manager
BW_API_URL = os.getenv("API_URL")
BW_IDENTITY_URL = os.getenv("IDENTITY_URL")
BW_ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")
BW_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
TIMESTAMP = os.getenv("TIMESTAMP")

if not all([BW_API_URL, BW_IDENTITY_URL, BW_ORGANIZATION_ID, BW_ACCESS_TOKEN, TIMESTAMP]):
    raise ValueError("One or more environment variables are not set. Check your .env file.")

# Setup Bitwarden client
bw_client = BitwardenClient(
    client_settings_from_dict(
        {
            "apiUrl": BW_API_URL,
            "deviceType": DeviceType.SDK,
            "identityUrl": BW_IDENTITY_URL,
            "userAgent": "Python",
        }
    )
)

# Authenticate using the Secret Manager Access Token
try:
    auth_client = bw_client.auth()
    auth_client.login_access_token(BW_ACCESS_TOKEN)
except Exception as e:
    logging.error(f"Error authenticating to Bitwarden: {e}")
    raise

def get_secret(secret_id):
    """
    Retrieve a secret from Bitwarden.

    Args:
        secret_id (str): The ID of the secret to retrieve.

    Returns:
        str: The secret value.

    Raises:
        Exception: If an error occurs while retrieving the secret.
    """
    try:
        UUID(secret_id, version=4)
        secret = bw_client.secrets().get(secret_id)
        return secret.data.value
    except Exception as e:
        logging.error(f"Error retrieving secret {secret_id}: {e}")
        raise

# Retrieve secrets from Bitwarden Secret Manager
ENCRYPTION_PASSWORD = get_secret("588b0643-7ba4-4a78-ba3e-9467ad9c81a7")
ZIP_PASSWORD = get_secret("3bcadf27-446d-47f0-b929-b1469fa58546")
ZIP_ATTACHMENT_PASSWORD = get_secret("89d458e7-9ac4-431e-9f23-95cb4b8cff86")

def decrypt(encrypted_data, password):
    """
    Decrypt data using Argon2.

    Args:
        encrypted_data (bytes): The data to decrypt.
        password (str): The password used for decryption.

    Returns:
        bytes: The decrypted data.

    Raises:
        Exception: If an error occurs during decryption.
    """
    try:
        # Ensure the Base64 encoded data is properly padded
        missing_padding = len(encrypted_data) % 4
        if missing_padding:
            encrypted_data += '=' * (4 - missing_padding)
        encrypted_data = urlsafe_b64decode(encrypted_data)
        salt = encrypted_data[:16]
        iv = encrypted_data[16:32]
        encrypted_data = encrypted_data[32:]
        key = hash_secret_raw(password.encode(), salt, time_cost=3, memory_cost=65536, parallelism=1, hash_len=32, type=Type.I)
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
        return decrypted_data
    except Exception as e:
        logging.error(f"{Fore.RED}Error decrypting data: {e}")
        raise

# Paths of files using the TIMESTAMP
ENCRYPTED_ZIP_FILE_PATH = f"/root/lazywarden/backup-drive/bw-backup_{TIMESTAMP}.zip"
DECRYPTED_ZIP_DIR_PATH = f"/root/lazywarden/backup-drive/decrypted_zip_{TIMESTAMP}"
DECRYPTED_JSON_FILE_PATH = os.path.join(DECRYPTED_ZIP_DIR_PATH, f"decrypted_bw-backup_{TIMESTAMP}.json")
DECRYPTED_ATTACHMENTS_DIR_PATH = os.path.join(DECRYPTED_ZIP_DIR_PATH, "attachments")

# Verify if the ZIP file exists
if not os.path.exists(ENCRYPTED_ZIP_FILE_PATH):
    print(f"The file {ENCRYPTED_ZIP_FILE_PATH} does not exist.")
else:
    # Create the destination directory if it does not exist
    os.makedirs(DECRYPTED_ZIP_DIR_PATH, exist_ok=True)
    os.makedirs(DECRYPTED_ATTACHMENTS_DIR_PATH, exist_ok=True)

    # Unzip the main encrypted ZIP file
    with pyzipper.AESZipFile(ENCRYPTED_ZIP_FILE_PATH, 'r') as zf:
        zf.pwd = ZIP_PASSWORD.encode()
        zf.extractall(DECRYPTED_ZIP_DIR_PATH)

    print(f"Decrypted ZIP contents saved to {DECRYPTED_ZIP_DIR_PATH}")

    # Path of the JSON file inside the unzipped folder
    encrypted_json_file_path = os.path.join(DECRYPTED_ZIP_DIR_PATH, f"bw-backup_{TIMESTAMP}.json")

    # Verify if the JSON file exists
    if not os.path.exists(encrypted_json_file_path):
        print(f"The file {encrypted_json_file_path} does not exist.")
    else:
        # Read the encrypted JSON file
        with open(encrypted_json_file_path, "rb") as f:
            encrypted_data = f.read()

        # Decrypt the JSON file data
        decrypted_data = decrypt(encrypted_data.decode('utf-8'), ENCRYPTION_PASSWORD)

        # Write the decrypted data to a new JSON file
        with open(DECRYPTED_JSON_FILE_PATH, "wb") as f:
            f.write(decrypted_data)
        
        print(f"Decrypted JSON data saved to {DECRYPTED_JSON_FILE_PATH}")

    # Unzip the attachments ZIP inside the main ZIP
    attachments_zip_file_path = os.path.join(DECRYPTED_ZIP_DIR_PATH, f"attachments_{TIMESTAMP}.zip")
    if not os.path.exists(attachments_zip_file_path):
        print(f"The file {attachments_zip_file_path} does not exist.")
    else:
        with pyzipper.AESZipFile(attachments_zip_file_path, 'r') as zf:
            zf.pwd = ZIP_ATTACHMENT_PASSWORD.encode()
            zf.extractall(DECRYPTED_ATTACHMENTS_DIR_PATH)

        print(f"Decrypted attachments saved to {DECRYPTED_ATTACHMENTS_DIR_PATH}")

# Adding a progress bar for decryption process
for _ in tqdm(range(100), desc=f"{Fore.GREEN}Decrypting Bitwarden Backup{Fore.RESET}", ncols=100, bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.BLUE, Fore.RESET)):
    time.sleep(0.01)  # Simulate some delay


print()
display_decrypt_effect("✅ Decrypting Completed Successfully! 🔓\nAll files have been decrypted! 🎉")

