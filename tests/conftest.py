import os
import sys

# The plugin's modules live in scripts/, which is not a package — put it on the
# path once here so every test module can import them by bare name.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
