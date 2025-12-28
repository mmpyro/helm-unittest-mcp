from utils.mcp import Server
from tools import *
from prompt import *


mcp = Server().mcp


# Run the server
if __name__ == "__main__":
    mcp.run()
