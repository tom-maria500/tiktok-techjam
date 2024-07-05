import pickle 
from pathlib import Path 
import streamlit_authenticator as stauth 
from streamlit_authenticator.utilities.hasher import Hasher

names = ["Maria Thomas, Vibha Guru"]
usernames = ["mthomas", "vguru"]
passwords = ["XXX", "XXX"]

hash_passwords = Hasher(passwords)
file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("wb") as file:
    pickle.dump(hash_passwords, file)