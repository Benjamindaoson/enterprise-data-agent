from dotenv import load_dotenv

from api.server import start_server


load_dotenv()


if __name__ == "__main__":
    start_server()